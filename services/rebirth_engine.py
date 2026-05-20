from copy import deepcopy
import hashlib

from services.rebirth_bot import ability_priority, choose_response
from services.rebirth_cards import create_card_instance, get_card
from services.rebirth_contracts import PHASE_CHOOSE, PHASE_FINISHED, PHASE_RESULT, RebirthError
from services.rebirth_events import append_command, append_event, append_snapshot
from services.rebirth_state import (
    RebirthStateError,
    TurnPhase,
    available_evolutions,
    clear_played_cards,
    create_match,
    current_turn_phase,
    draw_to_hand_size,
    is_main_phase,
    remove_from_hand,
    set_turn_phase,
)


ENGINE_ABILITY_KEYS = {
    "rending_strike",
    "apex_rend",
    "brace",
    "immovable",
    "fade_cut",
    "bleed_mark",
    "high_guard",
    "storm_dive",
    "bulwark",
    "fortress_hit",
    "molten_bite",
    "inferno_bite",
    "silent_pursuit",
}


class EffectStack:
    def __init__(self, effects=None):
        self.effects = list(effects or [])

    def push_effect(self, effect_data: dict):
        if not isinstance(effect_data, dict):
            raise RebirthError("Effect data must be an object.", "malformed_request")
        self.effects.append(deepcopy(effect_data))
        return effect_data

    def resolve_stack(self, match_state: dict):
        events = []
        while self.effects:
            effect = self.effects.pop()
            event = self._apply_effect(match_state, effect)
            if event:
                events.append(event)
        match_state["effect_stack"] = list(self.effects)
        return events

    def _apply_effect(self, match_state, effect):
        effect_type = str(effect.get("type") or effect.get("effect_type") or "").strip().lower()
        side_name = str(effect.get("side") or effect.get("target") or "").strip()
        side = match_state.get(side_name) if side_name in {"player", "bot"} else None

        if effect_type == "status_tick":
            return self._tick_statuses(side_name, side)
        if side is None:
            return None

        if effect_type == "status":
            status_name = str(effect.get("status") or "").strip().lower()
            if not status_name:
                return None
            statuses = side.setdefault("statuses", {})
            current = statuses.get(status_name, {})
            turns = max(int(current.get("turns", 0) or 0), int(effect.get("turns", 1) or 1))
            potency = max(int(current.get("potency", 0) or 0), int(effect.get("potency", 1) or 1))
            statuses[status_name] = {"turns": turns, "potency": potency}
            return f"{side['name']} is affected by {status_name}."

        if effect_type == "damage":
            amount = max(0, int(effect.get("amount", 0) or 0))
            if amount <= 0:
                return None
            side["hp"] = max(0, int(side.get("hp", 0) or 0) - amount)
            side["wounded"] = True
            return f"{side['name']} takes {amount} stack damage."

        if effect_type == "heal":
            amount = max(0, int(effect.get("amount", 0) or 0))
            if amount <= 0:
                return None
            side["hp"] = min(int(side.get("max_hp", side.get("hp", 0)) or 0), int(side.get("hp", 0) or 0) + amount)
            return f"{side['name']} heals {amount} HP."

        if effect_type == "shield":
            statuses = side.setdefault("statuses", {})
            amount = max(1, int(effect.get("amount", 1) or 1))
            statuses["shield"] = {"turns": max(1, int(effect.get("turns", 1) or 1)), "potency": amount}
            return f"{side['name']} gains a {amount}-point shield."

        return None

    def _tick_statuses(self, side_name, side):
        if side is None:
            return None
        statuses = side.setdefault("statuses", {})
        if not statuses:
            return None

        messages = []
        expired = []
        burn = statuses.get("burn")
        if burn:
            amount = max(1, int(burn.get("potency", 1) or 1))
            side["hp"] = max(0, int(side.get("hp", 0) or 0) - amount)
            side["wounded"] = True
            messages.append(f"{side['name']} suffers {amount} burn damage.")

        for status_name, status in list(statuses.items()):
            turns = int(status.get("turns", 1) or 1) - 1
            if turns <= 0:
                expired.append(status_name)
            else:
                status["turns"] = turns
        for status_name in expired:
            statuses.pop(status_name, None)
            messages.append(f"{side['name']}'s {status_name} fades.")

        if side_name and messages:
            return " ".join(messages)
        return None


