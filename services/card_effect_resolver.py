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
    kind = str(card.get("kind") or "spell")

    if kind == "creature":
        return _resolve_creature(match, actor_key, card, context)
    if kind == "support":
        return _resolve_support(match, actor_key, card, context)

    return _resolve_instant(match, actor_key, card, context)


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


def _resolve_instant(
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

    damage = _int(card.get("damage"))
    shield = _int(card.get("shield"))
    ambition = _int(card.get("ambition"))
    draw = _int(card.get("draw"))

    if card.get("id") == "pressure_move" and intent == "Strike":
        damage += 1
    if intent == "Guard":
        shield += 2
    if intent == "Focus":
        ambition += 1
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

    if shield:
        actor["shield"] = _int(actor.get("shield")) + shield
        _message(
            context,
            match,
            "shield_gain",
            actor=actor_key,
            text=f"{actor['name']} gained {shield} shield.",
            amount=shield,
            card_id=card.get("id"),
            source="card_effect",
        )

    damage_result = _resolve_damage(match, actor_key, enemy_key, card, damage, target, context)

    actor["ambition"] = _int(actor.get("ambition")) + ambition
    if ambition:
        _message(
            context,
            match,
            "ambition_gain",
            actor=actor_key,
            text=f"{actor['name']} gained {ambition} Ambition.",
            amount=ambition,
            card_id=card.get("id"),
            source="card_effect",
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
        "kind": "instant",
        "damage": damage_result,
        "shield": shield,
        "ambition": ambition,
        "draw": draw,
        "target": target or "enemy_hero",
    }


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

    if isinstance(target, str) and target.startswith("lane:"):
        lane = target.split(":", 1)[1]
        ensure_board: Callable[[Dict[str, Any]], Dict[str, Any]] = context["ensure_board"]
        enemy_board = ensure_board(match[enemy_key])
        creature = enemy_board.get(lane)

        if creature:
            hp_before = _int(creature.get("current_hp") if creature.get("current_hp") is not None else creature.get("hp"), 1)
            creature["current_hp"] = hp_before - damage
            hp_after = _int(creature.get("current_hp"))
            _message(
                context,
                match,
                "creature_damage",
                actor=actor_key,
                target=enemy_key,
                text=f"{creature.get('name', 'Creature')} received {damage} damage.",
                lane=lane,
                attacker=_creature_ref(actor_key, {"card_id": _card_id(card), "name": card.get("name")}),
                defender=_creature_ref(enemy_key, creature),
                damage=damage,
                hp_before=hp_before,
                hp_after=hp_after,
                card_id=card.get("id"),
            )
            context["cleanup_dead_creatures"](match, enemy_key)
            return {"requested": damage, "dealt": damage, "target": target}

    target_key = actor_key if target == "self" else enemy_key
    target_player = match[target_key]
    hp_before = _int(target_player.get("hp"))
    dealt = context["deal_hero_damage"](target_player, damage)
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
        damage=damage,
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
    return {"requested": damage, "dealt": dealt, "target": target_key}
