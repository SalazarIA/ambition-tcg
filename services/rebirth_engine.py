from copy import deepcopy
import hashlib

from services.rebirth_bot import ability_priority, choose_bot_attack, choose_response
from services.rebirth_cards import CARD_ABILITY_KEYS, create_card_instance, get_card, is_monster, is_spell, is_trap
from services.rebirth_contracts import PHASE_CHOOSE, PHASE_FINISHED, PHASE_RESULT, RebirthError
from services.rebirth_effects import (
    EffectBus,
    PRIORITY_ACTIVE_SPELL,
    PRIORITY_INTERRUPT,
    PRIORITY_PASSIVE_TRIGGER,
    apply_legendary_passives,
    cleanup_defeated_units,
    expire_statuses_for_trigger,
    resolve_effect_sequence,
    resolve_status_ticks,
)
from services.rebirth_events import append_command, append_event, append_snapshot, new_effect_chain_id
from services.rebirth_state import (
    FIELD_SLOT_COUNT,
    RebirthStateError,
    TurnPhase,
    available_evolutions,
    clear_played_cards,
    compact_battlefield,
    create_match,
    current_turn_phase,
    draw_to_hand_size,
    field_slots,
    is_main_phase,
    remove_from_hand,
    set_turn_phase,
)


ENGINE_ABILITY_KEYS = set(CARD_ABILITY_KEYS.values())
REDUCER_INLINE_RUNTIME_MODES = {"replay", "audit", "network_sync", "pvp_sync"}


def configure_runtime_execution(match, *, runtime_mode=None, apply_reducers_inline=None):
    mode = str(runtime_mode or match.get("_runtime_mode") or "singleplayer")
    if apply_reducers_inline is None:
        apply_reducers_inline = mode in REDUCER_INLINE_RUNTIME_MODES
    match["_runtime_mode"] = mode
    match["_apply_reducers_inline"] = bool(apply_reducers_inline)
    return match