def effect_stack_for(match):
    return EffectStack(match.setdefault("effect_stack", []))


def _persist_effect_stack(match, stack):
    match["effect_stack"] = list(stack.effects)
    return match["effect_stack"]


def start_match(seed=None, player_card_ids=None, player_name="You", bot_profile_id=None):
    return create_match(
        seed=seed,
        player_card_ids=player_card_ids,
        player_name=player_name,
        bot_profile_id=bot_profile_id,
    )


def compare_power(player_card, bot_card):
    player_power = int(player_card.get("attack", player_card.get("power", 0)) or 0)
    bot_power = int(bot_card.get("attack", bot_card.get("power", 0)) or 0)

    if player_power > bot_power:
        return "player"
    if bot_power > player_power:
        return "bot"
    return "clash"


def card_attack(card):
    return int(card.get("attack", card.get("power", 0)) or 0)


def card_guard(card):
    return int(card.get("guard", 0) or 0)


def ability_key(card):
    return str(card.get("ability_key") or "").strip()


def ability_name(card):
    return str(card.get("ability_name") or card.get("name") or "Ability")


def clash_attack(card, opponent_card, *, turn=1):
    attack = card_attack(card)
    events = []
    key = ability_key(card)
    if key == "high_guard" and card_guard(opponent_card) <= 3:
        attack += 1
        events.append(f"{card['name']} used High Guard for +1 clash attack.")
    elif key == "silent_pursuit" and int(turn or 1) <= 2:
        attack += 1
        events.append(f"{card['name']} used Silent Pursuit for +1 early clash attack.")
    return attack, events


def tie_priority(card, defender_wounded=False):
    key = ability_key(card)
    if key in {"fade_cut", "bleed_mark"} and defender_wounded:
        return 2
    return 0


def compare_clash(match, player_card, bot_card):
    player_attack, player_events = clash_attack(player_card, bot_card, turn=match.get("turn", 1))
    bot_attack, bot_events = clash_attack(bot_card, player_card, turn=match.get("turn", 1))
    events = player_events + bot_events

    if player_attack > bot_attack:
        return "player", {"player_attack": player_attack, "bot_attack": bot_attack, "events": events}
    if bot_attack > player_attack:
        return "bot", {"player_attack": player_attack, "bot_attack": bot_attack, "events": events}

    player_priority = tie_priority(player_card, match["bot"].get("wounded", False))
    bot_priority = tie_priority(bot_card, match["player"].get("wounded", False))
    if player_priority > bot_priority:
        events.append(f"{player_card['name']} cut through the tie against a wounded target.")
        return "player", {"player_attack": player_attack, "bot_attack": bot_attack, "events": events}
    if bot_priority > player_priority:
        events.append(f"{bot_card['name']} cut through the tie against a wounded target.")
        return "bot", {"player_attack": player_attack, "bot_attack": bot_attack, "events": events}
    return "clash", {"player_attack": player_attack, "bot_attack": bot_attack, "events": events}


def calculate_damage(attacker, defender, defender_wounded=False):
    return damage_details(attacker, defender, defender_wounded=defender_wounded)["amount"]


