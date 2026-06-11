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
    emit_monsters_fused,
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
    ensure_playable_opening_hand,
    field_slots,
    is_main_phase,
    remove_from_hand,
    set_turn_phase,
    shuffle_deck,
)

GAMEPLAY_COMMAND_TYPES = {"PLAY_CARD", "DECLARE_ATTACK", "NEXT_TURN", "EVOLVE_DUPLICATE", "FUSE_FIELD_PAIR"}


def mulligan_available(match):
    if not match or match.get("is_finished") or match.get("mulligan_used"):
        return False
    if int(match.get("turn", 1) or 1) != 1 or match.get("phase") != PHASE_CHOOSE:
        return False
    for command in match.get("commands") or []:
        if str(command.get("type") or command.get("command_type") or "") in GAMEPLAY_COMMAND_TYPES:
            return False
    return True


def mulligan(match):
    """Troca a mão inicial uma única vez, antes de qualquer ação do turno 1."""
    _require_command_dispatch(match)
    if not mulligan_available(match):
        raise RebirthError("O mulligan só está disponível uma vez, antes da primeira ação.", "mulligan_unavailable")
    player = match["player"]
    returned = [card.get("id") for card in player.get("hand") or []]
    player["deck"].extend(player.get("hand") or [])
    player["hand"] = []
    shuffle_deck(player, seed=match.get("game_seed"), owner="player", salt="mulligan")
    draw_to_hand_size(player)
    ensure_playable_opening_hand(player)
    match["mulligan_used"] = True
    append_command(match, "MULLIGAN", actor="player", payload={"returned_card_ids": returned})
    new_hand = [card.get("id") for card in player.get("hand") or []]
    message = "Mão inicial trocada no mulligan."
    match["log"].append(f"Turno {match['turn']:02d}   {message}")
    append_event(
        match,
        "HAND_MULLIGANED",
        actor="player",
        target_id="player",
        owner_id="player",
        payload={
            "returned_card_ids": returned,
            "drawn_card_ids": new_hand,
            "cards": deepcopy(player.get("hand") or []),
            "deck_instance_ids": [card.get("instance_id") for card in player.get("deck") or []],
        },
        message=message,
    )
    return match


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
    bot_card_ids=None,
    player_hp=None,
    bot_hp=None,
    campaign_version=None,
    campaign_node=None,
    campaign_attempt=None,
    campaign_modifiers=None,
    campaign_presentation=None,
    campaign_advice=None,
    shuffle=True,
):
    return create_match(
        seed=seed,
        player_card_ids=player_card_ids,
        player_name=player_name,
        bot_profile_id=bot_profile_id,
        runtime_mode=runtime_mode,
        apply_reducers_inline=apply_reducers_inline,
        first_duel=first_duel,
        bot_card_ids=bot_card_ids,
        player_hp=player_hp,
        bot_hp=bot_hp,
        campaign_version=campaign_version,
        campaign_node=campaign_node,
        campaign_attempt=campaign_attempt,
        campaign_modifiers=campaign_modifiers,
        campaign_presentation=campaign_presentation,
        campaign_advice=campaign_advice,
        shuffle=shuffle,
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


def _synergy_bonuses(match, side_name, card):
    """Bonus de sinergia K2 (condicional ao board/HP do dono). Determinístico."""
    if not match or not card or not isinstance(card.get("synergy"), dict):
        return 0, 0
    from services.rebirth_keywords import synergy_active, synergy_bonus

    side = match.get(side_name) or {}
    owner_field = [c for c in (side.get("field") or []) if c]
    if synergy_active(card, owner_field, owner_hp=int(side.get("hp", 30) or 30)):
        bonus = synergy_bonus(card)
        return int(bonus.get("attack", 0) or 0), int(bonus.get("guard", 0) or 0)
    return 0, 0


def clash_attack(card, opponent_card, *, turn=1, match=None, side_name=None):
    attack = card_attack(card)
    events = []
    key = ability_key(card)
    if match and side_name:
        synergy_attack, _synergy_guard = _synergy_bonuses(match, side_name, card)
        if synergy_attack:
            attack += synergy_attack
            events.append(f"{card['name']} ativa sinergia para +{synergy_attack} de ataque.")
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
    player_attack, player_events = clash_attack(player_card, bot_card, turn=match.get("turn", 1), match=match, side_name="player")
    bot_attack, bot_events = clash_attack(bot_card, player_card, turn=match.get("turn", 1), match=match, side_name="bot")
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


def damage_details(attacker, defender, defender_wounded=False, *, match=None, attacker_side=None, defender_side=None):
    attack_total = card_attack(attacker)
    guard_total = card_guard(defender)
    events = []
    if match and attacker_side:
        synergy_attack, _ = _synergy_bonuses(match, attacker_side, attacker)
        attack_total += synergy_attack
    if match and defender_side:
        _, synergy_guard = _synergy_bonuses(match, defender_side, defender)
        guard_total += synergy_guard
    amount = max(1, attack_total - guard_total // 2)
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


# A regra antiga de "exaustão" (fim súbito por HP quando qualquer lado ficava
# sem cartas) foi substituída por dano de fadiga incremental — ver
# _apply_fatigue em next_turn.


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
        # Campaign energy_ramp (audit #3): a SUSTAINED tempo edge — added every
        # turn, capped a bit above the normal ceiling so late bosses keep
        # out-curving without becoming infinite.
        ramp = int(side.get("energy_ramp_bonus", 0) or 0)
        side["max_energy"] = min(12, energy + ramp)
        side["energy"] = side["max_energy"]


def _restore_combat_modifiers(card):
    # Modificadores "duration: combat" (traps de congelar/enfraquecer) eram
    # aplicados e nunca revertidos — viravam debuff permanente. O ready do
    # turno restaura o ataque base + bônus permanentes legítimos.
    if "base_attack" not in card:
        return
    restored = int(card.get("base_attack", 0) or 0) + int(card.get("permanent_attack_bonus", 0) or 0)
    card["attack"] = restored
    card["power"] = restored


def _ready_battlefield(side):
    for card in compact_battlefield(side):
        _restore_combat_modifiers(card)
        # O exhaust do Shadow Reaper dura "1 turno" de verdade: a carta marcada
        # NAO e readiada aqui — o status expira depois que o bot agiu (fix do
        # legendary morto: antes, o ready apagava o exhaust antes do ataque).
        if "shadow_reaper_exhausted" in (card.get("statuses") or {}):
            card["just_summoned"] = False
            continue
        card["exhausted"] = False
        card["has_attacked"] = False
        card["has_acted"] = False
        card["just_summoned"] = False


def _prepare_summoned_monster(card):
    summoned = deepcopy(card)
    summoned["current_guard"] = int(summoned.get("guard", 0) or 0)
    summoned["max_guard"] = int(summoned.get("guard", 0) or 0)
    summoned["exhausted"] = False
    summoned["has_attacked"] = False
    summoned["has_acted"] = False
    # Summoning sickness: monstros recem-invocados so atacam neste turno se
    # tiverem RUSH (Investida) — exatamente o que o tooltip da keyword promete.
    summoned["just_summoned"] = True
    return summoned


def _find_battlefield_card(side, instance_id):
    for index, card in enumerate(field_slots(side)):
        if card and card.get("instance_id") == instance_id:
            return index, card
    return None, None


def _catalog_id(card):
    return str(card.get("catalog_id") or card.get("id") or "")


def _unit_hp(card):
    return max(0, int(card.get("current_guard", card.get("hp", card.get("guard", 0))) or 0))


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


def _spell_effects_for_target(match, side_name, card, target_instance_id=None):
    """Magias de dano podem mirar uma unidade inimiga em vez do herói."""
    effects = deepcopy(card.get("stack_effects") or [])
    if not target_instance_id:
        return effects
    opponent = _opponent_side(side_name)
    _index, target = _find_battlefield_card(match[opponent], target_instance_id)
    if target is None or _unit_hp(target) <= 0:
        raise RebirthError("O alvo da magia não está no campo inimigo.", "invalid_target")
    has_damage = False
    for effect in effects:
        if str(effect.get("type") or "").lower() == "damage" and str(effect.get("target") or "opponent").lower() in {"opponent", "enemy"}:
            effect["type"] = "unit_damage"
            effect["instance_id"] = target_instance_id
            has_damage = True
    if not has_damage:
        raise RebirthError("Esta magia não pode mirar unidades.", "spell_cannot_target_unit")
    return effects


def _resolve_spell_card(match, side_name, card, target_instance_id=None):
    spell_effects = _spell_effects_for_target(match, side_name, card, target_instance_id)
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
        spell_effects,
        effect_chain_id=effect_chain_id,
        parent_event_id=played_event["event_id"],
        root_event_id=played_event["root_event_id"],
        priority_level=PRIORITY_ACTIVE_SPELL,
        source_card=card,
    )
    if target_instance_id:
        for defeated in cleanup_defeated_units(
            match,
            effect_chain_id=effect_chain_id,
            parent_event_id=played_event["event_id"],
            root_event_id=played_event["root_event_id"],
        ):
            destroyed_message = f"{defeated['name']} foi destruído."
            effect_events.append(destroyed_message)
            match["log"].append(f"{turn_label}   {destroyed_message}")
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
    # K1: BURST keyword — dano direto ao oponente ao invocar.
    from services.rebirth_keywords import on_summon_burst
    burst_damage = on_summon_burst(summoned)
    if burst_damage > 0:
        opponent_side = "bot" if side_name == "player" else "player"
        opponent = match[opponent_side]
        actual = apply_turn_damage(match, opponent_side, burst_damage)
        if burst_damage > 0:
            burst_msg = f"{summoned['name']} detona ao entrar — {actual} de dano direto."
            match["log"].append(f"{turn_label}   {burst_msg}")
            append_event(
                match,
                "BURST_DAMAGE",
                actor=side_name,
                source_card_id=summoned["id"],
                target_id=opponent_side,
                payload={"side": opponent_side, "amount": burst_damage, "applied": actual, "keyword": "BURST"},
                message=burst_msg,
                parent_event_id=summoned_event["event_id"],
                root_event_id=summoned_event["root_event_id"],
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


FATIGUE_TURN_HARD_CAP = 120


def _apply_fatigue(match, *, effect_chain_id=None):
    """Fadiga estilo TCG moderno: deck vazio = dano crescente por turno.

    Substitui o antigo fim-súbito por exaustão (que encerrava a partida quando
    QUALQUER lado ficava sem cartas, decidindo por HP — um jogador com board e
    mão cheia podia perder porque o oponente esvaziou o próprio deck).
    Retorna True se a partida terminou nesta checagem.
    """
    for side_name in ("player", "bot"):
        side = match[side_name]
        if side.get("deck") or len(side.get("hand") or []) >= 5:
            continue
        counter = int(side.get("fatigue", 0) or 0) + 1
        side["fatigue"] = counter
        # Fadiga ignora escudos: é desgaste, não golpe (e espelha o reducer).
        hp_before = int(side.get("hp", 0) or 0)
        side["hp"] = max(0, hp_before - counter)
        applied = hp_before - side["hp"]
        if applied:
            side["wounded"] = True
        message = f"{side['name']} sofre {applied} de dano de fadiga (deck vazio)."
        match["log"].append(f"Turno {match['turn']:02d}   {message}")
        append_event(
            match,
            "FATIGUE_DAMAGE",
            actor="system",
            target_id=side_name,
            owner_id=side_name,
            effect_chain_id=effect_chain_id,
            payload={"side": side_name, "amount": applied, "fatigue": counter},
            message=message,
        )
    if finish_if_needed(match):
        return True
    if int(match.get("turn", 1) or 1) >= FATIGUE_TURN_HARD_CAP:
        # Trava de segurança contra partidas infinitas de cura mútua.
        player_hp = int(match["player"]["hp"])
        bot_hp = int(match["bot"]["hp"])
        match["winner"] = "player" if player_hp > bot_hp else "bot" if bot_hp > player_hp else "clash"
        match["is_finished"] = True
        match["phase"] = PHASE_FINISHED
        set_turn_phase(match, TurnPhase.END_PHASE)
        message = "Limite de turnos atingido. O duelo encerra pela vida restante."
        match["log"].append(message)
        append_event(
            match,
            "MATCH_FINISHED",
            payload={"winner": match["winner"], "player_hp": player_hp, "bot_hp": bot_hp, "reason": "turn_cap"},
            message=message,
        )
        append_snapshot(match, "MATCH_TURN_CAP")
        return True
    return False


def _bot_auto_summon_all(match, limit=None):
    """O bot gasta a mana do turno: invoca enquanto houver slot+mana, com cap
    por perfil (ver BOT_SUMMONS_BY_PROFILE)."""
    if limit is None:
        profile_id = (match.get("bot_profile") or {}).get("id") or "defensive"
        limit = BOT_SUMMONS_BY_PROFILE.get(profile_id, 2)
    summoned = []
    for _ in range(max(1, int(limit))):
        card = _bot_auto_summon(match)
        if not card:
            break
        summoned.append(card)
        if match.get("is_finished"):
            break
    return summoned


def _bot_rush_attacks(match, summoned_cards, *, effect_chain_id=None):
    """Invocações com RUSH (Investida) atacam no mesmo turno do bot."""
    from services.rebirth_keywords import has_keyword

    for card in summoned_cards or []:
        if match.get("is_finished"):
            return
        if not has_keyword(card, "RUSH"):
            continue
        _index, live_card = _find_battlefield_card(match["bot"], card.get("instance_id"))
        if not live_card or live_card.get("has_acted") or live_card.get("exhausted"):
            continue
        live_card["just_summoned"] = False
        _bot_auto_attack(match, effect_chain_id=effect_chain_id)


def _side_has_ready_attackers(side):
    return any(
        card
        and not card.get("exhausted")
        and not card.get("has_attacked")
        and not card.get("has_acted")
        for card in compact_battlefield(side)
    )


def _side_has_breakable_shield(match, side_name):
    side = match[side_name]
    if "shield" in (side.get("statuses") or {}):
        return True
    return any(
        "aegis_sentinel_shield" in (card.get("statuses") or {})
        or int(card.get("current_guard", card.get("guard", 0)) or 0) > 0
        for card in compact_battlefield(side)
    )


def _bot_support_score(match, card, profile_id):
    if not (is_spell(card) or is_trap(card)):
        return -1
    bot = match["bot"]
    cost = _card_cost(card)
    if cost > int(bot.get("energy", 0) or 0):
        return -1
    player = match["player"]
    action = str(card.get("action") or "").lower()
    player_pressure = len(compact_battlefield(player))
    player_ready = _side_has_ready_attackers(player)
    player_wounded = int(player.get("hp", 30) or 0) <= int(player.get("max_hp", 30) or 30) - 3
    bot_shielded = "shield" in (bot.get("statuses") or {})

    if is_trap(card):
        if len(bot.get("traps") or []) >= 2:
            return -1
        if player_ready:
            return 14 - cost
        if player_pressure and int(match.get("turn", 1) or 1) >= 2:
            return 11 - cost
        if int(match.get("turn", 1) or 1) >= 4 and profile_id == "defensive":
            return 7 - cost
        return -1

    if action == "drawtwocards" and bot.get("deck"):
        hand_size = len(bot.get("hand") or [])
        turn = int(match.get("turn", 1) or 1)
        if hand_size <= 3:
            return 14 - cost
        if hand_size <= 5 and turn >= 3:
            return 10 - cost
        if hand_size <= 6 and turn >= 6 and profile_id == "defensive":
            return 7 - cost
    if action in {"cleanseall", "tidalrenewal"} and bot.get("statuses"):
        return 12 - cost
    if action == "destroyshield":
        return 13 - cost if _side_has_breakable_shield(match, "player") else -1
    if action in {"healingrain", "tidalrenewal"} and int(bot.get("hp", 30) or 0) <= (22 if profile_id == "defensive" else 20):
        return 12 - cost
    if action in {"fortify", "stoneskin"} and not bot_shielded and player_ready and int(bot.get("hp", 30) or 0) <= (23 if profile_id == "defensive" else 20):
        return 11 - cost
    if action == "shadowdrain" and (int(bot.get("hp", 30) or 0) <= 18 or int(player.get("hp", 30) or 0) <= 6):
        return 10 - cost
    if action == "fireball" and int(player.get("hp", 30) or 0) <= (11 if profile_id != "aggressive" else 14):
        return 10 - cost
    if action == "burningedict" and player_wounded and "burn" not in (player.get("statuses") or {}):
        return 7 - cost
    return -1


def _bot_auto_play_support(match):
    if match.get("is_finished"):
        return None
    profile_id = (match.get("bot_profile") or {}).get("id") or "defensive"
    energy = int(match["bot"].get("energy", 0) or 0)
    # Board primeiro: o suporte não pode consumir a mana da invocação do turno.
    affordable_monsters = [
        _card_cost(card)
        for card in match["bot"].get("hand", [])
        if is_monster(card) and _card_cost(card) <= energy
    ]
    support_budget = energy
    if affordable_monsters and _battlefield_slots_available(match["bot"]) > 0:
        support_budget = energy - min(affordable_monsters)
    affordable = [
        card
        for card in match["bot"].get("hand", [])
        if (is_spell(card) or is_trap(card)) and _card_cost(card) <= support_budget
    ]
    scored = [(score, card) for card in affordable if (score := _bot_support_score(match, card, profile_id)) > 0]
    if not scored:
        return None
    _score, chosen = sorted(scored, key=lambda item: (item[0], -_card_cost(item[1]), item[1]["name"]))[-1]
    append_event(
        match,
        "BOT_DECISION",
        actor="bot",
        payload={"profile_id": profile_id, "card_id": chosen["id"], "instance_id": chosen["instance_id"], "support": True},
        message=f"O bot preparou {chosen['name']}.",
    )
    bot_card = remove_from_hand(match["bot"], card_instance_id=chosen["instance_id"])
    if is_spell(bot_card):
        return _resolve_spell_card(match, "bot", bot_card)
    if is_trap(bot_card):
        return _arm_trap_card(match, "bot", bot_card)
    return None


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


def _trigger_side_traps(match, owner_side, owner_card, opponent_card):
    """Dispara as traps armadas de owner_side contra o atacante adversario."""
    events = []
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
            payload={"card_id": trap["id"], "instance_id": trap.get("instance_id"), "effect": trap.get("trap_effect"), "card": deepcopy(triggered)},
            message=events[-1] if events else f"{trap['name']} foi acionada.",
        )
    side["traps"] = remaining_traps
    return events


def _resolve_direct_attack_traps(match, defender_side, attacker_card):
    """Ataque direto no heroi tambem revela as traps do defensor."""
    if attacker_card:
        _index, refreshed = _find_battlefield_card(match[_opponent_side(defender_side)], attacker_card.get("instance_id"))
        attacker_card = refreshed or attacker_card
    return _trigger_side_traps(match, defender_side, None, attacker_card)


def _resolve_combat_traps(match, player_card, bot_card, attacking_side="player"):
    """Traps disparam com contexto: apenas o lado ATACADO revela as suas.

    Antes, qualquer combate revelava as traps dos dois lados ao mesmo tempo —
    a sua propria trap punia o seu proprio ataque.
    """
    events = []
    defender_side = _opponent_side(attacking_side)
    pairs = (
        (defender_side, player_card if defender_side == "player" else bot_card,
         bot_card if defender_side == "player" else player_card),
    )
    for owner_side, owner_card, opponent_card in pairs:
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
    direct_events = _resolve_direct_attack_traps(match, "bot", player_card)
    damage = max(1, card_attack(player_card))
    damage = apply_turn_damage(match, "bot", damage)
    _emit_lifesteal(match, "player", player_card, damage, direct_events)
    result = {
        "outcome": "Victory",
        "winner": "player",
        "damage": {"player": 0, "bot": damage},
        "message": f"{player_card['name']} ataca diretamente. Bot sofre {damage} de dano.",
        "ability_events": direct_events,
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
    direct_events = _resolve_direct_attack_traps(match, "player", bot_card)
    damage = apply_turn_damage(match, "player", max(1, card_attack(bot_card)))
    _emit_lifesteal(match, "bot", bot_card, damage, direct_events)
    result = {
        "outcome": "Defeat",
        "winner": "bot",
        "damage": {"player": damage, "bot": 0},
        "message": f"{bot_card['name']} ataca diretamente. Você sofre {damage} de dano.",
        "ability_events": direct_events,
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


# Identidade de perfil + alavanca de dificuldade (calibrado no lab para a
# faixa 40-60% de winrate do jogador por perfil): o agressivo bate duas vezes
# mas desenvolve pouco; o oportunista monta board e escolhe um golpe certeiro;
# o defensivo segura a linha.
BOT_ATTACKS_PER_TURN = {
    "novice": 1,
    "defensive": 1,
    "opportunist": 2,
    "aggressive": 2,
}

# Ritmo de reposição (auditoria 2026-06-11): com 2 invocações/turno o bot
# re-enchia o campo mais rápido do que um casual remove e o jogo virava muro
# eterno. 1/turno abre o campo no mid game (defensive mantém 2: é a
# identidade da muralha — e a policy dele quase não remove o board alheio).
BOT_SUMMONS_BY_PROFILE = {
    "novice": 1,
    "defensive": 1,
    "opportunist": 1,
    "aggressive": 1,
}


def _bot_auto_attack_all(match, *, effect_chain_id=None):
    """O bot ataca com os monstros prontos até o orçamento do perfil."""
    profile_id = (match.get("bot_profile") or {}).get("id") or "defensive"
    budget = BOT_ATTACKS_PER_TURN.get(profile_id, 2)
    for _ in range(max(1, budget)):
        if match.get("is_finished"):
            return
        if _bot_auto_attack(match, effect_chain_id=effect_chain_id) is None:
            return


def _bot_auto_attack(match, *, effect_chain_id=None):
    if match.get("is_finished"):
        return None
    from services.rebirth_keywords import forces_target, has_taunt_on_side

    profile_id = (match.get("bot_profile") or {}).get("id") or "defensive"
    player_field = compact_battlefield(match["player"])
    # TAUNT vale para o bot também: com Provocar em campo, ele é obrigado a
    # resolver as provocadoras antes de ataque direto ou alvos livres.
    if has_taunt_on_side(player_field):
        player_field = [card for card in player_field if forces_target(card)]
    decision = choose_bot_attack(
        compact_battlefield(match["bot"]),
        player_field,
        player_hp=match["player"].get("hp", 30),
        turn=match.get("turn", 1),
        player_wounded=match["player"].get("wounded", False),
        bot_wounded=match["bot"].get("wounded", False),
        profile_id=profile_id,
    )
    if not decision:
        return None
    if decision.get("outcome") == "direct" and has_taunt_on_side(compact_battlefield(match["player"])):
        return None
    if (
        profile_id == "aggressive"
        and decision.get("outcome") == "direct"
        and not decision.get("lethal_window")
        and int(match.get("turn", 1) or 1) <= 2
        and int(match["player"].get("hp", 30) or 0) > 10
    ):
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


# audit #18: bloco de status pós-clash extraído de resolve_turn (270 LOC).
# Função pura de (winner, cartas) — não muta match. As regras de
# burn/decay/lifesteal/heal/cleanse/shield por ability_key vivem aqui, fora
# do núcleo de dano. Equivalência garantida pela suíte de canonical
# hash + parity + replay.
_CLASH_STATUS_BY_KEY = {
    "molten_bite": ("status", "burn"),
    "inferno_bite": ("status", "burn"),
    "fire_burn": ("status", "burn"),
    "shadow_decay": ("status", "decay"),
}


def _derive_clash_status_effects(winner, player_card, bot_card):
    if winner == "player":
        source_card, target_side, heal_side = player_card, "bot", "player"
    elif winner == "bot":
        source_card, target_side, heal_side = bot_card, "player", "bot"
    else:
        return []
    key = ability_key(source_card)
    effects = []
    if key in _CLASH_STATUS_BY_KEY:
        _, status_name = _CLASH_STATUS_BY_KEY[key]
        effects.append({"type": "status", "side": target_side, "status": status_name, "potency": 1, "turns": 2})
    if key in {"shadow_lifesteal", "shadow_drain"}:
        effects.append({"type": "heal", "side": heal_side, "amount": 2})
    if key == "water_heal":
        effects.append({"type": "heal", "side": heal_side, "amount": 2})
    if key == "water_cleanse":
        effects.append({"type": "cleanse", "side": heal_side})
    if key == "earth_shield":
        effects.append({"type": "shield", "side": heal_side, "amount": 2, "turns": 2})
    return effects


def _heal_side(match, side_name, amount):
    side = match[side_name]
    amount = max(0, int(amount or 0))
    if not amount:
        return 0
    before = int(side.get("hp", 0) or 0)
    side["hp"] = min(int(side.get("max_hp", before) or before), before + amount)
    return side["hp"] - before


def _emit_lifesteal(match, side_name, card, damage, ability_events):
    """LIFESTEAL com evento espelhado para o replay reconstruir o HP."""
    from services.rebirth_keywords import lifesteal_heal_amount

    heal = lifesteal_heal_amount(card, damage)
    if not heal:
        return 0
    healed = _heal_side(match, side_name, heal)
    if not healed:
        return 0
    message = f"{card['name']} drena {healed} PV com Drenar."
    ability_events.append(message)
    append_event(
        match,
        "HEALTH_RECOVERED",
        actor=side_name,
        source_card_id=card.get("id"),
        target_id=side_name,
        owner_id=side_name,
        payload={"side": side_name, "amount": healed, "keyword": "LIFESTEAL"},
        message=message,
    )
    return healed


def _apply_persistent_strike(match, *, winner_side, winner_card, loser_side, loser_card, damage, ability_events, hero_damage):
    """Resolve o golpe vencedor em campo persistente com as keywords reais.

    SHIELD (perdedor): ignora a primeira instância de dano recebida.
    PIERCE (vencedor): TODO o excedente sobre a Guarda vaza para o HP do herói
    (sem PIERCE, vale o Breakthrough universal capado em 2).
    LIFESTEAL (vencedor): recupera HP igual ao dano causado.
    EXECUTE (vencedor): destrói o alvo que sobreviver com Guarda <= 1.
    Retorna o dano efetivamente aplicado à Guarda.
    """
    from services.rebirth_keywords import (
        execute_kills,
        has_keyword,
        lifesteal_heal_amount,
        shield_absorbs,
    )

    if shield_absorbs(loser_card):
        loser_card["shield_consumed"] = True
        message = f"{loser_card['name']} ignora o golpe com Escudo."
        ability_events.append(message)
        append_event(
            match,
            "SHIELD_KEYWORD_ABSORBED",
            actor=loser_side,
            source_card_id=loser_card.get("id"),
            target_id=loser_card.get("instance_id"),
            owner_id=loser_side,
            payload={"side": loser_side, "instance_id": loser_card.get("instance_id"), "keyword": "SHIELD"},
            message=message,
        )
        return 0

    guard_before = max(0, int(loser_card.get("current_guard", loser_card.get("guard", 0)) or 0))
    loser_card["current_guard"] = int(loser_card.get("current_guard", loser_card.get("guard", 0)) or 0) - damage
    overflow = max(0, damage - guard_before)
    if overflow:
        if has_keyword(winner_card, "PIERCE"):
            applied = apply_turn_damage(match, loser_side, overflow)
            if applied:
                hero_damage[loser_side] = applied
                ability_events.append(f"Perfurar: {match[loser_side]['name']} sofre {applied} de dano excedente.")
        else:
            breakthrough = min(2, overflow)
            applied = apply_turn_damage(match, loser_side, breakthrough)
            if applied:
                hero_damage[loser_side] = applied
                ability_events.append(f"Breakthrough: {match[loser_side]['name']} sofre {applied} de dano excedente.")

    heal = lifesteal_heal_amount(winner_card, damage)
    if heal:
        healed = _heal_side(match, winner_side, heal)
        if healed:
            message = f"{winner_card['name']} drena {healed} PV com Drenar."
            ability_events.append(message)
            append_event(
                match,
                "HEALTH_RECOVERED",
                actor=winner_side,
                source_card_id=winner_card.get("id"),
                target_id=winner_side,
                owner_id=winner_side,
                payload={"side": winner_side, "amount": healed, "keyword": "LIFESTEAL"},
                message=message,
            )

    survivor_guard = max(0, int(loser_card.get("current_guard", 0) or 0))
    if survivor_guard and execute_kills(winner_card, {"guard": survivor_guard}):
        loser_card["current_guard"] = 0
        message = f"{winner_card['name']} executa {loser_card['name']} com Guarda baixa."
        ability_events.append(message)
        append_event(
            match,
            "UNIT_DAMAGE_RESOLVED",
            actor=winner_side,
            source_card_id=winner_card.get("id"),
            target_id=loser_card.get("instance_id"),
            owner_id=loser_side,
            payload={
                "side": loser_side,
                "amount": survivor_guard,
                "instance_id": loser_card.get("instance_id"),
                "keyword": "EXECUTE",
            },
            message=message,
        )
    return damage


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
    trap_events = _resolve_combat_traps(match, player_card, bot_card, attacking_side=attacking_side)
    _player_index, refreshed_player_card = _find_battlefield_card(match["player"], player_card.get("instance_id"))
    _bot_index, refreshed_bot_card = _find_battlefield_card(match["bot"], bot_card.get("instance_id"))
    player_card = refreshed_player_card or player_card
    bot_card = refreshed_bot_card or bot_card
    winner, clash = compare_clash(match, player_card, bot_card)
    ability_events = list(trap_events) + list(clash["events"])
    hero_damage = {"player": 0, "bot": 0}
    if winner == "player":
        damage_payload = damage_details(
            player_card, bot_card, match["bot"].get("wounded", False),
            match=match, attacker_side="player", defender_side="bot",
        )
        damage = damage_payload["amount"]
        ability_events.extend(damage_payload["events"])
        if persistent_field:
            damage = _apply_persistent_strike(
                match,
                winner_side="player",
                winner_card=player_card,
                loser_side="bot",
                loser_card=bot_card,
                damage=damage,
                ability_events=ability_events,
                hero_damage=hero_damage,
            )
        else:
            damage = apply_turn_damage(match, "bot", damage)
            _emit_lifesteal(match, "player", player_card, damage, ability_events)
        result = {
            "outcome": "Victory",
            "winner": "player",
            "damage": {"player": 0, "bot": damage},
            "message": f"{player_card['name']} venceu {bot_card['name']}. {'Alvo perde' if persistent_field else 'Bot sofre'} {damage} de dano.",
        }
    elif winner == "bot":
        damage_payload = damage_details(
            bot_card, player_card, match["player"].get("wounded", False),
            match=match, attacker_side="bot", defender_side="player",
        )
        damage = damage_payload["amount"]
        ability_events.extend(damage_payload["events"])
        if persistent_field:
            damage = _apply_persistent_strike(
                match,
                winner_side="bot",
                winner_card=bot_card,
                loser_side="player",
                loser_card=player_card,
                damage=damage,
                ability_events=ability_events,
                hero_damage=hero_damage,
            )
        else:
            damage = apply_turn_damage(match, "player", damage)
            _emit_lifesteal(match, "bot", bot_card, damage, ability_events)
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

    status_owner = result["winner"] if result.get("winner") in {"player", "bot"} else "system"
    status_effects = _derive_clash_status_effects(winner, player_card, bot_card)
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


def _labs_side_name(match, player_id):
    raw = str(player_id or "").strip()
    if raw in {"player", "bot"}:
        return raw
    owner_id = match.get("owner_user_id")
    if owner_id is not None and raw == str(owner_id):
        return "player"
    raise RebirthError("player_id nao corresponde a um participante valido do laboratorio.", "invalid_labs_player")


def _fusion_resulting_slot(slot_a, slot_b):
    left = min(int(slot_a), int(slot_b))
    right = max(int(slot_a), int(slot_b))
    if right - left != 1:
        raise RebirthError("As unidades precisam estar adjacentes para fundir.", "fusion_not_adjacent")
    return 1 if left <= 1 <= right else left


def _fusion_stats(material_a, material_b, resulting_card):
    combined_attack = card_attack(material_a) + card_attack(material_b)
    inherited_hp = max(_unit_hp(material_a), _unit_hp(material_b))
    resulting_card["attack"] = combined_attack
    resulting_card["power"] = combined_attack
    resulting_card["base_attack"] = combined_attack
    resulting_card["guard"] = inherited_hp
    resulting_card["current_guard"] = inherited_hp
    resulting_card["max_guard"] = inherited_hp
    resulting_card["breakthrough"] = True
    resulting_card["labs_fusion"] = True
    resulting_card["passives"] = sorted(set(list(resulting_card.get("passives") or []) + ["BREAKTHROUGH"]))
    # A fusão agora concede PIERCE de verdade: TODO o excedente sobre a Guarda
    # vaza para o HP (antes a flag "breakthrough" era cosmética — o teto de 2
    # valia para qualquer atacante).
    keywords = list(resulting_card.get("keywords") or [])
    if "PIERCE" not in keywords:
        keywords.append("PIERCE")
    resulting_card["keywords"] = keywords
    resulting_card["ability_key"] = "breakthrough"
    resulting_card["ability_name"] = "BREAKTHROUGH"
    resulting_card["ability_text"] = "Dano excedente sobre a Guarda atravessa direto para o HP inimigo."
    resulting_card["exhausted"] = False
    resulting_card["has_attacked"] = False
    resulting_card["has_acted"] = False
    return {
        "attack": combined_attack,
        "power": combined_attack,
        "hp": inherited_hp,
        "guard": inherited_hp,
        "current_guard": inherited_hp,
        "max_guard": inherited_hp,
        "passives": list(resulting_card["passives"]),
    }


def resolve_labs_fusion(match, *, player_id=None, source_instance_a=None, source_instance_b=None):
    _require_command_dispatch(match)
    if match.get("is_finished"):
        raise RebirthError("A partida ja terminou.", "match_finished")
    if not source_instance_a or not source_instance_b:
        raise RebirthError("Informe source_instance_a e source_instance_b.", "missing_fusion_material")
    if str(source_instance_a) == str(source_instance_b):
        raise RebirthError("A fusao precisa de duas unidades diferentes.", "invalid_fusion_material")

    side_name = _labs_side_name(match, player_id)
    side = match[side_name]
    slot_a, material_a = _find_battlefield_card(side, source_instance_a)
    slot_b, material_b = _find_battlefield_card(side, source_instance_b)
    if material_a is None or material_b is None:
        raise RebirthError("As duas unidades precisam pertencer ao mesmo jogador e estar no campo.", "invalid_fusion_material")
    if _unit_hp(material_a) <= 0 or _unit_hp(material_b) <= 0:
        raise RebirthError("As duas unidades precisam estar vivas para fundir.", "fusion_material_defeated")
    if _catalog_id(material_a) != _catalog_id(material_b):
        raise RebirthError("A fusao exige duas criaturas identicas.", "fusion_catalog_mismatch")

    resulting_slot = _fusion_resulting_slot(slot_a, slot_b)
    source_catalog_id = _catalog_id(material_a)
    try:
        source_card = get_card(source_catalog_id)
    except ValueError as exc:
        raise RebirthError(str(exc), "invalid_card") from exc
    resulting_catalog_id = source_card.get("evolution_id")
    if not resulting_catalog_id:
        raise RebirthError("Nao existe forma evoluida para esta fusao.", "fusion_target_missing")
    try:
        get_card(resulting_catalog_id)
    except ValueError as exc:
        raise RebirthError(str(exc), "fusion_target_missing") from exc

    append_command(
        match,
        "FUSE_FIELD_PAIR",
        actor=side_name,
        payload={
            "player_id": side_name,
            "source_instance_a": source_instance_a,
            "source_instance_b": source_instance_b,
        },
    )
    resulting_card = create_card_instance(resulting_catalog_id, side_name, _side_sequence(side))
    resulting_card["field_slot"] = resulting_slot
    resulting_card["slot"] = resulting_slot + 1
    resulting_card["fused_from"] = [material_a["instance_id"], material_b["instance_id"]]
    resulting_card["fusion_material_catalog_ids"] = [source_catalog_id, _catalog_id(material_b)]
    resulting_stats = _fusion_stats(material_a, material_b, resulting_card)
    match["log"].append(
        f"Turno {match['turn']:02d}   {material_a['name']} x2 explode em {resulting_card['name']}."
    )
    event = emit_monsters_fused(
        match,
        side_name=side_name,
        material_cards=[material_a, material_b],
        resulting_card=resulting_card,
        resulting_slot=resulting_slot,
        resulting_stats=resulting_stats,
    )
    return {
        "event": deepcopy(event),
        "resulting_card": deepcopy(resulting_card),
        "resulting_stats": deepcopy(resulting_stats),
    }


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


def play_card(match, *, card_instance_id=None, card_id=None, field_slot=None, target_instance_id=None):
    _require_command_dispatch(match)
    if match.get("is_finished"):
        raise RebirthError("A partida já terminou.", "match_finished")
    # Fase principal fluida: depois de um ataque (phase=result/END_PHASE) o
    # jogador ainda pode desenvolver o board até encerrar o turno — com
    # summoning sickness, "atacar e depois invocar" é a ordem natural.
    if match.get("phase") not in {PHASE_CHOOSE, PHASE_RESULT}:
        raise RebirthError("Avance para o próximo turno antes de jogar outra carta.", "invalid_phase")
    if not is_main_phase(match) and current_turn_phase(match) != TurnPhase.END_PHASE.value:
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
    if target_instance_id and is_spell(preview_card):
        # Valida o alvo antes de gastar mana/remover da mão.
        _spell_effects_for_target(match, "player", preview_card, target_instance_id)

    cost = _card_cost(preview_card)
    current_energy = int(match["player"].get("energy", match["player"].get("max_energy", 0)) or 0)
    if current_energy < cost:
        raise RebirthError(f"Mana insuficiente para jogar {preview_card['name']}.", "not_enough_energy")

    append_command(
        match,
        "PLAY_CARD",
        actor="player",
        payload={"card_instance_id": card_instance_id, "card_id": card_id, "field_slot": field_slot, "target_instance_id": target_instance_id},
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
        return _resolve_spell_card(match, "player", player_card, target_instance_id=target_instance_id)
    if is_trap(player_card):
        return _arm_trap_card(match, "player", player_card)
    if not is_monster(player_card):
        raise RebirthError("Só é possível jogar cartas de monstro, magia e armadilha.", "invalid_card")

    _summon_monster_card(match, "player", player_card, field_slot=field_slot)
    # Bot evolve/summon happens at the start of bot turn (see next_turn), not
    # in reaction to the player's summon. Keeping them turn-scoped means the
    # log no longer reads "You summoned X. Bot summoned Y." on the same turn,
    # and the player gets a real action loop instead of a same-turn answer.
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
    from services.rebirth_keywords import can_attack_this_turn
    if not can_attack_this_turn(attacker, just_summoned=bool(attacker.get("just_summoned"))):
        raise RebirthError(
            "Monstros recém-invocados precisam de Investida para atacar neste turno.",
            "summoning_sickness",
        )

    target = None
    if target_instance_id:
        _target_index, target = _find_battlefield_card(match["bot"], target_instance_id)
        if target is None:
            raise RebirthError("O alvo não está no campo do bot.", "invalid_target")
    else:
        target = compact_battlefield(match["bot"])[0] if compact_battlefield(match["bot"]) else None
        target_instance_id = target.get("instance_id") if target else None

    # K2: TAUNT — se o lado defensor tem alguma carta com TAUNT, o player
    # NÃO pode atacar diretamente o HP nem outros monstros não-TAUNT.
    # Força tactical decision: limpar taunt primeiro.
    from services.rebirth_keywords import has_taunt_on_side, forces_target
    bot_field = compact_battlefield(match["bot"])
    if has_taunt_on_side(bot_field):
        # Se atacando HP direto (sem target): bloqueia
        if target is None:
            raise RebirthError(
                "Há uma carta com Provocar no campo inimigo. Ataque-a primeiro.",
                "taunt_blocks_direct_attack",
            )
        # Se alvo escolhido não é taunt: bloqueia
        if not forces_target(target):
            raise RebirthError(
                "Há uma carta com Provocar no campo inimigo. Ataque-a primeiro.",
                "taunt_blocks_alternate_target",
            )

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

    return result


def evolve_duplicate(match, card_id):
    _require_command_dispatch(match)
    if match.get("is_finished"):
        raise RebirthError("A partida já terminou.", "match_finished")
    if match.get("phase") not in {PHASE_CHOOSE, PHASE_RESULT}:
        raise RebirthError("A evolução só está disponível antes de encerrar o turno.", "invalid_phase")
    if not is_main_phase(match) and current_turn_phase(match) != TurnPhase.END_PHASE.value:
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

    # K2: REGEN — restaura 1 de Guarda no início do turno pra cartas que portam.
    # Aplicado em ambos os lados; não pode exceder max_guard original da carta.
    from services.rebirth_keywords import regen_amount as _regen_amt
    for _side_name in ("player", "bot"):
        for _card in compact_battlefield(match[_side_name]):
            _heal = _regen_amt(_card)
            if not _heal:
                continue
            _max = int(_card.get("max_guard", _card.get("guard", 0)) or 0)
            _cur = int(_card.get("current_guard", _card.get("guard", 0)) or 0)
            if _cur >= _max:
                continue
            _restored = min(_heal, _max - _cur)
            _card["current_guard"] = _cur + _restored
            if _restored > 0:
                _msg = f"{_card['name']} regenera +{_restored} de Guarda."
                match["log"].append(f"Turno {match['turn']:02d}   {_msg}")
                append_event(
                    match,
                    "REGEN_TICK",
                    actor=_side_name,
                    source_card_id=_card.get("id"),
                    target_id=_card.get("instance_id"),
                    owner_id=_side_name,
                    payload={"amount": _restored, "keyword": "REGEN", "new_guard": _card["current_guard"]},
                    message=_msg,
                )
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
    if _apply_fatigue(match, effect_chain_id=effect_chain_id):
        return match
    _ready_battlefield(match["player"])
    _ready_battlefield(match["bot"])
    append_event(match, "UNITS_READIED", actor="system", target_id="player", owner_id="player", effect_chain_id=effect_chain_id, payload={"side": "player"})
    append_event(match, "UNITS_READIED", actor="system", target_id="bot", owner_id="bot", effect_chain_id=effect_chain_id, payload={"side": "bot"})
    _refresh_energy_for_turn(match)
    append_event(
        match,
        "ENERGY_REFRESHED",
        actor="system",
        effect_chain_id=effect_chain_id,
        payload={
            "turn": match.get("turn"),
            "energy": int(match["player"].get("energy", 0) or 0),
            # Por lado: o energy_ramp da campanha dá tetos diferentes — o
            # reducer antigo aplicava a energia do player nos dois lados e o
            # replay de boss divergia.
            "player_energy": int(match["player"].get("energy", 0) or 0),
            "player_max_energy": int(match["player"].get("max_energy", 0) or 0),
            "bot_energy": int(match["bot"].get("energy", 0) or 0),
            "bot_max_energy": int(match["bot"].get("max_energy", 0) or 0),
        },
    )
    evolve_bot_if_ready(match)
    _bot_auto_play_support(match)
    if match.get("is_finished"):
        return match
    _bot_auto_attack_all(match, effect_chain_id=effect_chain_id)
    if match.get("is_finished"):
        return match
    summoned_cards = _bot_auto_summon_all(match)
    if match.get("is_finished"):
        return match
    _bot_rush_attacks(match, summoned_cards, effect_chain_id=effect_chain_id)
    if match.get("is_finished"):
        return match
    # O exhaust do Shadow Reaper expira DEPOIS de o bot agir — antes deste fix
    # ele era limpo antes do ataque do bot e a lendária não fazia nada.
    expired_events = expire_statuses_for_trigger(match, "TURN_STARTED", {"effect_chain_id": effect_chain_id})
    for event in expired_events:
        match["log"].append(f"Turno {match['turn']:02d}   {event}")
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
    return match
