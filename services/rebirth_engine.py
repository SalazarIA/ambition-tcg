from copy import deepcopy
import hashlib

from services.rebirth_bot import ability_priority, choose_response
from services.rebirth_cards import CARD_ABILITY_KEYS, create_card_instance, get_card, is_monster, is_spell, is_trap
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


ENGINE_ABILITY_KEYS = set(CARD_ABILITY_KEYS.values())
BATTLEFIELD_LIMIT = 4


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

        if effect_type == "draw":
            amount = max(1, int(effect.get("amount", 1) or 1))
            drawn = draw_to_hand_size(side, len(side.get("hand", [])) + amount)
            if not drawn:
                return None
            return f"{side['name']} draws {len(drawn)} card{'s' if len(drawn) != 1 else ''}."

        if effect_type == "cleanse":
            statuses = side.setdefault("statuses", {})
            if not statuses:
                return None
            removed = sorted(statuses.keys())
            statuses.clear()
            return f"{side['name']} cleanses {', '.join(removed)}."

        if effect_type == "destroy_shield":
            statuses = side.setdefault("statuses", {})
            if "shield" not in statuses:
                return None
            statuses.pop("shield", None)
            return f"{side['name']}'s shield is destroyed."

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

        if effect_type == "weaken":
            amount = max(1, int(effect.get("amount", 1) or 1))
            statuses = side.setdefault("statuses", {})
            statuses["weaken"] = {"turns": max(1, int(effect.get("turns", 1) or 1)), "potency": amount}
            return f"{side['name']} is weakened by {amount}."

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
        decay = statuses.get("decay")
        if decay:
            amount = max(1, int(decay.get("potency", 1) or 1))
            side["hp"] = max(0, int(side.get("hp", 0) or 0) - amount)
            side["wounded"] = True
            messages.append(f"{side['name']} suffers {amount} decay damage.")

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
    return max(0, int(card.get("attack", card.get("power", 0)) or 0) + int(card.get("attack_adjustment", 0) or 0))