def damage_details(attacker, defender, defender_wounded=False):
    amount = max(1, card_attack(attacker) - card_guard(defender) // 2)
    events = []
    attacker_key = ability_key(attacker)
    defender_key = ability_key(defender)

    if attacker_key == "rending_strike" and defender_wounded:
        amount += 2
        events.append(f"{attacker['name']} found the wound for +2 damage.")
    elif attacker_key == "apex_rend" and defender_wounded:
        amount += 3
        events.append(f"{attacker['name']} tore into the old wound for +3 damage.")
    elif attacker_key == "molten_bite":
        amount += 1
        events.append(f"{attacker['name']} added +1 damage with Molten Bite.")
    elif attacker_key == "inferno_bite":
        amount += 3
        events.append(f"{attacker['name']} added +3 damage with Inferno Bite.")
    elif attacker_key == "bleed_mark":
        amount += 1
        events.append(f"{attacker['name']} marked the target for +1 damage.")
    elif attacker_key == "storm_dive" and card_guard(defender) <= 3:
        amount += 2
        events.append(f"{attacker['name']} dove through low guard for +2 damage.")
    elif attacker_key == "immovable":
        amount += 2
        events.append(f"{attacker['name']} turned guard into +2 counter damage.")

    if attacker_key == "fortress_hit":
        before_minimum = amount
        amount = max(3, amount)
        if amount > before_minimum:
            events.append(f"{attacker['name']} guaranteed 3 damage with Fortress Hit.")

    reductions = {
        "brace": 2,
        "immovable": 3,
        "fortress_hit": 4,
    }
    reduction = reductions.get(defender_key, 0)
    if defender_key == "bulwark" and card_attack(attacker) <= 4:
        reduction = 3
    if reduction:
        before_reduction = amount
        amount = max(1, amount - reduction)
        if amount < before_reduction:
            events.append(f"{defender['name']} reduced incoming damage by {before_reduction - amount}.")

    return {"amount": amount, "events": events}


def apply_turn_damage(match, loser, amount):
    if loser == "player":
        side = match["player"]
    elif loser == "bot":
        side = match["bot"]
    else:
        return 0

    amount = max(0, int(amount or 0))
    shield = (side.get("statuses") or {}).get("shield")
    if shield and amount:
        absorbed = min(amount, max(0, int(shield.get("potency", 0) or 0)))
        amount -= absorbed
        shield["potency"] = max(0, int(shield.get("potency", 0) or 0) - absorbed)
        if shield["potency"] <= 0:
            side.setdefault("statuses", {}).pop("shield", None)
    side["hp"] = max(0, int(side["hp"]) - amount)
    side["wounded"] = amount > 0
    return amount


def finish_if_needed(match):
    player_hp = int(match["player"]["hp"])
    bot_hp = int(match["bot"]["hp"])

    if player_hp <= 0 and bot_hp <= 0:
        match["winner"] = "clash"
    elif player_hp <= 0:
        match["winner"] = "bot"
    elif bot_hp <= 0:
        match["winner"] = "player"
    else:
        return False

    match["is_finished"] = True
    match["phase"] = PHASE_FINISHED
    set_turn_phase(match, TurnPhase.END_PHASE)
    if match["winner"] == "player":
        match["log"].append("Victory. The bot is out of lives.")
    elif match["winner"] == "bot":
        match["log"].append("Defeat. You are out of lives.")
    else:
        match["log"].append("Final clash. Both sides fell together.")
    append_event(
        match,
        "MATCH_FINISHED",
        payload={"winner": match["winner"], "player_hp": player_hp, "bot_hp": bot_hp},
        message=match["log"][-1],
    )
    append_snapshot(match, "match_finished")
    return True


def _future_cards_empty(side):
    return not side.get("hand") and not side.get("deck")


def finish_if_exhausted(match):
    player_empty = _future_cards_empty(match["player"])
    bot_empty = _future_cards_empty(match["bot"])
    if not player_empty and not bot_empty:
        return False

    player_hp = int(match["player"]["hp"])
    bot_hp = int(match["bot"]["hp"])
    if player_hp > bot_hp:
        winner = "player"
        outcome = "Victory"
        message = "The duel reaches exhaustion. You survive with more HP and win the duel."
    elif bot_hp > player_hp:
        winner = "bot"
        outcome = "Defeat"
        message = "The duel reaches exhaustion. The bot survives with more HP and wins the duel."
    else:
        winner = "clash"
        outcome = "Clash"
        message = "The duel reaches exhaustion with equal HP. The match ends in a final clash."

    match["winner"] = winner
    match["is_finished"] = True
    match["phase"] = PHASE_FINISHED
    set_turn_phase(match, TurnPhase.END_PHASE)
    result = match.get("result") or {
        "damage": {"player": 0, "bot": 0},
        "ability_events": [],
        "effective_attack": {"player": 0, "bot": 0},
    }
    result["outcome"] = outcome
    result["winner"] = winner if winner in {"player", "bot"} else None
    result["message"] = f"{result.get('message', '').strip()} {message}".strip()
    result.setdefault("damage", {"player": 0, "bot": 0})
    result.setdefault("ability_events", [])
    result.setdefault("effective_attack", {"player": 0, "bot": 0})
    match["result"] = result
    match["log"].append(message)
    append_event(
        match,
        "MATCH_FINISHED",
        payload={"winner": winner, "player_hp": player_hp, "bot_hp": bot_hp, "reason": "exhaustion"},
        message=message,
    )
    append_snapshot(match, "match_exhausted")
    return True


def resolve_turn(match, player_card, bot_card):
    pre_stack = effect_stack_for(match)
    pre_stack_events = pre_stack.resolve_stack(match)
    _persist_effect_stack(match, pre_stack)

    winner, clash = compare_clash(match, player_card, bot_card)
    ability_events = list(pre_stack_events) + list(clash["events"])
    if winner == "player":
        damage_payload = damage_details(player_card, bot_card, match["bot"].get("wounded", False))
        damage = damage_payload["amount"]
        ability_events.extend(damage_payload["events"])
        damage = apply_turn_damage(match, "bot", damage)
        result = {
            "outcome": "Victory",
            "winner": "player",
            "damage": {"player": 0, "bot": damage},
            "message": f"{player_card['name']} overpowers {bot_card['name']}. Bot takes {damage} damage.",
        }
    elif winner == "bot":
        damage_payload = damage_details(bot_card, player_card, match["player"].get("wounded", False))
        damage = damage_payload["amount"]
        ability_events.extend(damage_payload["events"])
        damage = apply_turn_damage(match, "player", damage)
        result = {
            "outcome": "Defeat",
            "winner": "bot",
            "damage": {"player": damage, "bot": 0},
            "message": f"{bot_card['name']} beats {player_card['name']}. You take {damage} damage.",
        }
    else:
        match["player"]["wounded"] = False
        match["bot"]["wounded"] = False
        result = {
            "outcome": "Clash",
            "winner": None,
            "damage": {"player": 0, "bot": 0},
            "message": f"{player_card['name']} and {bot_card['name']} lock blades. No damage lands.",
        }

    status_stack = effect_stack_for(match)
    if winner == "player" and ability_key(player_card) in {"molten_bite", "inferno_bite"}:
        status_stack.push_effect({"type": "status", "side": "bot", "status": "burn", "potency": 1, "turns": 2})
    elif winner == "bot" and ability_key(bot_card) in {"molten_bite", "inferno_bite"}:
        status_stack.push_effect({"type": "status", "side": "player", "status": "burn", "potency": 1, "turns": 2})
    status_events = status_stack.resolve_stack(match)
    _persist_effect_stack(match, status_stack)
    ability_events.extend(status_events)

    if ability_events:
        result["message"] = f"{result['message']} {' '.join(ability_events)}"
    result["ability_events"] = ability_events
    result["effective_attack"] = {
        "player": clash["player_attack"],
        "bot": clash["bot_attack"],
    }
    match["result"] = result
    match["last_clash"] = {
        "player_card": deepcopy(player_card),
        "bot_card": deepcopy(bot_card),
        "outcome": result["outcome"],
        "ability_events": ability_events,
        "effective_attack": deepcopy(result["effective_attack"]),
    }
    match["log"].append(result["message"])
    append_event(
        match,
        "CLASH_RESOLVED",
        payload={
            "player_card_id": player_card["id"],
            "bot_card_id": bot_card["id"],
            "outcome": result["outcome"],
            "winner": result["winner"],
            "effective_attack": deepcopy(result["effective_attack"]),
        },
        message=result["message"],
    )
    damage = result.get("damage") or {}
    if int(damage.get("player", 0) or 0) or int(damage.get("bot", 0) or 0):
        append_event(
            match,
            "DAMAGE_DEALT",
            payload={
                "player": int(damage.get("player", 0) or 0),
                "bot": int(damage.get("bot", 0) or 0),
                "player_hp": match["player"]["hp"],
                "bot_hp": match["bot"]["hp"],
            },
        )
    for ability_event in ability_events:
        append_event(
            match,
            "ABILITY_TRIGGERED",
            payload={"message": ability_event},
            message=ability_event,
        )
    finish_if_needed(match)
    if not match["is_finished"]:
        match["phase"] = PHASE_RESULT
        set_turn_phase(match, TurnPhase.END_PHASE)
    append_snapshot(match, "clash_resolved")
    return result


def _side_sequence(side):
    return (
        len(side.get("deck", []))
        + len(side.get("hand", []))
        + len(side.get("discard", []))
        + (1 if side.get("played_card") else 0)
        + 1
    )


def _evolution_choice(side, profile_id=None):
    options = available_evolutions(side)
    if not options:
        return None

    def evolved_card(option):
        return get_card(option["evolution_id"])

    profile_id = str(profile_id or "defensive")
    if profile_id == "aggressive":
        return sorted(options, key=lambda option: (card_attack(evolved_card(option)), ability_priority(evolved_card(option))))[-1]
    if profile_id == "opportunist":
        return sorted(options, key=lambda option: (ability_priority(evolved_card(option)), card_attack(evolved_card(option))))[-1]
    return sorted(options, key=lambda option: (card_guard(evolved_card(option)), card_attack(evolved_card(option))))[-1]


def _evolve_side_duplicate(match, side_name, card_id):
    side = match[side_name]
    card = get_card(card_id)
    evolution_id = card.get("evolution_id")
    if not evolution_id:
        raise RebirthError("This monster has no MVP evolution.", "duplicate_not_available")

    matches = [hand_card for hand_card in side["hand"] if hand_card["id"] == card_id]
    if len(matches) < 2:
        raise RebirthError("Two matching monsters are required to evolve.", "duplicate_not_available")

    consumed = []
    for _ in range(2):
        consumed.append(remove_from_hand(side, card_id=card_id))
    for consumed_card in consumed:
        side["discard"].append(consumed_card)

    evolved = create_card_instance(evolution_id, side_name, _side_sequence(side))
    evolved["evolved_from"] = [consumed_card["instance_id"] for consumed_card in consumed]
    side["hand"].insert(0, evolved)
    actor = "Bot" if side_name == "bot" else card["name"]
    if side_name == "bot":
        match["log"].append(f"Turn {match['turn']:02d}   Bot evolved {card['name']} x2 into {evolved['name']}.")
    else:
        match["log"].append(f"Turn {match['turn']:02d}   {actor} x2 evolved into {evolved['name']}.")
    append_event(
        match,
        "CARD_EVOLVED",
        actor=side_name,
        payload={
            "source_card_id": card_id,
            "evolution_id": evolution_id,
            "consumed_instance_ids": list(evolved["evolved_from"]),
            "created_instance_id": evolved["instance_id"],
        },
        message=match["log"][-1],
    )
    append_snapshot(match, f"{side_name}_evolved")
    return deepcopy(evolved)


def evolve_bot_if_ready(match):
    if match.get("is_finished") or match.get("phase") != PHASE_CHOOSE or not is_main_phase(match):
        return None
    choice = _evolution_choice(match["bot"], (match.get("bot_profile") or {}).get("id"))
    if not choice:
        return None
    profile_id = (match.get("bot_profile") or {}).get("id") or "defensive"
    rates = {"defensive": 0.95, "aggressive": 0.75, "opportunist": 0.85}
    source = f"{match.get('match_id')}:{profile_id}:{match.get('turn')}:{choice['card_id']}"
    roll = int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:4], 16) / 0xFFFF
    if roll > rates.get(profile_id, 0.55):
        return None
    return _evolve_side_duplicate(match, "bot", choice["card_id"])


