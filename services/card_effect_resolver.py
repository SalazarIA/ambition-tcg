"""Canonical BE2 card effect resolver.

The resolver is intentionally callback-driven so it can stay small and avoid a
hard dependency cycle with the battle engine. BE2 owns validation and turn flow;
this module owns the repeatable side effects produced by cards.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Optional


EffectContext = Dict[str, Any]


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _enemy_side(actor_key: str) -> str:
    return "opponent" if actor_key == "player" else "player"


def _card_id(card: Dict[str, Any]) -> str:
    return str(card.get("card_id") or card.get("id") or card.get("name") or "card")


def infer_card_type(card: Optional[Dict[str, Any]]) -> str:
    """Return the gameplay type used by the BE2 card-play contract.

    The engine historically used ``kind=guard`` for trap-like defensive cards.
    RC V6 keeps that old value valid while exposing official Trap cards as
    ``trap`` so they can be prepared instead of summoned or cast immediately.
    """
    card = card or {}
    raw = str(card.get("card_type") or card.get("kind") or card.get("type") or card.get("official_type") or "card").strip().lower()
    official = str(card.get("official_type") or card.get("type") or "").strip().lower()

    if raw in {"creature", "monster", "unit"} or official == "monster":
        return "creature"
    if raw in {"trap"} or official == "trap":
        return "trap"
    if raw in {"guard"}:
        return "guard"
    if raw in {"support"}:
        return "support"
    if raw in {"spell", "magic"} or official == "spell":
        return "spell"
    return "card"


def infer_spell_effect(card: Optional[Dict[str, Any]]) -> str:
    card = card or {}
    haystack = " ".join([
        str(card.get("effect_type") or ""),
        str(card.get("effect_key") or ""),
        str(card.get("effect") or ""),
        str(card.get("role") or ""),
        str(card.get("name") or ""),
        str(card.get("text") or card.get("description") or ""),
    ]).lower()

    if "drain" in haystack or "drenar" in haystack:
        return "drain"
    if any(token in haystack for token in ("heal", "restore", "cura", "curar", "vital")):
        return "heal"
    if any(token in haystack for token in ("shield", "guard", "barrier", "armor", "escudo", "barreira")):
        return "shield"
    if any(token in haystack for token in ("ambition", "focus", "insight", "draw", "compra", "mana", "recurso", "boost")):
        return "ambition"
    if any(token in haystack for token in ("damage", "burn", "fire", "bolt", "strike", "dano", "labareda", "explos")):
        return "damage"

    if _int(card.get("heal")):
        return "heal"
    if _int(card.get("shield")):
        return "shield"
    if _int(card.get("damage")):
        return "damage"
    if _int(card.get("ambition")) or _int(card.get("draw")):
        return "ambition"
    return "noop"


def infer_trap_effect(card: Optional[Dict[str, Any]]) -> str:
    card = card or {}
    haystack = " ".join([
        str(card.get("trigger_type") or ""),
        str(card.get("effect_type") or ""),
        str(card.get("effect_key") or ""),
        str(card.get("effect") or ""),
        str(card.get("role") or ""),
        str(card.get("name") or ""),
        str(card.get("text") or card.get("description") or ""),
    ]).lower()

    if any(token in haystack for token in ("counter", "thorn", "spike", "ambush", "contra", "cinzas", "oculta")):
        return "counter"
    if any(token in haystack for token in ("snare", "root", "bind", "weaken", "raiz", "aprision", "marca")):
        return "snare"
    if any(token in haystack for token in ("heal", "restore", "cura", "reativo")):
        return "heal"
    if any(token in haystack for token in ("shield", "guard", "barrier", "shell", "muralha", "barreira", "escudo")):
        return "shield"
    if any(token in haystack for token in ("burn", "fire", "damage", "dano", "selo", "vinculo")):
        return "counter"
    return "prepared"


def _message(context: EffectContext, match: Dict[str, Any], event_type: str, **data: Any) -> None:
    add_event: Callable[..., Dict[str, Any]] = context["add_event"]
    add_combat_event: Callable[..., Dict[str, Any]] = context["add_combat_event"]
    add_event(match, event_type, **data)
    add_combat_event(match, event_type, **_combat_data(data))


def _combat_data(data: Dict[str, Any]) -> Dict[str, Any]:
    combat = dict(data)
    if "actor" in combat and "side" not in combat:
        combat["side"] = combat.pop("actor")
    if "text" in combat and "message" not in combat:
        combat["message"] = combat.pop("text")
    return combat


def _creature_ref(side: str, creature: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "side": side,
        "instance_id": creature.get("instance_id"),
        "card_id": creature.get("card_id") or creature.get("id"),
        "name": creature.get("name"),
    }


def resolve_card_effect(
    match: Dict[str, Any],
    actor_key: str,
    card: Dict[str, Any],
    context: EffectContext,
) -> Dict[str, Any]:
    """Resolve the effect of an already-validated BE2 card play."""
    kind = infer_card_type(card)

    if kind == "creature":
        return _resolve_creature(match, actor_key, card, context)
    if kind == "support":
        return _resolve_support(match, actor_key, card, context)
    if kind == "trap":
        return _resolve_trap_prepare(match, actor_key, card, context)

    return resolve_spell_effect(match, actor_key, card, context)


def _resolve_creature(
    match: Dict[str, Any],
    actor_key: str,
    card: Dict[str, Any],
    context: EffectContext,
) -> Dict[str, Any]:
    actor = match[actor_key]
    lane = str(context.get("lane") or "")
    ensure_board: Callable[[Dict[str, Any]], Dict[str, Any]] = context["ensure_board"]
    create_instance: Callable[..., Dict[str, Any]] = context["create_creature_instance"]
    board = ensure_board(actor)
    instance = create_instance(match, actor_key, lane, card)

    board[lane] = instance
    ambition = _int(card.get("ambition"))
    actor["ambition"] = _int(actor.get("ambition")) + ambition

    text = f"{actor['name']} summoned {card['name']} to {lane}."
    match["log"].append(text)
    _message(
        context,
        match,
        "card_played",
        actor=actor_key,
        text=text,
        card_id=card.get("id"),
        card_name=card.get("name"),
        instance_id=instance.get("instance_id"),
        kind=card.get("kind"),
        lane=lane,
    )
    if ambition:
        _message(
            context,
            match,
            "ambition_gain",
            actor=actor_key,
            text=f"{actor['name']} gained {ambition} Ambition from {card['name']}.",
            amount=ambition,
            card_id=card.get("id"),
            source="card_play",
        )

    return {"kind": "creature", "instance": instance, "ambition": ambition}


def _resolve_support(
    match: Dict[str, Any],
    actor_key: str,
    card: Dict[str, Any],
    context: EffectContext,
) -> Dict[str, Any]:
    actor = match[actor_key]
    field = actor.setdefault("field", {})
    old = field.get("support")

    if old:
        actor.setdefault("discard", []).append(old)
        text = f"{actor['name']} replaced support {old['name']}."
        match["log"].append(text)
        context["add_event"](match, "card_replaced", actor=actor_key, text=text, card_id=old.get("id"))

    field["support"] = deepcopy(card)
    ambition = _int(card.get("ambition"))
    actor["ambition"] = _int(actor.get("ambition")) + ambition

    text = f"{actor['name']} played support {card['name']}."
    match["log"].append(text)
    _message(
        context,
        match,
        "card_played",
        actor=actor_key,
        text=text,
        card_id=card.get("id"),
        card_name=card.get("name"),
        kind=card.get("kind"),
    )
    if ambition:
        _message(
            context,
            match,
            "ambition_gain",
            actor=actor_key,
            text=f"{actor['name']} gained {ambition} Ambition from {card['name']}.",
            amount=ambition,
            card_id=card.get("id"),
            source="card_play",
        )

    return {"kind": "support", "ambition": ambition}


def _target_contract(context: EffectContext) -> Dict[str, Any]:
    value = context.get("target_contract")
    return value if isinstance(value, dict) else {}


def _scaled_value(value: Any, default: int = 0, cap: int = 8) -> int:
    raw = _int(value, default)
    if raw > 20:
        raw = round(raw / 100)
    return max(0, min(cap, raw))


def _target_owner_key(actor_key: str, target: Dict[str, Any], fallback_enemy: bool = True) -> str:
    owner = str(target.get("target_owner") or "").strip().lower()
    if owner in {"player", "self", actor_key}:
        return actor_key
    if owner in {"opponent", "enemy", "bot"}:
        return _enemy_side(actor_key)
    return _enemy_side(actor_key) if fallback_enemy else actor_key


def _apply_creature_damage(
    match: Dict[str, Any],
    owner_key: str,
    lane: str,
    amount: int,
    card: Dict[str, Any],
    context: EffectContext,
    actor_key: str,
) -> Dict[str, Any]:
    ensure_board: Callable[[Dict[str, Any]], Dict[str, Any]] = context["ensure_board"]
    board = ensure_board(match[owner_key])
    creature = board.get(lane)
    if not creature:
        return {"requested": amount, "dealt": 0, "blocked": 0, "target": f"{owner_key}:{lane}"}

    requested = max(0, int(amount or 0))
    shield = _int(creature.get("shield"))
    blocked = min(shield, requested)
    creature["shield"] = max(0, shield - blocked)
    dealt = max(0, requested - blocked)
    hp_before = _int(creature.get("current_hp") if creature.get("current_hp") is not None else creature.get("hp"), 1)
    creature["current_hp"] = hp_before - dealt
    hp_after = _int(creature.get("current_hp"))
    _message(
        context,
        match,
        "creature_damage",
        actor=actor_key,
        target=owner_key,
        text=f"{creature.get('name', 'Creature')} received {dealt} damage.",
        lane=lane,
        attacker=_creature_ref(actor_key, {"card_id": _card_id(card), "name": card.get("name")}),
        defender=_creature_ref(owner_key, creature),
        damage=dealt,
        amount=dealt,
        requested_damage=requested,
        shield_blocked=blocked,
        hp_before=hp_before,
        hp_after=hp_after,
        card_id=card.get("id"),
        card_name=card.get("name"),
    )
    context["cleanup_dead_creatures"](match, owner_key)
    return {"requested": requested, "dealt": dealt, "blocked": blocked, "target": f"{owner_key}:{lane}"}


def apply_direct_damage(
    match: Dict[str, Any],
    actor_key: str,
    target_key: str,
    amount: int,
    card: Dict[str, Any],
    context: EffectContext,
) -> Dict[str, Any]:
    target_player = match[target_key]
    hp_before = _int(target_player.get("hp"))
    dealt = context["deal_hero_damage"](target_player, amount)
    hp_after = _int(target_player.get("hp"))

    if target_key != actor_key:
        match[actor_key]["last_damage_dealt"] = _int(match[actor_key].get("last_damage_dealt")) + dealt

    _message(
        context,
        match,
        "direct_attack",
        actor=actor_key,
        target=target_key,
        text=f"{match[actor_key]['name']} dealt {dealt} direct damage.",
        amount=dealt,
        damage=amount,
        card_id=card.get("id"),
        card_name=card.get("name"),
        target_side=target_key,
    )
    _message(
        context,
        match,
        "hero_damage",
        actor=actor_key,
        target=target_key,
        text=f"{target_player['name']} received {dealt} damage.",
        amount=dealt,
        damage=dealt,
        hp_before=hp_before,
        hp_after=hp_after,
        card_id=card.get("id"),
        card_name=card.get("name"),
        target_side=target_key,
    )
    return {"requested": amount, "dealt": dealt, "target": target_key}


def apply_shield(
    match: Dict[str, Any],
    actor_key: str,
    amount: int,
    card: Dict[str, Any],
    context: EffectContext,
    target: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    amount = max(0, int(amount or 0))
    if amount <= 0:
        return {"amount": 0, "target": "none"}

    target = target or {}
    owner_key = _target_owner_key(actor_key, target, fallback_enemy=False)
    lane = str(target.get("target_lane") or "").strip().lower()
    if target.get("target_type") == "creature" and lane:
        ensure_board: Callable[[Dict[str, Any]], Dict[str, Any]] = context["ensure_board"]
        creature = ensure_board(match[owner_key]).get(lane)
        if creature:
            creature["shield"] = _int(creature.get("shield")) + amount
            _message(
                context,
                match,
                "shield_gain",
                actor=actor_key,
                target=owner_key,
                text=f"{creature.get('name', 'Creature')} gained {amount} shield.",
                amount=amount,
                lane=lane,
                target_type="creature",
                card_id=card.get("id"),
                card_name=card.get("name"),
                source="spell_effect",
            )
            return {"amount": amount, "target": f"{owner_key}:{lane}"}

    match[owner_key]["shield"] = _int(match[owner_key].get("shield")) + amount
    _message(
        context,
        match,
        "shield_gain",
        actor=owner_key,
        target=owner_key,
        text=f"{match[owner_key]['name']} gained {amount} shield.",
        amount=amount,
        card_id=card.get("id"),
        card_name=card.get("name"),
        source="spell_effect",
    )
    return {"amount": amount, "target": owner_key}


def apply_heal(
    match: Dict[str, Any],
    actor_key: str,
    amount: int,
    card: Dict[str, Any],
    context: EffectContext,
    target: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    amount = max(0, int(amount or 0))
    if amount <= 0:
        return {"amount": 0, "target": "none"}

    target = target or {}
    owner_key = _target_owner_key(actor_key, target, fallback_enemy=False)
    lane = str(target.get("target_lane") or "").strip().lower()
    if target.get("target_type") == "creature" and lane:
        ensure_board: Callable[[Dict[str, Any]], Dict[str, Any]] = context["ensure_board"]
        creature = ensure_board(match[owner_key]).get(lane)
        if creature:
            before = _int(creature.get("current_hp") if creature.get("current_hp") is not None else creature.get("hp"))
            max_hp = _int(creature.get("max_hp") or creature.get("hp"), before)
            after = min(max_hp, before + amount)
            creature["current_hp"] = after
            _message(
                context,
                match,
                "spell_heal",
                actor=actor_key,
                target=owner_key,
                text=f"{creature.get('name', 'Creature')} healed {after - before} HP.",
                amount=after - before,
                lane=lane,
                target_type="creature",
                hp_before=before,
                hp_after=after,
                card_id=card.get("id"),
                card_name=card.get("name"),
            )
            return {"amount": after - before, "target": f"{owner_key}:{lane}"}

    target_player = match[owner_key]
    before = _int(target_player.get("hp"))
    max_hp = _int(target_player.get("max_hp"), before)
    after = min(max_hp, before + amount)
    target_player["hp"] = after
    _message(
        context,
        match,
        "spell_heal",
        actor=actor_key,
        target=owner_key,
        text=f"{target_player['name']} healed {after - before} HP.",
        amount=after - before,
        hp_before=before,
        hp_after=after,
        card_id=card.get("id"),
        card_name=card.get("name"),
    )
    return {"amount": after - before, "target": owner_key}


def apply_ambition_gain(
    match: Dict[str, Any],
    actor_key: str,
    amount: int,
    card: Dict[str, Any],
    context: EffectContext,
) -> int:
    amount = max(0, int(amount or 0))
    if amount <= 0:
        return 0
    match[actor_key]["ambition"] = _int(match[actor_key].get("ambition")) + amount
    _message(
        context,
        match,
        "spell_ambition",
        actor=actor_key,
        target=actor_key,
        text=f"{match[actor_key]['name']} gained {amount} Ambition from {card.get('name', 'a spell')}.",
        amount=amount,
        card_id=card.get("id"),
        card_name=card.get("name"),
        source="spell_effect",
    )
    _message(
        context,
        match,
        "ambition_gain",
        actor=actor_key,
        text=f"{match[actor_key]['name']} gained {amount} Ambition.",
        amount=amount,
        card_id=card.get("id"),
        source="spell_effect",
    )
    return amount


def resolve_spell_effect(
    match: Dict[str, Any],
    actor_key: str,
    card: Dict[str, Any],
    context: EffectContext,
) -> Dict[str, Any]:
    actor = match[actor_key]
    enemy_key = _enemy_side(actor_key)
    enemy = match[enemy_key]
    intent = actor.get("intent") or "Focus"
    target = context.get("target")
    target_contract = _target_contract(context)

    damage = _int(card.get("damage"))
    shield = _int(card.get("shield"))
    heal = _int(card.get("heal"))
    ambition = _int(card.get("ambition"))
    draw = _int(card.get("draw"))
    effect_type = infer_spell_effect(card)

    if effect_type in {"damage", "drain"} and damage <= 0:
        damage = _scaled_value(card.get("value"), default=_int(card.get("cost"), 1) + 1, cap=6)
    if effect_type == "shield" and shield <= 0:
        shield = _scaled_value(card.get("value"), default=_int(card.get("cost"), 1) + 3, cap=8)
    if effect_type in {"heal", "drain"} and heal <= 0:
        heal = _scaled_value(card.get("value"), default=max(3, damage), cap=8)
    if effect_type == "ambition" and ambition <= 0:
        ambition = max(2, _scaled_value(card.get("value"), default=2, cap=5))

    if card.get("id") == "pressure_move" and intent == "Strike":
        damage += 1
    if intent == "Guard":
        shield += 2
    if intent == "Focus":
        ambition += 2
    if context["card_has_keyword"](card, "focused"):
        ambition += 1

    text = f"{actor['name']} cast {card['name']}."
    _message(
        context,
        match,
        "card_played",
        actor=actor_key,
        text=text,
        card_id=card.get("id"),
        card_name=card.get("name"),
        kind=card.get("kind"),
        target=target,
    )
    _message(
        context,
        match,
        "spell_cast",
        actor=actor_key,
        target=target_contract.get("target_owner") or target,
        text=text,
        card_id=card.get("id"),
        card_name=card.get("name"),
        effect_type=effect_type,
        cast_mode=target_contract.get("cast_mode") or "cast",
    )
    if target or target_contract:
        _message(
            context,
            match,
            "spell_targeted",
            actor=actor_key,
            target=target_contract.get("target_owner") or target,
            text=f"{card['name']} targeted {target_contract.get('label') or target or 'self'}.",
            card_id=card.get("id"),
            card_name=card.get("name"),
            target_type=target_contract.get("target_type"),
            target_owner=target_contract.get("target_owner"),
            target_lane=target_contract.get("target_lane"),
        )

    shield_result = apply_shield(match, actor_key, shield, card, context, target_contract) if shield else {"amount": 0}
    if shield_result.get("amount"):
        _message(
            context,
            match,
            "spell_shield",
            actor=actor_key,
            target=shield_result.get("target"),
            text=f"{card.get('name', 'Spell')} added {shield_result.get('amount')} shield.",
            amount=shield_result.get("amount"),
            card_id=card.get("id"),
            card_name=card.get("name"),
        )
    heal_result = apply_heal(match, actor_key, heal, card, context, target_contract) if heal else {"amount": 0}
    damage_result = _resolve_damage(match, actor_key, enemy_key, card, damage, target, context)
    ambition_result = apply_ambition_gain(match, actor_key, ambition, card, context) if ambition else 0

    if not any([damage_result.get("dealt"), shield_result.get("amount"), heal_result.get("amount"), ambition_result, draw]):
        _message(
            context,
            match,
            "spell_noop",
            actor=actor_key,
            target=target,
            text=f"{card['name']} resolved with no immediate effect.",
            card_id=card.get("id"),
            card_name=card.get("name"),
            effect_type=effect_type,
        )

    if draw:
        context["draw_cards"](actor, draw)
        _message(
            context,
            match,
            "card_draw",
            actor=actor_key,
            text=f"{actor['name']} drew {draw} card.",
            amount=draw,
            card_id=card.get("id"),
            source="card_effect",
        )

    return {
        "kind": "spell",
        "effect_type": effect_type,
        "damage": damage_result,
        "shield": shield_result,
        "heal": heal_result,
        "ambition": ambition_result,
        "draw": draw,
        "target": target or "enemy_hero",
    }


def _resolve_trap_prepare(
    match: Dict[str, Any],
    actor_key: str,
    card: Dict[str, Any],
    context: EffectContext,
) -> Dict[str, Any]:
    actor = match[actor_key]
    trap_card = deepcopy(card)
    effect = infer_trap_effect(trap_card)
    trap = {
        "id": f"{actor_key}-trap-{match.get('round', 0)}-{_card_id(trap_card)}-{len(actor.get('prepared_traps') or []) + 1}",
        "card": trap_card,
        "owner": actor_key,
        "prepared_round": int(match.get("round") or 0),
        "trigger_type": "on_attack",
        "effect": effect,
        "consumed": False,
    }
    actor.setdefault("prepared_traps", []).append(trap)
    actor.setdefault("field", {})["traps"] = actor["prepared_traps"]

    ambition = _int(card.get("ambition"))
    actor["ambition"] = _int(actor.get("ambition")) + ambition
    text = f"{actor['name']} prepared trap {card['name']}."
    match["log"].append(text)
    _message(
        context,
        match,
        "trap_prepared",
        actor=actor_key,
        text=text,
        card_id=card.get("id"),
        card_name=card.get("name"),
        kind="trap",
        effect_type=effect,
        prepared=True,
    )
    if ambition:
        _message(
            context,
            match,
            "ambition_gain",
            actor=actor_key,
            text=f"{actor['name']} gained {ambition} Ambition from {card['name']}.",
            amount=ambition,
            card_id=card.get("id"),
            source="trap_prepare",
        )

    return {"kind": "trap", "trap": trap, "ambition": ambition}


def _resolve_damage(
    match: Dict[str, Any],
    actor_key: str,
    enemy_key: str,
    card: Dict[str, Any],
    damage: int,
    target: Optional[str],
    context: EffectContext,
) -> Dict[str, Any]:
    if damage <= 0:
        return {"requested": 0, "dealt": 0, "target": target or "none"}

    if target == "self" and card.get("kind") == "guard":
        target = None

    target_contract = _target_contract(context)
    if isinstance(target, str) and target.startswith("lane:"):
        lane = target.split(":", 1)[1]
        ensure_board: Callable[[Dict[str, Any]], Dict[str, Any]] = context["ensure_board"]
        enemy_board = ensure_board(match[enemy_key])
        creature = enemy_board.get(lane)

        if creature:
            damage_result = _apply_creature_damage(match, enemy_key, lane, damage, card, context, actor_key)
            _message(
                context,
                match,
                "spell_damage",
                actor=actor_key,
                target=enemy_key,
                text=f"{card.get('name', 'Spell')} dealt {damage_result.get('dealt', 0)} damage to {creature.get('name', 'Creature')}.",
                lane=lane,
                card_id=card.get("id"),
                card_name=card.get("name"),
                amount=damage_result.get("dealt", 0),
                damage=damage_result.get("dealt", 0),
            )
            return damage_result

    if target_contract.get("target_type") == "creature" and target_contract.get("target_lane"):
        owner_key = _target_owner_key(actor_key, target_contract, fallback_enemy=True)
        lane = str(target_contract.get("target_lane"))
        damage_result = _apply_creature_damage(match, owner_key, lane, damage, card, context, actor_key)
        if damage_result.get("dealt"):
            _message(
                context,
                match,
                "spell_damage",
                actor=actor_key,
                target=owner_key,
                text=f"{card.get('name', 'Spell')} dealt {damage_result.get('dealt', 0)} damage.",
                lane=lane,
                card_id=card.get("id"),
                card_name=card.get("name"),
                amount=damage_result.get("dealt", 0),
                damage=damage_result.get("dealt", 0),
            )
        return damage_result

    target_key = actor_key if target == "self" else enemy_key
    if target_contract.get("target_type") == "hero":
        target_key = _target_owner_key(actor_key, target_contract, fallback_enemy=True)
    damage_result = apply_direct_damage(match, actor_key, target_key, damage, card, context)
    _message(
        context,
        match,
        "spell_damage",
        actor=actor_key,
        target=target_key,
        text=f"{card.get('name', 'Spell')} dealt {damage_result.get('dealt', 0)} damage.",
        amount=damage_result.get("dealt", 0),
        damage=damage_result.get("dealt", 0),
        card_id=card.get("id"),
        card_name=card.get("name"),
        target_side=target_key,
    )
    return damage_result
