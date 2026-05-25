"""Pure deterministic reducers for Rebirth event sourcing.

Reducers never emit events, read globals, call random, or mutate the caller's
state. Each reducer receives a serializable state snapshot and one GameEvent,
then returns a new serializable state snapshot.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, List, Optional

from services.rebirth_domain import REDUCER_VERSION


Reducer = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


def _payload(event: Dict[str, Any]) -> Dict[str, Any]:
    payload = event.get("payload") or {}
    return payload if isinstance(payload, dict) else {}


def _side_name(event: Dict[str, Any]) -> Optional[str]:
    side = str(event.get("owner_id") or event.get("actor") or "")
    return side if side in {"player", "bot"} else None


def _iter_card_containers(state: Dict[str, Any]) -> Iterable[List[Any]]:
    for side_name in ("player", "bot"):
        side = state.get(side_name) or {}
        for key in ("field", "battlefield", "hand", "deck", "discard", "traps"):
            value = side.get(key)
            if isinstance(value, list):
                yield value
        played = side.get("played_card")
        if played:
            yield [played]


def _find_card(state: Dict[str, Any], target_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not target_id:
        return None
    for container in _iter_card_containers(state):
        for card in container:
            if isinstance(card, dict) and (card.get("instance_id") == target_id or card.get("id") == target_id):
                return card
    return None


def _statuses(card: Dict[str, Any]) -> Dict[str, Any]:
    statuses = card.get("statuses")
    if not isinstance(statuses, dict):
        statuses = {}
        card["statuses"] = statuses
    return statuses


def _copy_state(state: Dict[str, Any]) -> Dict[str, Any]:
    copied = deepcopy(state)
    copied["reducer_version"] = copied.get("reducer_version") or REDUCER_VERSION
    return copied


def reduce_resource_consumed(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    if not side_name:
        return next_state
    resource = str(payload.get("resource") or "mana")
    amount = max(0, int(payload.get("amount", payload.get("mana", 1)) or 0))
    if resource in {"mana", "energy"}:
        side = next_state[side_name]
        side["energy"] = max(0, int(side.get("energy", 0) or 0) - amount)
    return next_state


def reduce_stat_modifier_applied(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    card = _find_card(next_state, event.get("target_id") or payload.get("instance_id"))
    if not card:
        return next_state
    stat = str(payload.get("stat") or "").lower()
    amount = int(payload.get("amount", 0) or 0)
    if stat in {"attack", "atk", "power"}:
        card["base_attack"] = int(card.get("base_attack", card.get("attack", card.get("power", 0))) or 0)
        card["attack"] = int(card.get("attack", card.get("power", 0)) or 0) + amount
        card["power"] = int(card.get("power", card.get("attack", 0)) or 0) + amount
        if payload.get("duration") == "permanent":
            card["permanent_attack_bonus"] = int(card.get("permanent_attack_bonus", 0) or 0) + amount
    if stat in {"guard", "grd"}:
        card["base_guard"] = int(card.get("base_guard", card.get("guard", 0)) or 0)
        card["guard"] = int(card.get("guard", 0) or 0) + amount
        card["max_guard"] = int(card.get("max_guard", card.get("guard", 0)) or 0) + amount
        card["current_guard"] = int(card.get("current_guard", card.get("guard", 0)) or 0) + amount
    return next_state


def reduce_shield_granted(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    card = _find_card(next_state, event.get("target_id") or payload.get("instance_id"))
    if not card:
        return next_state
    amount = max(0, int(payload.get("guard_bonus", payload.get("amount", 0)) or 0))
    status_name = str(payload.get("status") or "aegis_sentinel_shield")
    if status_name in _statuses(card):
        return next_state
    card["base_guard"] = int(card.get("base_guard", card.get("guard", 0)) or 0)
    card["max_guard"] = int(card.get("max_guard", card.get("guard", 0)) or 0) + amount
    card["current_guard"] = int(card.get("current_guard", card.get("guard", 0)) or 0) + amount
    card["temporary_guard_bonus"] = int(card.get("temporary_guard_bonus", 0) or 0) + amount
    card["shield_expires_on"] = str(payload.get("expires_on") or "DAMAGE_RESOLVED")
    _statuses(card)[status_name] = {
        "guard": amount,
        "source_card_id": event.get("source_card_id"),
        "expires_on": card["shield_expires_on"],
        "lifecycle": "next_damage_resolved",
    }
    return next_state


def reduce_unit_exhausted(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    card = _find_card(next_state, event.get("target_id") or payload.get("target_instance_id"))
    if not card:
        return next_state
    card["exhausted"] = True
    card["has_acted"] = True
    _statuses(card)["shadow_reaper_exhausted"] = {
        "turns": max(1, int(payload.get("duration_turns", 1) or 1)),
        "source_card_id": event.get("source_card_id"),
        "expires_on": "TURN_STARTED",
        "lifecycle": "next_turn_started",
    }
    return next_state


def reduce_shield_broken(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    card = _find_card(next_state, event.get("target_id") or payload.get("instance_id"))
    if not card:
        return next_state
    status_name = str(payload.get("status") or "aegis_sentinel_shield")
    status = _statuses(card).pop(status_name, None) or {}
    amount = max(0, int(payload.get("guard_bonus", status.get("guard", 0)) or 0))
    card["temporary_guard_bonus"] = max(0, int(card.get("temporary_guard_bonus", 0) or 0) - amount)
    card["max_guard"] = max(int(card.get("guard", 0) or 0), int(card.get("max_guard", card.get("guard", 0)) or 0) - amount)
    card["current_guard"] = max(0, int(card.get("current_guard", card.get("guard", 0)) or 0) - amount)
    card.pop("shield_expires_on", None)
    return next_state


def reduce_status_expired(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    card = _find_card(next_state, event.get("target_id") or payload.get("instance_id"))
    if not card:
        return next_state
    status_name = str(payload.get("status") or "")
    if status_name:
        _statuses(card).pop(status_name, None)
    if status_name == "shadow_reaper_exhausted":
        card["exhausted"] = False
    return next_state


def reduce_noop(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    return _copy_state(state)


REDUCER_REGISTRY: Dict[str, Reducer] = {
    "RESOURCE_CONSUMED": reduce_resource_consumed,
    "STAT_MODIFIER_APPLIED": reduce_stat_modifier_applied,
    "SHIELD_GRANTED": reduce_shield_granted,
    "UNIT_EXHAUSTED": reduce_unit_exhausted,
    "SHIELD_BROKEN": reduce_shield_broken,
    "STATUS_EXPIRED": reduce_status_expired,
}

REDUCER_ORDER = tuple(sorted(REDUCER_REGISTRY))


def reducer_for(event_type: str) -> Reducer:
    return REDUCER_REGISTRY.get(str(event_type or ""), reduce_noop)


def reduce_event(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    return reducer_for(str(event.get("event_type") or event.get("type") or ""))(state, event)


def reduce_events(base_state: Dict[str, Any], events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    state = _copy_state(base_state)
    ordered = sorted(events or [], key=lambda event: (int(event.get("sequence_id", event.get("version", 0)) or 0), str(event.get("event_type", event.get("type", "")))))
    for event in ordered:
        state = reduce_event(state, event)
    return state