def play_card(match, *, card_instance_id=None, card_id=None):
    if match.get("is_finished"):
        raise RebirthError("Match is already finished.", "match_finished")
    if match.get("phase") != PHASE_CHOOSE:
        raise RebirthError("Advance to the next turn before playing another card.", "invalid_phase")
    if not is_main_phase(match):
        raise RebirthError(f"Cards can only be played during MAIN_PHASE. Current phase: {current_turn_phase(match)}.", "invalid_phase")
    if not card_instance_id and not card_id:
        raise RebirthError("A card_instance_id or card_id is required.", "missing_card")
    append_command(
        match,
        "PLAY_CARD",
        actor="player",
        payload={"card_instance_id": card_instance_id, "card_id": card_id},
    )

    try:
        player_card = remove_from_hand(
            match["player"],
            card_instance_id=card_instance_id,
            card_id=card_id,
        )
    except RebirthStateError as exc:
        raise RebirthError(str(exc), "invalid_card") from exc

    evolve_bot_if_ready(match)
    set_turn_phase(match, TurnPhase.COMBAT_PHASE)
    bot_profile_id = (match.get("bot_profile") or {}).get("id")
    bot_choice = choose_response(
        match["bot"]["hand"],
        player_card,
        profile_id=bot_profile_id,
        turn=match.get("turn", 1),
        player_wounded=match["player"].get("wounded", False),
        bot_wounded=match["bot"].get("wounded", False),
        match_id=match.get("match_id"),
    )
    if not bot_choice:
        finish_if_exhausted(match)
        return match

    bot_card = remove_from_hand(match["bot"], card_instance_id=bot_choice["instance_id"])
    match["player"]["played_card"] = player_card
    match["bot"]["played_card"] = bot_card
    turn_label = f"Turn {match['turn']:02d}"
    match["log"].append(f"{turn_label}   You played {player_card['name']}.")
    match["log"].append(f"{turn_label}   Bot played {bot_card['name']}.")
    append_event(
        match,
        "CARD_PLAYED",
        actor="player",
        payload={"card_id": player_card["id"], "instance_id": player_card["instance_id"]},
        message=match["log"][-2],
    )
    append_event(
        match,
        "CARD_PLAYED",
        actor="bot",
        payload={"card_id": bot_card["id"], "instance_id": bot_card["instance_id"]},
        message=match["log"][-1],
    )
    resolve_turn(match, player_card, bot_card)
    if not match["is_finished"]:
        finish_if_exhausted(match)
    return match