def start_match(
    seed=None,
    player_card_ids=None,
    player_name="Você",
    bot_profile_id=None,
    runtime_mode="singleplayer",
    apply_reducers_inline=None,
    first_duel=False,
):
    return create_match(
        seed=seed,
        player_card_ids=player_card_ids,
        player_name=player_name,
        bot_profile_id=bot_profile_id,
        runtime_mode=runtime_mode,
        apply_reducers_inline=apply_reducers_inline,
        first_duel=first_duel,
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
    return str(card.get("ability_name") or card.get("name") or "Habilidade")


def clash_attack(card, opponent_card, *, turn=1):
    attack = card_attack(card)
    events = []
    key = ability_key(card)
    if key == "high_guard" and card_guard(opponent_card) <= 3:
        attack += 1
        events.append(f"{card['name']} usou Guarda Alta para +1 de ataque no combate.")
    elif key == "silent_pursuit" and int(turn or 1) <= 2:
        attack += 1
        events.append(f"{card['name']} usou Perseguição Silenciosa para +1 de ataque inicial.")
    elif key == "fire_surge" and int(turn or 1) <= 2:
        attack += 2
        events.append(f"{card['name']} avançou para +2 de ataque inicial.")
    elif key == "water_tide" and int(turn or 1) >= 3:
        attack += 2
        events.append(f"{card['name']} surfou a maré crescente para +2 de ataque.")
    elif key == "earth_fortify":
        bonus = min(2, max(0, card_guard(card) // 4))
        if bonus:
            attack += bonus
            events.append(f"{card['name']} converteu guarda em +{bonus} de ataque.")
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
        events.append(f"{player_card['name']} desempatou contra um alvo ferido.")
        return "player", {"player_attack": player_attack, "bot_attack": bot_attack, "events": events}
    if bot_priority > player_priority:
        events.append(f"{bot_card['name']} desempatou contra um alvo ferido.")
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
        events.append(f"{attacker['name']} explorou a ferida para +2 de dano.")
    elif attacker_key == "apex_rend" and defender_wounded:
        amount += 3
        events.append(f"{attacker['name']} rasgou a ferida antiga para +3 de dano.")
    elif attacker_key == "molten_bite":
        amount += 1
        events.append(f"{attacker['name']} adicionou +1 de dano com Molten Bite.")
    elif attacker_key == "inferno_bite":
        amount += 3
        events.append(f"{attacker['name']} adicionou +3 de dano com Inferno Bite.")
    elif attacker_key == "bleed_mark":
        amount += 1
        events.append(f"{attacker['name']} marcou o alvo para +1 de dano.")
    elif attacker_key == "storm_dive" and card_guard(defender) <= 3:
        amount += 2
        events.append(f"{attacker['name']} atravessou a guarda baixa para +2 de dano.")
    elif attacker_key == "immovable":
        amount += 2
        events.append(f"{attacker['name']} transformou guarda em +2 de contra-dano.")
    elif attacker_key == "fire_direct":
        amount += 2
        events.append(f"{attacker['name']} causou +2 de dano direto de fogo.")
    elif attacker_key == "fire_execute" and defender_wounded:
        # v69: nerf de +3 → +2. Coalheart Runner (custo 1) tinha 124 procs em
        # 60 partidas trivializando finishes; reduzir o pico mantém a identidade
        # de execute mas elimina o swing barato. tie_priority continua dando o
        # desempate em alvos feridos, então o "papel" da carta permanece.
        amount += 2
        events.append(f"{attacker['name']} finalizou o alvo ferido para +2 de dano.")
    elif attacker_key == "shadow_decay":
        amount += 1
        events.append(f"{attacker['name']} abriu uma ferida de deterioração para +1 de dano.")
    elif attacker_key == "shadow_drain":
        amount += 1
        events.append(f"{attacker['name']} drenou +1 de dano pelas sombras.")

    if attacker_key == "fortress_hit":
        before_minimum = amount
        amount = max(3, amount)
        if amount > before_minimum:
            events.append(f"{attacker['name']} garantiu 3 de dano com Fortress Hit.")

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
            events.append(f"{defender['name']} reduziu o dano recebido em {before_reduction - amount}.")

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
        match["log"].append("Vitória. O bot ficou sem vida.")
    elif match["winner"] == "bot":
        match["log"].append("Derrota. Você ficou sem vida.")
    else:
        match["log"].append("Clash final. Os dois lados caíram juntos.")
    append_event(
        match,
        "MATCH_FINISHED",
        payload={"winner": match["winner"], "player_hp": player_hp, "bot_hp": bot_hp},
        message=match["log"][-1],
    )
    append_snapshot(match, "MATCH_FINISHED")
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
        message = "O duelo chegou à exaustão. Você sobrevive com mais PV e vence."
    elif bot_hp > player_hp:
        winner = "bot"
        outcome = "Defeat"
        message = "O duelo chegou à exaustão. O bot sobrevive com mais PV e vence."
    else:
        winner = "clash"
        outcome = "Clash"
        message = "O duelo chegou à exaustão com PV iguais. A partida termina em clash final."

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
    append_snapshot(match, "MATCH_EXHAUSTED")
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
        raise RebirthError(f"Mana insuficiente para jogar {card['name']}.", "not_enough_energy")
    side["energy"] = current - cost
    return cost


def _refresh_energy_for_turn(match):
    # v55 balance: piso de mana é 2, não 1 — T1 ficava sem ar (1 invocação
    # custo-1 e fim). T1=2, T2=2 (idêntico ao T1, mas garante uma magia + um
    # monstro), T3=3, ..., T10+=10 (mesma capa final).
    energy = min(10, max(2, int(match.get("turn", 1) or 1)))
    for side_name in ("player", "bot"):
        side = match[side_name]
        side["max_energy"] = energy
        side["energy"] = energy


def _ready_battlefield(side):
    for card in compact_battlefield(side):
        card["exhausted"] = False
        card["has_attacked"] = False
        card["has_acted"] = False


def _prepare_summoned_monster(card):
    summoned = deepcopy(card)
    summoned["current_guard"] = int(summoned.get("guard", 0) or 0)
    summoned["max_guard"] = int(summoned.get("guard", 0) or 0)
    summoned["exhausted"] = False
    summoned["has_attacked"] = False
    summoned["has_acted"] = False
    return summoned


def _find_battlefield_card(side, instance_id):
    for index, card in enumerate(field_slots(side)):
        if card and card.get("instance_id") == instance_id:
            return index, card
    return None, None


def _battlefield_slots_available(side):
    return sum(1 for card in field_slots(side) if card is None)


def _first_empty_battlefield_slot(side):
    for index, card in enumerate(field_slots(side)):
        if card is None:
            return index
    return None


def _resolve_battlefield_slot(side, field_slot=None):
    if _battlefield_slots_available(side) <= 0:
        raise RebirthError("Todos os slots de duelo estão ocupados.", "battlefield_full")
    if field_slot is None or field_slot == "":
        slot = _first_empty_battlefield_slot(side)
    else:
        try:
            slot = int(field_slot)
        except (TypeError, ValueError) as exc:
            raise RebirthError("field_slot deve ser 0, 1 ou 2.", "invalid_slot") from exc
    if slot is None or slot < 0 or slot >= FIELD_SLOT_COUNT:
        raise RebirthError("field_slot está fora da zona de duelo ativa.", "invalid_slot")
    if field_slots(side)[slot] is not None:
        raise RebirthError("O slot de duelo já está ocupado.", "slot_occupied")
    return slot


def _hand_card(side, *, card_instance_id=None, card_id=None):
    for card in side.get("hand", []):
        if card_instance_id and card.get("instance_id") == card_instance_id:
            return card
        if not card_instance_id and card_id and card.get("id") == card_id:
            return card
    raise RebirthStateError("A carta não está na mão.")


def _opponent_side(side_name):
    return "bot" if side_name == "player" else "player"


def _require_command_dispatch(match):
    if match.get("_require_command_dispatcher") and int(match.get("_command_dispatch_depth", 0) or 0) <= 0:
        raise RebirthError("Ação Rebirth deve ser processada pelo CommandDispatcher.", "dispatcher_required")


def _resolve_spell_card(match, side_name, card):
    cost = _spend_card_cost(match, side_name, card)
    effect_chain_id = new_effect_chain_id(match, "spell")
    turn_label = f"Turno {match['turn']:02d}"
    actor_label = "Bot" if side_name == "bot" else "Você"
    match["log"].append(f"{turn_label}   {actor_label} lançou {card['name']}.")
    played_event = append_event(
        match,
        "CARD_PLAYED",
        actor=side_name,
        payload={"card_id": card["id"], "instance_id": card["instance_id"], "type": "SPELL", "cost": cost},
        message=match["log"][-1],
        effect_chain_id=effect_chain_id,
    )
    effect_events = resolve_effect_sequence(
        match,
        side_name,
        card.get("stack_effects") or [],
        effect_chain_id=effect_chain_id,
        parent_event_id=played_event["event_id"],
        root_event_id=played_event["root_event_id"],
        priority_level=PRIORITY_ACTIVE_SPELL,
        source_card=card,
    )
    discard_bus = EffectBus(match, effect_chain_id=effect_chain_id)
    discard_bus.dispatch(
        "CARD_DISCARDED",
        actor=side_name,
        source_card_id=card.get("id"),
        target_id=side_name,
        owner_id=side_name,
        payload={"side": side_name, "card": deepcopy(card), "reason": "spell_resolved"},
        order=900,
        priority_level=PRIORITY_ACTIVE_SPELL,
        stable_entity_id=card.get("instance_id"),
        parent_event_id=played_event["event_id"],
        root_event_id=played_event["root_event_id"],
    )
    discard_bus.flush()
    match["last_clash"] = None
    match["result"] = {
        "outcome": "Spell",
        "winner": None,
        "damage": {"player": 0, "bot": 0},
        "message": f"{card['name']} resolveu seus efeitos na pilha.",
        "ability_events": effect_events,
        "effective_attack": {"player": 0, "bot": 0},
    }
    if effect_events:
        match["result"]["message"] = f"{match['result']['message']} {' '.join(effect_events)}"
    append_event(
        match,
        "SPELL_RESOLVED",
        actor=side_name,
        payload={"card_id": card["id"], "effects": deepcopy(card.get("stack_effects") or [])},
        message=match["result"]["message"],
        effect_chain_id=effect_chain_id,
        parent_event_id=played_event["event_id"],
        root_event_id=played_event["root_event_id"],
    )
    for event in effect_events:
        append_event(match, "ABILITY_TRIGGERED", actor=side_name, payload={"message": event}, message=event)
    finish_if_needed(match)
    if not match.get("is_finished"):
        match["phase"] = PHASE_CHOOSE
        set_turn_phase(match, TurnPhase.MAIN_PHASE)
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
        "message": f"{card['name']} foi armada virada para baixo.",
        "ability_events": [],
        "effective_attack": {"player": 0, "bot": 0},
    }
    turn_label = f"Turno {match['turn']:02d}"
    actor_label = "Bot" if side_name == "bot" else "Você"
    match["log"].append(f"{turn_label}   {actor_label} armou uma armadilha virada para baixo.")
    append_event(
        match,
        "TRAP_ARMED",
        actor=side_name,
        payload={"card_id": card["id"], "instance_id": card["instance_id"], "slot": armed["slot"], "cost": cost, "card": deepcopy(armed)},
        message=match["log"][-1],
    )
    match["phase"] = PHASE_CHOOSE
    set_turn_phase(match, TurnPhase.MAIN_PHASE)
    return match


def _summon_monster_card(match, side_name, card, field_slot=None):
    side = match[side_name]
    slot = _resolve_battlefield_slot(side, field_slot)
    cost = _spend_card_cost(match, side_name, card)
    summoned = _prepare_summoned_monster(card)
    summoned["field_slot"] = slot
    summoned["slot"] = slot + 1
    field_slots(side)[slot] = summoned
    compact_battlefield(side)
    side["played_card"] = summoned
    match["last_clash"] = None
    match["result"] = {
        "outcome": "Summon",
        "winner": None,
        "damage": {"player": 0, "bot": 0},
        "message": f"{summoned['name']} entra em campo.",
        "ability_events": [],
        "effective_attack": {"player": 0, "bot": 0},
    }
    turn_label = f"Turno {match['turn']:02d}"
    actor_label = "Bot" if side_name == "bot" else "Você"
    verb = "invocou" if actor_label == "Você" else "invocou"
    match["log"].append(f"{turn_label}   {actor_label} {verb} {summoned['name']}.")
    played_event = append_event(
        match,
        "CARD_PLAYED",
        actor=side_name,
        payload={"card_id": summoned["id"], "instance_id": summoned["instance_id"], "type": "MONSTER", "cost": cost},
        message=match["log"][-1],
    )
    summoned_event = append_event(
        match,
        "MONSTER_SUMMONED",
        actor=side_name,
        source_card_id=summoned["id"],
        target_id=summoned["instance_id"],
        owner_id=side_name,
        payload={
            "card_id": summoned["id"],
            "instance_id": summoned["instance_id"],
            "slot": slot + 1,
            "field_slot": slot,
            "current_guard": summoned["current_guard"],
            "card": deepcopy(summoned),
        },
        message=match["result"]["message"],
        parent_event_id=played_event["event_id"],
        root_event_id=played_event["root_event_id"],
    )
    passive_events = apply_legendary_passives(
        match,
        "CARD_SUMMONED",
        {
            "source_card": summoned,
            "owner_side": side_name,
            "effect_chain_id": new_effect_chain_id(match, "summon"),
            "parent_event_id": summoned_event["event_id"],
            "root_event_id": summoned_event["root_event_id"],
        },
    )
    if passive_events:
        match["result"]["ability_events"] = passive_events
        match["result"]["message"] = f"{match['result']['message']} {' '.join(passive_events)}"
    match["phase"] = PHASE_CHOOSE
    set_turn_phase(match, TurnPhase.MAIN_PHASE)
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
    player_card = match["player"].get("played_card") or (compact_battlefield(match["player"])[0] if compact_battlefield(match["player"]) else None)
    chosen = None
    if player_card:
        decision = choose_response(
            affordable,
            player_card,
            profile_id=profile_id,
            turn=match.get("turn", 1),
            player_wounded=match["player"].get("wounded", False),
            bot_wounded=match["bot"].get("wounded", False),
            match_id=match.get("match_id"),
            bot_battlefield=compact_battlefield(match["bot"]),
            player_battlefield=compact_battlefield(match["player"]),
            player_hp=match["player"].get("hp", 30),
        )
        if decision:
            chosen = next((card for card in affordable if card.get("instance_id") == decision.get("instance_id")), None)
            if chosen is None:
                chosen = next((card for card in affordable if card.get("id") == decision.get("id")), None)
    if chosen is None:
        if profile_id == "aggressive":
            chosen = sorted(affordable, key=lambda card: (card_attack(card), ability_priority(card), card_guard(card), card["name"]))[-1]
        elif profile_id == "opportunist":
            chosen = sorted(affordable, key=lambda card: (ability_priority(card), card_attack(card), card_guard(card), card["name"]))[-1]
        else:
            chosen = sorted(affordable, key=lambda card: (card_guard(card), card_attack(card), ability_priority(card), card["name"]))[-1]
    append_event(
        match,
        "BOT_DECISION",
        actor="bot",
        payload={
            "profile_id": profile_id,
            "card_id": chosen["id"],
            "instance_id": chosen["instance_id"],
            "response_to": player_card.get("id") if player_card else None,
        },
        message=f"O bot escolheu {chosen['name']}.",
    )
    bot_card = remove_from_hand(match["bot"], card_instance_id=chosen["instance_id"])
    return _summon_monster_card(match, "bot", bot_card)


def _apply_trap_effect(match, owner_side, trap, owner_card, opponent_card):
    effect = str(trap.get("trap_effect") or "").strip().lower()
    effect_chain_id = trap.get("effect_chain_id") or new_effect_chain_id(match, "interrupt")
    bus = EffectBus(match, effect_chain_id=effect_chain_id)
    messages = [f"{trap['name']} foi revelada."]
    opponent_side = _opponent_side(owner_side)
    order = 100
    opponent_instance_id = (opponent_card or {}).get("instance_id")
    if effect == "negate_attack":
        bus.dispatch(
            "STAT_MODIFIER_APPLIED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=opponent_instance_id,
            owner_id=owner_side,
            payload={"stat": "attack", "amount": -card_attack(opponent_card), "duration": "combat", "side": opponent_side},
            message=f"{trap['name']} anula o ataque de {opponent_card['name']}.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_instance_id,
        )
        messages.append(f"{trap['name']} anula o ataque de {opponent_card['name']}.")
    elif effect == "reflect_damage":
        bus.dispatch(
            "DAMAGE_RESOLVED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=opponent_side,
            owner_id=owner_side,
            payload={"side": opponent_side, "amount": 3},
            message=f"{match[opponent_side]['name']} sofre 3 de dano da pilha.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_side,
        )
        messages.append(f"{trap['name']} reflete 3 de dano.")
    elif effect == "burn_attacker":
        bus.dispatch(
            "STATUS_APPLIED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=opponent_side,
            owner_id=owner_side,
            payload={"side": opponent_side, "status": "burn", "potency": 1, "turns": 2},
            message=f"{match[opponent_side]['name']} é afetado por queimadura.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_side,
        )
        messages.append(f"{trap['name']} marca o atacante com queimadura.")
    elif effect == "shield_owner":
        bus.dispatch(
            "SHIELD_APPLIED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=owner_side,
            owner_id=owner_side,
            payload={"side": owner_side, "amount": 3, "turns": 2},
            message=f"{match[owner_side]['name']} recebe um escudo de 3 pontos.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=owner_side,
        )
        messages.append(f"{trap['name']} ergue um escudo.")
    elif effect == "cleanse_owner":
        bus.dispatch(
            "STATUS_CLEANSED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=owner_side,
            owner_id=owner_side,
            payload={"side": owner_side, "removed": sorted((match[owner_side].get("statuses") or {}).keys())},
            message=f"{match[owner_side]['name']} remove efeitos ativos.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=owner_side,
        )
        messages.append(f"{trap['name']} purifica seu controlador.")
    elif effect == "freeze_attacker":
        bus.dispatch(
            "STAT_MODIFIER_APPLIED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=opponent_instance_id,
            owner_id=owner_side,
            payload={"stat": "attack", "amount": -2, "duration": "combat", "side": opponent_side},
            message=f"{trap['name']} reduz o ataque de {opponent_card['name']} em 2.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_instance_id,
        )
        bus.dispatch(
            "STATUS_APPLIED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=opponent_side,
            owner_id=owner_side,
            payload={"side": opponent_side, "status": "freeze", "potency": 1, "turns": 1},
            message=f"{match[opponent_side]['name']} é afetado por congelamento.",
            order=order + 1,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_side,
            chain_from_previous=True,
        )
        messages.append(f"{trap['name']} congela o atacante para -2 de ataque.")
    elif effect == "drain_attacker":
        bus.dispatch(
            "DAMAGE_RESOLVED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=opponent_side,
            owner_id=owner_side,
            payload={"side": opponent_side, "amount": 2},
            message=f"{match[opponent_side]['name']} sofre 2 de dano da pilha.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_side,
        )
        bus.dispatch(
            "HEALTH_RECOVERED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=owner_side,
            owner_id=owner_side,
            payload={"side": owner_side, "amount": 2},
            message=f"{match[owner_side]['name']} recupera 2 PV.",
            order=order + 1,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=owner_side,
            chain_from_previous=True,
        )
        messages.append(f"{trap['name']} drena 2 PV.")
    elif effect == "destroy_shield":
        target_id = opponent_side
        payload = {"side": opponent_side, "status": "shield"}
        message = f"O escudo de {match[opponent_side]['name']} foi destruído."
        shielded_units = sorted(
            (
                card
                for card in compact_battlefield(match[opponent_side])
                if "aegis_sentinel_shield" in (card.get("statuses") or {})
            ),
            key=lambda card: (int(card.get("field_slot", 0) or 0), str(card.get("instance_id") or "")),
        )
        if "shield" not in (match[opponent_side].get("statuses") or {}) and shielded_units:
            protected = shielded_units[0]
            shield = (protected.get("statuses") or {}).get("aegis_sentinel_shield") or {}
            target_id = protected.get("instance_id")
            payload = {
                "side": opponent_side,
                "status": "aegis_sentinel_shield",
                "instance_id": target_id,
                "guard_bonus": max(0, int(shield.get("guard", 0) or 0)),
                "armor_break": True,
            }
            message = f"{protected['name']} perde sua armadura temporária."
        bus.dispatch(
            "SHIELD_BROKEN",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=target_id,
            owner_id=owner_side,
            payload=payload,
            message=message,
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_side,
        )
        messages.append(f"{trap['name']} quebra o escudo adversário.")
    elif effect == "heal_owner":
        bus.dispatch(
            "HEALTH_RECOVERED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=owner_side,
            owner_id=owner_side,
            payload={"side": owner_side, "amount": 3},
            message=f"{match[owner_side]['name']} recupera 3 PV.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=owner_side,
        )
        messages.append(f"{trap['name']} recupera 3 PV.")
    elif effect == "weaken_attacker":
        bus.dispatch(
            "STAT_MODIFIER_APPLIED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=opponent_instance_id,
            owner_id=owner_side,
            payload={"stat": "attack", "amount": -2, "duration": "combat", "side": opponent_side},
            message=f"{trap['name']} reduz o ataque de {opponent_card['name']} em 2.",
            order=order,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_instance_id,
        )
        bus.dispatch(
            "STATUS_APPLIED",
            actor=owner_side,
            source_card_id=trap.get("id"),
            target_id=opponent_side,
            owner_id=owner_side,
            payload={"side": opponent_side, "status": "weaken", "potency": 2, "turns": 1},
            message=f"{match[opponent_side]['name']} sofre fraqueza de 2.",
            order=order + 1,
            priority_level=PRIORITY_INTERRUPT,
            stable_entity_id=opponent_side,
            chain_from_previous=True,
        )
        messages.append(f"{trap['name']} enfraquece o atacante.")
    return messages + [event.get("message") for event in bus.flush() if event.get("message")]


def _resolve_combat_traps(match, player_card, bot_card):
    events = []
    for owner_side, owner_card, opponent_card in (
        ("player", player_card, bot_card),
        ("bot", bot_card, player_card),
    ):
        if owner_card:
            _owner_index, refreshed_owner = _find_battlefield_card(match[owner_side], owner_card.get("instance_id"))
            owner_card = refreshed_owner or owner_card
        if opponent_card:
            _opponent_index, refreshed_opponent = _find_battlefield_card(match[_opponent_side(owner_side)], opponent_card.get("instance_id"))
            opponent_card = refreshed_opponent or opponent_card
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
            match[owner_side].setdefault("discard", []).append(triggered)
            append_event(
                match,
                "TRAP_TRIGGERED",
                actor=owner_side,
                payload={"card_id": trap["id"], "instance_id": trap.get("instance_id"), "effect": trap.get("trap_effect"), "card": deepcopy(triggered)},
                message=events[-1] if events else f"{trap['name']} foi acionada.",
            )
        match[owner_side]["traps"] = remaining_traps
    return events


def _resolve_unanswered_attack(match, player_card, *, effect_chain_id=None, parent_event_id=None, root_event_id=None):
    effect_chain_id = effect_chain_id or new_effect_chain_id(match, "combat")
    set_turn_phase(match, TurnPhase.COMBAT_PHASE)
    match["player"]["played_card"] = player_card
    damage = max(1, card_attack(player_card))
    damage = apply_turn_damage(match, "bot", damage)
    result = {
        "outcome": "Victory",
        "winner": "player",
        "damage": {"player": 0, "bot": damage},
        "message": f"{player_card['name']} ataca diretamente. Bot sofre {damage} de dano.",
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
        payload={
            "player_card_id": player_card["id"],
            "bot_card_id": None,
            "outcome": result["outcome"],
            "winner": "player",
            "damage": deepcopy(result["damage"]),
            "effective_attack": deepcopy(result["effective_attack"]),
            "player_card": deepcopy(player_card),
            "bot_card": None,
        },
        message=result["message"],
        effect_chain_id=effect_chain_id,
        parent_event_id=parent_event_id,
        root_event_id=root_event_id,
    )
    damage_event = append_event(
        match,
        "DAMAGE_RESOLVED",
        actor="player",
        source_card_id=player_card.get("id"),
        target_id="bot",
        owner_id="player",
        effect_chain_id=effect_chain_id,
        parent_event_id=parent_event_id,
        root_event_id=root_event_id,
        payload={"player": 0, "bot": damage, "player_hp": match["player"]["hp"], "bot_hp": match["bot"]["hp"], "direct": True},
    )
    result["ability_events"].extend(
        expire_statuses_for_trigger(
            match,
            "DAMAGE_RESOLVED",
            {"effect_chain_id": effect_chain_id, "parent_event_id": damage_event["event_id"], "root_event_id": damage_event["root_event_id"]},
        )
    )
    finish_if_needed(match)
    if not match.get("is_finished"):
        match["phase"] = PHASE_RESULT
        set_turn_phase(match, TurnPhase.END_PHASE)
    return result


def _resolve_unanswered_bot_attack(match, bot_card, *, effect_chain_id=None, parent_event_id=None, root_event_id=None):
    effect_chain_id = effect_chain_id or new_effect_chain_id(match, "bot-combat")
    set_turn_phase(match, TurnPhase.COMBAT_PHASE)
    match["bot"]["played_card"] = bot_card
    damage = apply_turn_damage(match, "player", max(1, card_attack(bot_card)))
    result = {
        "outcome": "Defeat",
        "winner": "bot",
        "damage": {"player": damage, "bot": 0},
        "message": f"{bot_card['name']} ataca diretamente. Você sofre {damage} de dano.",
        "ability_events": [],
        "effective_attack": {"player": 0, "bot": card_attack(bot_card)},
    }
    match["result"] = result
    match["last_clash"] = {
        "player_card": None,
        "bot_card": deepcopy(bot_card),
        "outcome": result["outcome"],
        "ability_events": [],
        "effective_attack": deepcopy(result["effective_attack"]),
    }
    match["log"].append(result["message"])
    append_event(
        match,
        "CLASH_RESOLVED",
        actor="bot",
        payload={
            "player_card_id": None,
            "bot_card_id": bot_card["id"],
            "outcome": result["outcome"],
            "winner": "bot",
            "damage": deepcopy(result["damage"]),
            "effective_attack": deepcopy(result["effective_attack"]),
            "player_card": None,
            "bot_card": deepcopy(bot_card),
        },
        message=result["message"],
        effect_chain_id=effect_chain_id,
        parent_event_id=parent_event_id,
        root_event_id=root_event_id,
    )
    damage_event = append_event(
        match,
        "DAMAGE_RESOLVED",
        actor="bot",
        source_card_id=bot_card.get("id"),
        target_id="player",
        owner_id="bot",
        effect_chain_id=effect_chain_id,
        parent_event_id=parent_event_id,
        root_event_id=root_event_id,
        payload={"player": damage, "bot": 0, "player_hp": match["player"]["hp"], "bot_hp": match["bot"]["hp"], "direct": True},
    )
    result["ability_events"].extend(
        expire_statuses_for_trigger(
            match,
            "DAMAGE_RESOLVED",
            {"effect_chain_id": effect_chain_id, "parent_event_id": damage_event["event_id"], "root_event_id": damage_event["root_event_id"]},
        )
    )
    finish_if_needed(match)
    return result


def _bot_auto_attack(match, *, effect_chain_id=None):
    if match.get("is_finished"):
        return None
    decision = choose_bot_attack(
        compact_battlefield(match["bot"]),
        compact_battlefield(match["player"]),
        player_hp=match["player"].get("hp", 30),
        turn=match.get("turn", 1),
        player_wounded=match["player"].get("wounded", False),
        bot_wounded=match["bot"].get("wounded", False),
    )
    if not decision:
        return None
    _attacker_index, attacker = _find_battlefield_card(match["bot"], decision.get("attacker_instance_id"))
    if not attacker:
        return None
    _target_index, target = _find_battlefield_card(match["player"], decision.get("target_instance_id"))
    chain_id = effect_chain_id or new_effect_chain_id(match, "bot-attack")
    attack_event = append_event(
        match,
        "ATTACK_DECLARED",
        actor="bot",
        source_card_id=attacker.get("id"),
        target_id=(target or {}).get("instance_id"),
        owner_id="bot",
        effect_chain_id=chain_id,
        payload={
            "attacker_card_id": attacker.get("id"),
            "attacker_instance_id": attacker.get("instance_id"),
            "target_instance_id": (target or {}).get("instance_id"),
            "automated": True,
        },
        message=f"{attacker['name']} inicia o ataque do bot.",
    )
    attacker["exhausted"] = True
    attacker["has_attacked"] = True
    attacker["has_acted"] = True
    match["bot"]["played_card"] = attacker
    if target:
        match["player"]["played_card"] = target
        return resolve_turn(
            match,
            target,
            attacker,
            persistent_field=True,
            attacking_side="bot",
            effect_chain_id=chain_id,
            parent_event_id=attack_event["event_id"],
            root_event_id=attack_event["root_event_id"],
        )
    return _resolve_unanswered_bot_attack(
        match,
        attacker,
        effect_chain_id=chain_id,
        parent_event_id=attack_event["event_id"],
        root_event_id=attack_event["root_event_id"],
    )


def resolve_turn(
    match,
    player_card,
    bot_card,
    *,
    persistent_field=False,
    attacking_side="player",
    effect_chain_id=None,
    parent_event_id=None,
    root_event_id=None,
):
    effect_chain_id = effect_chain_id or new_effect_chain_id(match, "combat")
    trap_events = _resolve_combat_traps(match, player_card, bot_card)
    _player_index, refreshed_player_card = _find_battlefield_card(match["player"], player_card.get("instance_id"))
    _bot_index, refreshed_bot_card = _find_battlefield_card(match["bot"], bot_card.get("instance_id"))
    player_card = refreshed_player_card or player_card
    bot_card = refreshed_bot_card or bot_card
    winner, clash = compare_clash(match, player_card, bot_card)
    ability_events = list(trap_events) + list(clash["events"])
    hero_damage = {"player": 0, "bot": 0}
    if winner == "player":
        damage_payload = damage_details(player_card, bot_card, match["bot"].get("wounded", False))
        damage = damage_payload["amount"]
        ability_events.extend(damage_payload["events"])
        if persistent_field:
            guard_before = max(0, int(bot_card.get("current_guard", bot_card.get("guard", 0)) or 0))
            bot_card["current_guard"] = int(bot_card.get("current_guard", bot_card.get("guard", 0)) or 0) - damage
            breakthrough = min(2, max(0, damage - guard_before))
            if breakthrough:
                hero_damage["bot"] = apply_turn_damage(match, "bot", breakthrough)
                ability_events.append(f"Breakthrough: Bot sofre {hero_damage['bot']} de dano excedente.")
        else:
            damage = apply_turn_damage(match, "bot", damage)
        result = {
            "outcome": "Victory",
            "winner": "player",
            "damage": {"player": 0, "bot": damage},
            "message": f"{player_card['name']} venceu {bot_card['name']}. {'Alvo perde' if persistent_field else 'Bot sofre'} {damage} de dano.",
        }
    elif winner == "bot":
        damage_payload = damage_details(bot_card, player_card, match["player"].get("wounded", False))
        damage = damage_payload["amount"]
        ability_events.extend(damage_payload["events"])
        if persistent_field:
            guard_before = max(0, int(player_card.get("current_guard", player_card.get("guard", 0)) or 0))
            player_card["current_guard"] = int(player_card.get("current_guard", player_card.get("guard", 0)) or 0) - damage
            breakthrough = min(2, max(0, damage - guard_before))
            if breakthrough:
                hero_damage["player"] = apply_turn_damage(match, "player", breakthrough)
                ability_events.append(f"Breakthrough: Você sofre {hero_damage['player']} de dano excedente.")
        else:
            damage = apply_turn_damage(match, "player", damage)
        result = {
            "outcome": "Defeat",
            "winner": "bot",
            "damage": {"player": damage, "bot": 0},
            "message": f"{bot_card['name']} derrotou {player_card['name']}. {'Atacante perde' if persistent_field else 'Você sofre'} {damage} de dano.",
        }
    else:
        # Em combate no campo, um empate troca dano de Guarda entre as
        # criaturas sem marcar dano direto nos herois.
        clash_damage = {"player": 0, "bot": 0}
        clash_message = f"{player_card['name']} e {bot_card['name']} travam lâminas."
        if persistent_field:
            player_guard_damage = max(1, clash["bot_attack"])
            bot_guard_damage = max(1, clash["player_attack"])
            player_card["current_guard"] = int(player_card.get("current_guard", player_card.get("guard", 0)) or 0) - player_guard_damage
            bot_card["current_guard"] = int(bot_card.get("current_guard", bot_card.get("guard", 0)) or 0) - bot_guard_damage
            clash_damage = {"player": player_guard_damage, "bot": bot_guard_damage}
            clash_message += f" Ambos sofrem o golpe (você -{player_guard_damage} Guarda, bot -{bot_guard_damage} Guarda)."
        else:
            match["player"]["wounded"] = True
            match["bot"]["wounded"] = True
            clash_message += " Nenhum dano é causado."
        result = {
            "outcome": "Clash",
            "winner": None,
            "damage": clash_damage,
            "message": clash_message,
        }

    if persistent_field:
        result["hero_damage"] = hero_damage

    status_effects = []
    status_owner = result["winner"] if result.get("winner") in {"player", "bot"} else "system"
    if winner == "player":
        attacker_key = ability_key(player_card)
        if attacker_key in {"molten_bite", "inferno_bite", "fire_burn"}:
            status_effects.append({"type": "status", "side": "bot", "status": "burn", "potency": 1, "turns": 2})
        if attacker_key == "shadow_decay":
            status_effects.append({"type": "status", "side": "bot", "status": "decay", "potency": 1, "turns": 2})
        if attacker_key in {"shadow_lifesteal", "shadow_drain"}:
            status_effects.append({"type": "heal", "side": "player", "amount": 2})
        if ability_key(player_card) == "water_heal":
            status_effects.append({"type": "heal", "side": "player", "amount": 2})
        if ability_key(player_card) == "water_cleanse":
            status_effects.append({"type": "cleanse", "side": "player"})
        if ability_key(player_card) == "earth_shield":
            status_effects.append({"type": "shield", "side": "player", "amount": 2, "turns": 2})
    elif winner == "bot":
        attacker_key = ability_key(bot_card)
        if attacker_key in {"molten_bite", "inferno_bite", "fire_burn"}:
            status_effects.append({"type": "status", "side": "player", "status": "burn", "potency": 1, "turns": 2})
        if attacker_key == "shadow_decay":
            status_effects.append({"type": "status", "side": "player", "status": "decay", "potency": 1, "turns": 2})
        if attacker_key in {"shadow_lifesteal", "shadow_drain"}:
            status_effects.append({"type": "heal", "side": "bot", "amount": 2})
        if ability_key(bot_card) == "water_heal":
            status_effects.append({"type": "heal", "side": "bot", "amount": 2})
        if ability_key(bot_card) == "water_cleanse":
            status_effects.append({"type": "cleanse", "side": "bot"})
        if ability_key(bot_card) == "earth_shield":
            status_effects.append({"type": "shield", "side": "bot", "amount": 2, "turns": 2})
    status_events = resolve_effect_sequence(
        match,
        status_owner,
        status_effects,
        effect_chain_id=effect_chain_id,
        parent_event_id=parent_event_id,
        root_event_id=root_event_id,
        priority_level=PRIORITY_PASSIVE_TRIGGER,
        source_card=player_card if winner == "player" else bot_card if winner == "bot" else None,
    )
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
        effect_chain_id=effect_chain_id,
        payload={
            "player_card_id": player_card["id"],
            "bot_card_id": bot_card["id"],
            "outcome": result["outcome"],
            "winner": result["winner"],
            "effective_attack": deepcopy(result["effective_attack"]),
            "damage": deepcopy(result.get("damage") or {"player": 0, "bot": 0}),
            "hero_damage": deepcopy(result.get("hero_damage")) if persistent_field else None,
            "player_card": deepcopy(player_card),
            "bot_card": deepcopy(bot_card),
        },
        message=result["message"],
        parent_event_id=parent_event_id,
        root_event_id=root_event_id,
    )
    damage = result.get("damage") or {}
    damage_event = None
    if int(damage.get("player", 0) or 0) or int(damage.get("bot", 0) or 0):
        damage_event = append_event(
            match,
            "DAMAGE_RESOLVED",
            actor=result["winner"] or "system",
            source_card_id=(player_card if result["winner"] == "player" else bot_card).get("id") if result["winner"] else None,
            target_id="player" if int(damage.get("player", 0) or 0) else "bot",
            owner_id=result["winner"] or "system",
            effect_chain_id=effect_chain_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
            payload={
                "player": int(damage.get("player", 0) or 0),
                "bot": int(damage.get("bot", 0) or 0),
                "player_hp": match["player"]["hp"],
                "bot_hp": match["bot"]["hp"],
                "persistent_field": bool(persistent_field),
                "guard_damage": deepcopy(damage) if persistent_field else {},
                "hero_damage": deepcopy(hero_damage) if persistent_field else {},
                "player_instance_id": player_card.get("instance_id"),
                "bot_instance_id": bot_card.get("instance_id"),
            },
        )
        ability_events.extend(
            expire_statuses_for_trigger(
                match,
                "DAMAGE_RESOLVED",
                {"effect_chain_id": effect_chain_id, "parent_event_id": damage_event["event_id"], "root_event_id": damage_event["root_event_id"]},
            )
        )
    defeated_units = cleanup_defeated_units(
        match,
        effect_chain_id=effect_chain_id,
        parent_event_id=damage_event["event_id"] if damage_event else parent_event_id,
        root_event_id=(damage_event or {}).get("root_event_id") or root_event_id,
    ) if persistent_field else []
    defeated_events = []
    for defeated in defeated_units:
        message = f"{defeated['name']} foi destruído."
        ability_events.append(message)
        defeated_events.append(message)
        match["log"].append(f"Turno {match['turn']:02d}   {message}")
    result["ability_events"] = ability_events
    match["result"] = result
    if persistent_field and defeated_events:
        result["message"] = f"{result['message']} {' '.join(defeated_events)}"
    attacker_card = player_card if attacking_side == "player" else bot_card
    attacker_survived = bool(attacker_card) and int(attacker_card.get("current_guard", attacker_card.get("guard", 1)) or 0) > 0
    if attacker_survived:
        survived_parent = damage_event["event_id"] if damage_event else parent_event_id
        survived_event = append_event(
            match,
            "UNIT_SURVIVED_COMBAT",
            actor=attacking_side,
            source_card_id=attacker_card.get("id"),
            target_id=attacker_card.get("instance_id"),
            owner_id=attacking_side,
            effect_chain_id=effect_chain_id,
            parent_event_id=survived_parent,
            root_event_id=root_event_id,
            payload={"card_id": attacker_card.get("id"), "instance_id": attacker_card.get("instance_id"), "field_slot": attacker_card.get("field_slot")},
        )
        passive_events = apply_legendary_passives(
            match,
            "UNIT_SURVIVED_COMBAT",
            {
                "attacker_card": attacker_card,
                "attacker_side": attacking_side,
                "effect_chain_id": effect_chain_id,
                "parent_event_id": survived_event["event_id"],
                "root_event_id": survived_event["root_event_id"],
            },
        )
        ability_events.extend(passive_events)
        if passive_events:
            result["message"] = f"{result['message']} {' '.join(passive_events)}"
        result["ability_events"] = ability_events
        match["result"] = result
    if (
        int(damage.get("player", 0) or 0)
        or int(damage.get("bot", 0) or 0)
        or int(hero_damage.get("player", 0) or 0)
        or int(hero_damage.get("bot", 0) or 0)
    ):
        append_event(
            match,
            "DAMAGE_DEALT",
            effect_chain_id=effect_chain_id,
            payload={
                "player": int(damage.get("player", 0) or 0),
                "bot": int(damage.get("bot", 0) or 0),
                "hero_damage": deepcopy(hero_damage),
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
    return result


def _side_sequence(side):
    return (
        len(side.get("deck", []))
        + len(side.get("hand", []))
        + len(compact_battlefield(side))
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
    try:
        card = get_card(card_id)
    except ValueError as exc:
        raise RebirthError(str(exc), "invalid_card") from exc
    evolution_id = card.get("evolution_id")
    if not evolution_id:
        raise RebirthError("Este monstro não possui evolução MVP.", "duplicate_not_available")

    matches = [hand_card for hand_card in side["hand"] if hand_card["id"] == card_id]
    if len(matches) < 2:
        raise RebirthError("São necessários dois monstros iguais para evoluir.", "duplicate_not_available")

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
        match["log"].append(f"Turno {match['turn']:02d}   Bot evoluiu {card['name']} x2 em {evolved['name']}.")
    else:
        match["log"].append(f"Turno {match['turn']:02d}   {actor} x2 evoluiu para {evolved['name']}.")
    append_event(
        match,
        "CARD_EVOLVED",
        actor=side_name,
        payload={
            "source_card_id": card_id,
            "evolution_id": evolution_id,
            "consumed_instance_ids": list(evolved["evolved_from"]),
            "created_instance_id": evolved["instance_id"],
            "consumed_cards": deepcopy(consumed),
            "evolved_card": deepcopy(evolved),
        },
        message=match["log"][-1],
    )
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


def play_card(match, *, card_instance_id=None, card_id=None, field_slot=None):
    _require_command_dispatch(match)
    if match.get("is_finished"):
        raise RebirthError("A partida já terminou.", "match_finished")
    if match.get("phase") != PHASE_CHOOSE:
        raise RebirthError("Avance para o próximo turno antes de jogar outra carta.", "invalid_phase")
    if not is_main_phase(match):
        raise RebirthError(f"Cartas só podem ser jogadas na fase principal. Fase atual: {current_turn_phase(match)}.", "invalid_phase")
    if not card_instance_id and not card_id:
        raise RebirthError("Informe card_instance_id ou card_id.", "missing_card")

    try:
        preview_card = _hand_card(match["player"], card_instance_id=card_instance_id, card_id=card_id)
    except RebirthStateError as exc:
        raise RebirthError(str(exc), "invalid_card") from exc

    if is_monster(preview_card):
        _resolve_battlefield_slot(match["player"], field_slot)
    elif not is_spell(preview_card) and not is_trap(preview_card):
        raise RebirthError("Só é possível jogar cartas de monstro, magia e armadilha.", "invalid_card")

    cost = _card_cost(preview_card)
    current_energy = int(match["player"].get("energy", match["player"].get("max_energy", 0)) or 0)
    if current_energy < cost:
        raise RebirthError(f"Mana insuficiente para jogar {preview_card['name']}.", "not_enough_energy")

    append_command(
        match,
        "PLAY_CARD",
        actor="player",
        payload={"card_instance_id": card_instance_id, "card_id": card_id, "field_slot": field_slot},
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
        raise RebirthError("Só é possível jogar cartas de monstro, magia e armadilha.", "invalid_card")

    _summon_monster_card(match, "player", player_card, field_slot=field_slot)
    # Bot evolve/summon happens at the start of bot turn (see next_turn), not
    # in reaction to the player's summon. Keeping them turn-scoped means the
    # log no longer reads "You summoned X. Bot summoned Y." on the same turn,
    # and the player gets a real action loop instead of a same-turn answer.
    if not match["is_finished"]:
        finish_if_exhausted(match)
    return match


def declare_attack(match, *, attacker_instance_id=None, target_instance_id=None):
    _require_command_dispatch(match)
    if match.get("is_finished"):
        raise RebirthError("A partida já terminou.", "match_finished")
    if match.get("phase") not in {PHASE_CHOOSE, PHASE_RESULT}:
        raise RebirthError("O ataque não está disponível nesta fase.", "invalid_phase")
    if not is_main_phase(match) and match.get("phase") != PHASE_RESULT:
        raise RebirthError(f"Ataques só podem ser declarados na fase principal. Fase atual: {current_turn_phase(match)}.", "invalid_phase")
    if not attacker_instance_id:
        raise RebirthError("Informe attacker_instance_id.", "missing_attacker")

    _attacker_index, attacker = _find_battlefield_card(match["player"], attacker_instance_id)
    if attacker is None:
        raise RebirthError("O atacante não está no seu campo.", "invalid_attacker")
    if attacker.get("exhausted") or attacker.get("has_attacked") or attacker.get("has_acted"):
        raise RebirthError("Este monstro já atacou neste turno.", "attacker_exhausted")

    target = None
    if target_instance_id:
        _target_index, target = _find_battlefield_card(match["bot"], target_instance_id)
        if target is None:
            raise RebirthError("O alvo não está no campo do bot.", "invalid_target")
    else:
        target = compact_battlefield(match["bot"])[0] if compact_battlefield(match["bot"]) else None
        target_instance_id = target.get("instance_id") if target else None

    if target is None and int(match.get("turn", 1) or 1) == 1:
        raise RebirthError(
            "Dano direto não está disponível no primeiro turno. Encerre o turno para o bot responder.",
            "first_turn_direct_attack_blocked",
        )

    effect_chain_id = new_effect_chain_id(match, "attack")
    append_command(
        match,
        "DECLARE_ATTACK",
        actor="player",
        payload={"attacker_instance_id": attacker_instance_id, "target_instance_id": target_instance_id},
    )
    attack_event = append_event(
        match,
        "ATTACK_DECLARED",
        actor="player",
        source_card_id=attacker.get("id"),
        target_id=target_instance_id,
        owner_id="player",
        effect_chain_id=effect_chain_id,
        payload={
            "attacker_card_id": attacker.get("id"),
            "attacker_instance_id": attacker_instance_id,
            "target_instance_id": target_instance_id,
        },
    )

    set_turn_phase(match, TurnPhase.COMBAT_PHASE)
    match["player"]["played_card"] = attacker
    attacker["exhausted"] = True
    attacker["has_attacked"] = True
    attacker["has_acted"] = True

    if target_instance_id:
        match["bot"]["played_card"] = target
        result = resolve_turn(
            match,
            attacker,
            target,
            persistent_field=True,
            effect_chain_id=effect_chain_id,
            parent_event_id=attack_event["event_id"],
            root_event_id=attack_event["root_event_id"],
        )
    else:
        result = _resolve_unanswered_attack(
            match,
            attacker,
            effect_chain_id=effect_chain_id,
            parent_event_id=attack_event["event_id"],
            root_event_id=attack_event["root_event_id"],
        )

    if not match["is_finished"]:
        finish_if_exhausted(match)
    return result


def evolve_duplicate(match, card_id):
    _require_command_dispatch(match)
    if match.get("is_finished"):
        raise RebirthError("A partida já terminou.", "match_finished")
    if match.get("phase") != PHASE_CHOOSE:
        raise RebirthError("A evolução só está disponível antes de jogar uma carta.", "invalid_phase")
    if not is_main_phase(match):
        raise RebirthError(f"A evolução só está disponível na fase principal. Fase atual: {current_turn_phase(match)}.", "invalid_phase")
    if not card_id:
        raise RebirthError("Informe card_id.", "missing_card")
    try:
        card = get_card(card_id)
    except ValueError as exc:
        raise RebirthError(str(exc), "invalid_card") from exc
    if not card.get("evolution_id"):
        raise RebirthError("Este monstro não possui evolução MVP.", "duplicate_not_available")
    if len([hand_card for hand_card in match["player"]["hand"] if hand_card["id"] == card_id]) < 2:
        raise RebirthError("São necessários dois monstros iguais para evoluir.", "duplicate_not_available")

    try:
        append_command(match, "EVOLVE_DUPLICATE", actor="player", payload={"card_id": card_id})
        return _evolve_side_duplicate(match, "player", card_id)
    except RebirthError:
        raise
    except ValueError as exc:
        raise RebirthError(str(exc), "invalid_card") from exc


def next_turn(match):
    _require_command_dispatch(match)
    if match.get("is_finished"):
        raise RebirthError("A partida já terminou.", "match_finished")
    if match.get("phase") not in {PHASE_RESULT, PHASE_CHOOSE}:
        raise RebirthError("O próximo turno só está disponível na fase principal ou após o combate.", "invalid_phase")

    effect_chain_id = new_effect_chain_id(match, "turn")
    append_command(match, "NEXT_TURN", actor="player", payload={"turn": match.get("turn")})
    set_turn_phase(match, TurnPhase.END_PHASE)
    turn_ended_event = append_event(
        match,
        "TURN_ENDED",
        actor="system",
        effect_chain_id=effect_chain_id,
        payload={"turn": match.get("turn")},
    )
    turn_end_events = apply_legendary_passives(
        match,
        "TURN_ENDED",
        {"effect_chain_id": effect_chain_id, "parent_event_id": turn_ended_event["event_id"], "root_event_id": turn_ended_event["root_event_id"]},
    )
    for event in turn_end_events:
        match["log"].append(f"Turno {match['turn']:02d}   {event}")
    append_snapshot(match, "TURN_ENDED")
    clear_played_cards(match)
    append_event(match, "PLAYED_CARDS_CLEARED", actor="system", effect_chain_id=effect_chain_id, payload={"turn": match.get("turn")})
    match["turn"] += 1
    set_turn_phase(match, TurnPhase.DRAW_PHASE)
    status_events = resolve_status_ticks(
        match,
        effect_chain_id=effect_chain_id,
        parent_event_id=turn_ended_event["event_id"],
        root_event_id=turn_ended_event["root_event_id"],
    )
    for status_event in status_events:
        match["log"].append(f"Turno {match['turn']:02d}   {status_event}")
        append_event(match, "ABILITY_TRIGGERED", payload={"message": status_event}, message=status_event)
    if finish_if_needed(match):
        return match
    player_drawn = draw_to_hand_size(match["player"])
    bot_drawn = draw_to_hand_size(match["bot"])
    for side_name, drawn in (("player", player_drawn), ("bot", bot_drawn)):
        if drawn:
            append_event(
                match,
                "CARDS_DRAWN",
                actor=side_name,
                target_id=side_name,
                owner_id=side_name,
                effect_chain_id=effect_chain_id,
                payload={
                    "side": side_name,
                    "amount": len(drawn),
                    "card_ids": [card.get("id") for card in drawn],
                    "instance_ids": [card.get("instance_id") for card in drawn],
                    "cards": deepcopy(drawn),
                },
            )
    _ready_battlefield(match["player"])
    _ready_battlefield(match["bot"])
    append_event(match, "UNITS_READIED", actor="system", target_id="player", owner_id="player", effect_chain_id=effect_chain_id, payload={"side": "player"})
    append_event(match, "UNITS_READIED", actor="system", target_id="bot", owner_id="bot", effect_chain_id=effect_chain_id, payload={"side": "bot"})
    expired_events = expire_statuses_for_trigger(match, "TURN_STARTED", {"effect_chain_id": effect_chain_id})
    for event in expired_events:
        match["log"].append(f"Turno {match['turn']:02d}   {event}")
    _refresh_energy_for_turn(match)
    append_event(
        match,
        "ENERGY_REFRESHED",
        actor="system",
        effect_chain_id=effect_chain_id,
        payload={"turn": match.get("turn"), "energy": int(match["player"].get("energy", 0) or 0)},
    )
    evolve_bot_if_ready(match)
    _bot_auto_attack(match, effect_chain_id=effect_chain_id)
    if match.get("is_finished"):
        return match
    _bot_auto_summon(match)
    match["result"] = None
    match["last_clash"] = None
    match["phase"] = PHASE_CHOOSE
    set_turn_phase(match, TurnPhase.MAIN_PHASE)
    match["log"].append(f"Turno {match['turn']:02d}   Escolha uma carta.")
    append_event(
        match,
        "TURN_STARTED",
        effect_chain_id=effect_chain_id,
        payload={
            "turn": match["turn"],
            "player_hand_count": len(match["player"]["hand"]),
            "bot_hand_count": len(match["bot"]["hand"]),
        },
        message=match["log"][-1],
    )
    finish_if_exhausted(match)
    return match