def card_guard(card):
    return max(0, int(card.get("guard", 0) or 0) + int(card.get("guard_adjustment", 0) or 0))


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
    elif key == "fire_surge" and int(turn or 1) <= 2:
        attack += 2
        events.append(f"{card['name']} surged for +2 early combat attack.")
    elif key == "water_tide" and int(turn or 1) >= 3:
        attack += 2
        events.append(f"{card['name']} rode the rising tide for +2 combat attack.")
    elif key == "earth_fortify":
        bonus = min(2, max(0, card_guard(card) // 4))
        if bonus:
            attack += bonus
            events.append(f"{card['name']} converted guard into +{bonus} combat attack.")
    return attack, events


def tie_priority(card, defender_wounded=False):
    key = ability_key(card)
    if key in {"fade_cut", "bleed_mark", "shadow_mark", "fire_execute"} and defender_wounded:
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
    elif attacker_key == "fire_direct":
        amount += 2
        events.append(f"{attacker['name']} drove +2 direct fire damage.")
    elif attacker_key == "fire_execute" and defender_wounded:
        amount += 3
        events.append(f"{attacker['name']} executed the wounded target for +3 damage.")
    elif attacker_key == "shadow_decay":
        amount += 1
        events.append(f"{attacker['name']} opened a decay wound for +1 damage.")
    elif attacker_key == "shadow_drain":
        amount += 1
        events.append(f"{attacker['name']} drained +1 damage through shadow.")

    if attacker_key == "fortress_hit":
        before_minimum = amount
        amount = max(3, amount)
        if amount > before_minimum:
            events.append(f"{attacker['name']} guaranteed 3 damage with Fortress Hit.")

    reductions = {
        "brace": 2,
        "immovable": 3,
        "fortress_hit": 4,
        "water_guard": 2,
        "earth_bulwark": 3,
    }
    reduction = reductions.get(defender_key, 0)
    if defender_key in {"bulwark", "earth_counter"} and card_attack(attacker) <= 4:
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


def _card_cost(card):
    if is_monster(card):
        return max(1, min(10, int(card.get("cost") or card.get("tier") or 1)))
    return max(0, int(card.get("cost", 0) or 0))


def _spend_card_cost(match, side_name, card):
    side = match[side_name]
    cost = _card_cost(card)
    if cost <= 0:
        return 0
    current = int(side.get("energy", side.get("max_energy", 0)) or 0)
    if current < cost:
        raise RebirthError(f"Not enough energy to play {card['name']}.", "not_enough_energy")
    side["energy"] = current - cost
    return cost


def _refresh_energy_for_turn(match):
    energy = min(10, max(1, int(match.get("turn", 1) or 1)))
    for side_name in ("player", "bot"):
        side = match[side_name]
        side["max_energy"] = energy
        side["energy"] = energy


def _ready_battlefield(side):
    for card in side.get("battlefield", []):
        card["exhausted"] = False
        card["has_attacked"] = False


def _prepare_summoned_monster(card):
    summoned = deepcopy(card)
    summoned["current_guard"] = int(summoned.get("guard", 0) or 0)
    summoned["max_guard"] = int(summoned.get("guard", 0) or 0)
    summoned["exhausted"] = False
    summoned["has_attacked"] = False
    return summoned


def _find_battlefield_card(side, instance_id):
    for index, card in enumerate(side.get("battlefield", [])):
        if card.get("instance_id") == instance_id:
            return index, card
    return None, None


def _remove_defeated_battlefield_cards(side):
    defeated = []
    survivors = []
    for card in side.get("battlefield", []):
        if int(card.get("current_guard", card.get("guard", 0)) or 0) <= 0:
            defeated.append(card)
        else:
            survivors.append(card)
    side["battlefield"] = survivors
    for card in defeated:
        defeated_card = deepcopy(card)
        defeated_card["defeated"] = True
        side.setdefault("discard", []).append(defeated_card)
    return defeated


def _battlefield_slots_available(side):
    return max(0, BATTLEFIELD_LIMIT - len(side.get("battlefield", [])))


def _opponent_side(side_name):
    return "bot" if side_name == "player" else "player"


def _resolve_effect_side(owner_side, effect):
    target = str(effect.get("target") or effect.get("side") or "self").strip().lower()
    if target in {"self", "owner", "ally"}:
        return owner_side
    if target in {"opponent", "enemy", "attacker"}:
        return _opponent_side(owner_side)
    if target in {"player", "bot"}:
        return target
    return owner_side


def _push_card_effects(stack, owner_side, effects):
    for effect in reversed(effects or []):
        payload = deepcopy(effect)
        payload["side"] = _resolve_effect_side(owner_side, payload)
        payload.pop("target", None)
        stack.push_effect(payload)


def _resolve_spell_card(match, side_name, card):
    cost = _spend_card_cost(match, side_name, card)
    side = match[side_name]
    stack = effect_stack_for(match)
    _push_card_effects(stack, side_name, card.get("stack_effects") or [])
    effect_events = stack.resolve_stack(match)
    _persist_effect_stack(match, stack)
    side["discard"].append(card)
    match["last_clash"] = None
    match["result"] = {
        "outcome": "Spell",
        "winner": None,
        "damage": {"player": 0, "bot": 0},
        "message": f"{card['name']} resolved through the effect stack.",
        "ability_events": effect_events,
        "effective_attack": {"player": 0, "bot": 0},
    }
    if effect_events:
        match["result"]["message"] = f"{match['result']['message']} {' '.join(effect_events)}"
    turn_label = f"Turn {match['turn']:02d}"
    actor_label = "Bot" if side_name == "bot" else "You"
    match["log"].append(f"{turn_label}   {actor_label} cast {card['name']}.")
    append_event(
        match,
        "CARD_PLAYED",
        actor=side_name,
        payload={"card_id": card["id"], "instance_id": card["instance_id"], "type": "SPELL", "cost": cost},
        message=match["log"][-1],
    )
    append_event(
        match,
        "SPELL_RESOLVED",
        actor=side_name,
        payload={"card_id": card["id"], "effects": deepcopy(card.get("stack_effects") or [])},
        message=match["result"]["message"],
    )
    for event in effect_events:
        append_event(match, "ABILITY_TRIGGERED", actor=side_name, payload={"message": event}, message=event)
    finish_if_needed(match)
    if not match.get("is_finished"):
        match["phase"] = PHASE_CHOOSE
        set_turn_phase(match, TurnPhase.MAIN_PHASE)
    append_snapshot(match, f"{side_name}_spell_resolved")
    return match


def _arm_trap_card(match, side_name, card):
    cost = _spend_card_cost(match, side_name, card)
    side = match[side_name]
    armed = deepcopy(card)
    armed["armed"] = True
    armed["revealed"] = False
    armed["face_down"] = True
    armed["slot"] = len(side.setdefault("traps", [])) + 1
    armed["owner_side"] = side_name
    side["traps"].append(armed)
    match["last_clash"] = None
    match["result"] = {
        "outcome": "Trap Armed",
        "winner": None,
        "damage": {"player": 0, "bot": 0},
        "message": f"{card['name']} was set face down.",
        "ability_events": [],
        "effective_attack": {"player": 0, "bot": 0},
    }
    turn_label = f"Turn {match['turn']:02d}"
    actor_label = "Bot" if side_name == "bot" else "You"
    match["log"].append(f"{turn_label}   {actor_label} set a trap face down.")
    append_event(
        match,
        "TRAP_ARMED",
        actor=side_name,
        payload={"card_id": card["id"], "instance_id": card["instance_id"], "slot": armed["slot"], "cost": cost},
        message=match["log"][-1],
    )
    match["phase"] = PHASE_CHOOSE
    set_turn_phase(match, TurnPhase.MAIN_PHASE)
    append_snapshot(match, f"{side_name}_trap_armed")
    return match


def _summon_monster_card(match, side_name, card):
    side = match[side_name]
    if _battlefield_slots_available(side) <= 0:
        raise RebirthError("Battlefield is full.", "battlefield_full")
    cost = _spend_card_cost(match, side_name, card)
    summoned = _prepare_summoned_monster(card)
    side.setdefault("battlefield", []).append(summoned)
    side["played_card"] = summoned
    match["last_clash"] = None
    match["result"] = {
        "outcome": "Summon",
        "winner": None,
        "damage": {"player": 0, "bot": 0},
        "message": f"{summoned['name']} enters the battlefield.",
        "ability_events": [],
        "effective_attack": {"player": 0, "bot": 0},
    }
    turn_label = f"Turn {match['turn']:02d}"
    actor_label = "Bot" if side_name == "bot" else "You"
    match["log"].append(f"{turn_label}   {actor_label} summoned {summoned['name']}.")
    append_event(
        match,
        "CARD_PLAYED",
        actor=side_name,
        payload={"card_id": summoned["id"], "instance_id": summoned["instance_id"], "type": "MONSTER", "cost": cost},
        message=match["log"][-1],
    )
    append_event(
        match,
        "MONSTER_SUMMONED",
        actor=side_name,
        payload={
            "card_id": summoned["id"],
            "instance_id": summoned["instance_id"],
            "slot": len(side.get("battlefield", [])),
            "current_guard": summoned["current_guard"],
        },
        message=match["result"]["message"],
    )
    match["phase"] = PHASE_CHOOSE
    set_turn_phase(match, TurnPhase.MAIN_PHASE)
    append_snapshot(match, f"{side_name}_monster_summoned")
    return summoned


def _bot_auto_summon(match):
    if match.get("is_finished") or _battlefield_slots_available(match["bot"]) <= 0:
        return None
    affordable = [
        card
        for card in match["bot"].get("hand", [])
        if is_monster(card) and _card_cost(card) <= int(match["bot"].get("energy", 0) or 0)
    ]
    if not affordable:
        return None
    profile_id = (match.get("bot_profile") or {}).get("id") or "defensive"
    if profile_id == "aggressive":
        chosen = sorted(affordable, key=lambda card: (card_attack(card), ability_priority(card), card_guard(card), card["name"]))[-1]
    elif profile_id == "opportunist":
        chosen = sorted(affordable, key=lambda card: (ability_priority(card), card_attack(card), card_guard(card), card["name"]))[-1]
    else:
        chosen = sorted(affordable, key=lambda card: (card_guard(card), card_attack(card), ability_priority(card), card["name"]))[-1]
    bot_card = remove_from_hand(match["bot"], card_instance_id=chosen["instance_id"])
    return _summon_monster_card(match, "bot", bot_card)


def _apply_trap_effect(match, owner_side, trap, owner_card, opponent_card):
    effect = str(trap.get("trap_effect") or "").strip().lower()
    stack = effect_stack_for(match)
    messages = [f"{trap['name']} flips face up."]
    if effect == "negate_attack":
        opponent_card["attack_adjustment"] = opponent_card.get("attack_adjustment", 0) - card_attack(opponent_card)
        messages.append(f"{trap['name']} negates {opponent_card['name']}'s attack.")
    elif effect == "reflect_damage":
        stack.push_effect({"type": "damage", "side": _opponent_side(owner_side), "amount": 3})
        messages.append(f"{trap['name']} reflects 3 damage.")
    elif effect == "burn_attacker":
        stack.push_effect({"type": "status", "side": _opponent_side(owner_side), "status": "burn", "potency": 1, "turns": 2})
        messages.append(f"{trap['name']} brands the attacker with burn.")
    elif effect == "shield_owner":
        stack.push_effect({"type": "shield", "side": owner_side, "amount": 3, "turns": 2})
        messages.append(f"{trap['name']} raises a shield.")
    elif effect == "cleanse_owner":
        stack.push_effect({"type": "cleanse", "side": owner_side})
        messages.append(f"{trap['name']} cleanses its owner.")
    elif effect == "freeze_attacker":
        opponent_card["attack_adjustment"] = opponent_card.get("attack_adjustment", 0) - 2
        stack.push_effect({"type": "status", "side": _opponent_side(owner_side), "status": "freeze", "potency": 1, "turns": 1})
        messages.append(f"{trap['name']} freezes the attacker for -2 attack.")
    elif effect == "drain_attacker":
        stack.push_effect({"type": "heal", "side": owner_side, "amount": 2})
        stack.push_effect({"type": "damage", "side": _opponent_side(owner_side), "amount": 2})
        messages.append(f"{trap['name']} drains 2 HP.")
    elif effect == "destroy_shield":
        stack.push_effect({"type": "destroy_shield", "side": _opponent_side(owner_side)})
        messages.append(f"{trap['name']} breaks the opposing shield.")
    elif effect == "heal_owner":
        stack.push_effect({"type": "heal", "side": owner_side, "amount": 3})
        messages.append(f"{trap['name']} restores 3 HP.")
    elif effect == "weaken_attacker":
        opponent_card["attack_adjustment"] = opponent_card.get("attack_adjustment", 0) - 2
        stack.push_effect({"type": "weaken", "side": _opponent_side(owner_side), "amount": 2, "turns": 1})
        messages.append(f"{trap['name']} weakens the attacker.")
    stack_events = stack.resolve_stack(match)
    _persist_effect_stack(match, stack)
    return messages + stack_events


def _resolve_combat_traps(match, player_card, bot_card):
    events = []
    for owner_side, owner_card, opponent_card in (
        ("player", player_card, bot_card),
        ("bot", bot_card, player_card),
    ):
        side = match[owner_side]
        remaining_traps = []
        for trap in side.get("traps", []):
            if not trap.get("armed", True) or trap.get("trigger_phase") != TurnPhase.COMBAT_PHASE.value:
                remaining_traps.append(trap)
                continue
            triggered = deepcopy(trap)
            triggered["armed"] = False
            triggered["revealed"] = True
            triggered["face_down"] = False
            events.extend(_apply_trap_effect(match, owner_side, triggered, owner_card, opponent_card))
            side.setdefault("discard", []).append(triggered)
            append_event(
                match,
                "TRAP_TRIGGERED",
                actor=owner_side,
                payload={"card_id": trap["id"], "instance_id": trap.get("instance_id"), "effect": trap.get("trap_effect")},
                message=events[-1] if events else f"{trap['name']} triggered.",
            )
        side["traps"] = remaining_traps
    return events


def _resolve_unanswered_attack(match, player_card):
    set_turn_phase(match, TurnPhase.COMBAT_PHASE)
    match["player"]["played_card"] = player_card
    damage = max(1, card_attack(player_card))
    damage = apply_turn_damage(match, "bot", damage)
    result = {
        "outcome": "Victory",
        "winner": "player",
        "damage": {"player": 0, "bot": damage},
        "message": f"{player_card['name']} attacks directly. Bot takes {damage} damage.",
        "ability_events": [],
        "effective_attack": {"player": card_attack(player_card), "bot": 0},
    }
    match["result"] = result
    match["last_clash"] = {
        "player_card": deepcopy(player_card),
        "bot_card": None,
        "outcome": result["outcome"],
        "ability_events": [],
        "effective_attack": deepcopy(result["effective_attack"]),
    }
    match["log"].append(result["message"])
    append_event(
        match,
        "CLASH_RESOLVED",
        actor="player",
        payload={"player_card_id": player_card["id"], "bot_card_id": None, "outcome": result["outcome"], "winner": "player"},
        message=result["message"],
    )
    finish_if_needed(match)
    if not match.get("is_finished"):
        match["phase"] = PHASE_RESULT
        set_turn_phase(match, TurnPhase.END_PHASE)
    append_snapshot(match, "direct_attack_resolved")
    return result


def resolve_turn(match, player_card, bot_card, *, persistent_field=False):
    pre_stack = effect_stack_for(match)
    pre_stack_events = pre_stack.resolve_stack(match)
    _persist_effect_stack(match, pre_stack)

    trap_events = _resolve_combat_traps(match, player_card, bot_card)
    winner, clash = compare_clash(match, player_card, bot_card)
    ability_events = list(pre_stack_events) + list(trap_events) + list(clash["events"])
    if winner == "player":
        damage_payload = damage_details(player_card, bot_card, match["bot"].get("wounded", False))
        damage = damage_payload["amount"]
        ability_events.extend(damage_payload["events"])
        if persistent_field:
            bot_card["current_guard"] = int(bot_card.get("current_guard", bot_card.get("guard", 0)) or 0) - damage
        else:
            damage = apply_turn_damage(match, "bot", damage)
        result = {
            "outcome": "Victory",
            "winner": "player",
            "damage": {"player": 0, "bot": damage},
            "message": f"{player_card['name']} overpowers {bot_card['name']}. {'Target loses' if persistent_field else 'Bot takes'} {damage} damage.",
        }
    elif winner == "bot":
        damage_payload = damage_details(bot_card, player_card, match["player"].get("wounded", False))
        damage = damage_payload["amount"]
        ability_events.extend(damage_payload["events"])
        if persistent_field:
            player_card["current_guard"] = int(player_card.get("current_guard", player_card.get("guard", 0)) or 0) - damage
        else:
            damage = apply_turn_damage(match, "player", damage)
        result = {
            "outcome": "Defeat",
            "winner": "bot",
            "damage": {"player": damage, "bot": 0},
            "message": f"{bot_card['name']} beats {player_card['name']}. {'Attacker loses' if persistent_field else 'You take'} {damage} damage.",
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
    if winner == "player":
        attacker_key = ability_key(player_card)
        if attacker_key in {"molten_bite", "inferno_bite", "fire_burn"}:
            status_stack.push_effect({"type": "status", "side": "bot", "status": "burn", "potency": 1, "turns": 2})
        if attacker_key == "shadow_decay":
            status_stack.push_effect({"type": "status", "side": "bot", "status": "decay", "potency": 1, "turns": 2})
        if attacker_key in {"shadow_lifesteal", "shadow_drain"}:
            status_stack.push_effect({"type": "heal", "side": "player", "amount": 2})
        if ability_key(player_card) == "water_heal":
            status_stack.push_effect({"type": "heal", "side": "player", "amount": 2})
        if ability_key(player_card) == "water_cleanse":
            status_stack.push_effect({"type": "cleanse", "side": "player"})
        if ability_key(player_card) == "earth_shield":
            status_stack.push_effect({"type": "shield", "side": "player", "amount": 2, "turns": 2})
    elif winner == "bot":
        attacker_key = ability_key(bot_card)
        if attacker_key in {"molten_bite", "inferno_bite", "fire_burn"}:
            status_stack.push_effect({"type": "status", "side": "player", "status": "burn", "potency": 1, "turns": 2})
        if attacker_key == "shadow_decay":
            status_stack.push_effect({"type": "status", "side": "player", "status": "decay", "potency": 1, "turns": 2})
        if attacker_key in {"shadow_lifesteal", "shadow_drain"}:
            status_stack.push_effect({"type": "heal", "side": "bot", "amount": 2})
        if ability_key(bot_card) == "water_heal":
            status_stack.push_effect({"type": "heal", "side": "bot", "amount": 2})
        if ability_key(bot_card) == "water_cleanse":
            status_stack.push_effect({"type": "cleanse", "side": "bot"})
        if ability_key(bot_card) == "earth_shield":
            status_stack.push_effect({"type": "shield", "side": "bot", "amount": 2, "turns": 2})
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
    defeated_player = _remove_defeated_battlefield_cards(match["player"]) if persistent_field else []
    defeated_bot = _remove_defeated_battlefield_cards(match["bot"]) if persistent_field else []
    defeated_events = []
    for defeated in defeated_player + defeated_bot:
        message = f"{defeated['name']} is destroyed."
        ability_events.append(message)
        defeated_events.append(message)
        match["log"].append(f"Turn {match['turn']:02d}   {message}")
        append_event(match, "MONSTER_DESTROYED", payload={"card_id": defeated["id"], "instance_id": defeated["instance_id"]}, message=message)
    result["ability_events"] = ability_events
    match["result"] = result
    if persistent_field and defeated_events:
        result["message"] = f"{result['message']} {' '.join(defeated_events)}"
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
        + len(side.get("battlefield", []))
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

    if is_spell(player_card):
        return _resolve_spell_card(match, "player", player_card)
    if is_trap(player_card):
        return _arm_trap_card(match, "player", player_card)
    if not is_monster(player_card):
        raise RebirthError("Only monster, spell and trap cards can be played.", "invalid_card")

    evolve_bot_if_ready(match)
    summoned = _summon_monster_card(match, "player", player_card)
    player_result = deepcopy(match.get("result") or {})
    bot_summoned = _bot_auto_summon(match)
    if bot_summoned:
        match["result"] = player_result
        match["result"]["message"] = f"{summoned['name']} enters the battlefield. Bot answers by summoning {bot_summoned['name']}."
        match["result"]["ability_events"] = [f"Bot summoned {bot_summoned['name']}."]
    if not match["is_finished"]:
        finish_if_exhausted(match)
    return match


def declare_attack(match, *, attacker_instance_id=None, target_instance_id=None):
    if match.get("is_finished"):
        raise RebirthError("Match is already finished.", "match_finished")
    if match.get("phase") not in {PHASE_CHOOSE, PHASE_RESULT}:
        raise RebirthError("Attack is not available in this phase.", "invalid_phase")
    if not is_main_phase(match) and match.get("phase") != PHASE_RESULT:
        raise RebirthError(f"Attacks can only be declared during MAIN_PHASE. Current phase: {current_turn_phase(match)}.", "invalid_phase")
    if not attacker_instance_id:
        raise RebirthError("attacker_instance_id is required.", "missing_attacker")

    _attacker_index, attacker = _find_battlefield_card(match["player"], attacker_instance_id)
    if attacker is None:
        raise RebirthError("Attacker is not on your battlefield.", "invalid_attacker")
    if attacker.get("exhausted") or attacker.get("has_attacked"):
        raise RebirthError("This monster has already attacked this turn.", "attacker_exhausted")

    target = None
    if target_instance_id:
        _target_index, target = _find_battlefield_card(match["bot"], target_instance_id)
        if target is None:
            raise RebirthError("Target is not on the bot battlefield.", "invalid_target")
    elif match["bot"].get("battlefield"):
        raise RebirthError("Direct attack is blocked while the bot controls defenders.", "defenders_block_direct")

    append_command(
        match,
        "DECLARE_ATTACK",
        actor="player",
        payload={"attacker_instance_id": attacker_instance_id, "target_instance_id": target_instance_id},
    )

    set_turn_phase(match, TurnPhase.COMBAT_PHASE)
    match["player"]["played_card"] = attacker
    attacker["exhausted"] = True
    attacker["has_attacked"] = True

    if target_instance_id:
        match["bot"]["played_card"] = target
        result = resolve_turn(match, attacker, target, persistent_field=True)
    else:
        result = _resolve_unanswered_attack(match, attacker)

    if not match["is_finished"]:
        finish_if_exhausted(match)
    return result


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
    if match.get("phase") not in {PHASE_RESULT, PHASE_CHOOSE}:
        raise RebirthError("Next turn is available only from the main phase or after combat.", "invalid_phase")

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
    _ready_battlefield(match["player"])
    _ready_battlefield(match["bot"])
    _refresh_energy_for_turn(match)
    _bot_auto_summon(match)
    match["result"] = None
    match["last_clash"] = None
    match["phase"] = PHASE_CHOOSE
    set_turn_phase(match, TurnPhase.MAIN_PHASE)
    match["log"].append(f"Turn {match['turn']:02d}   Choose a card.")
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