def evolve_duplicate(match, card_id):
    if match.get("is_finished"):
        raise RebirthError("Match is already finished.", "match_finished")
    if match.get("phase") != PHASE_CHOOSE:
        raise RebirthError("Evolution is only available before playing a card.", "invalid_phase")
    if not is_main_phase(match):
        raise RebirthError(f"Evolution is only available during MAIN_PHASE. Current phase: {current_turn_phase(match)}.", "invalid_phase")
    if not card_id:
        raise RebirthError("card_id is required.", "missing_card")
    append_command(match, "EVOLVE_DUPLICATE", actor="player", payload={"card_id": card_id})

    try:
        return _evolve_side_duplicate(match, "player", card_id)
    except RebirthError:
        raise
    except ValueError as exc:
        raise RebirthError(str(exc), "invalid_card") from exc


def next_turn(match):
    if match.get("is_finished"):
        raise RebirthError("Match is already finished.", "match_finished")
    if match.get("phase") != PHASE_RESULT:
        raise RebirthError("Next turn is available only after a clash result.", "invalid_phase")

    append_command(match, "NEXT_TURN", actor="player", payload={"turn": match.get("turn")})
    set_turn_phase(match, TurnPhase.END_PHASE)
    clear_played_cards(match)
    match["turn"] += 1
    set_turn_phase(match, TurnPhase.DRAW_PHASE)
    draw_stack = effect_stack_for(match)
    draw_stack.push_effect({"type": "status_tick", "side": "player"})
    draw_stack.push_effect({"type": "status_tick", "side": "bot"})
    status_events = draw_stack.resolve_stack(match)
    _persist_effect_stack(match, draw_stack)
    for status_event in status_events:
        match["log"].append(f"Turn {match['turn']:02d}   {status_event}")
        append_event(match, "ABILITY_TRIGGERED", payload={"message": status_event}, message=status_event)
    if finish_if_needed(match):
        return match
    draw_to_hand_size(match["player"])
    draw_to_hand_size(match["bot"])
    match["result"] = None
    match["last_clash"] = None
    match["phase"] = PHASE_CHOOSE
    set_turn_phase(match, TurnPhase.MAIN_PHASE)
    match["log"].append(f"Turn {match['turn']:02d}   Choose one monster.")
    append_event(
        match,
        "TURN_STARTED",
        payload={
            "turn": match["turn"],
            "player_hand_count": len(match["player"]["hand"]),
            "bot_hand_count": len(match["bot"]["hand"]),
        },
        message=match["log"][-1],
    )
    append_snapshot(match, "turn_started")
    finish_if_exhausted(match)
    return match
