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
    payload = _payload(event)
    for value in (payload.get("side"), event.get("target_id"), event.get("owner_id"), event.get("actor")):
        side = str(value or "")
        if side in {"player", "bot"}:
            return side
    return None


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


def _side_statuses(side: Dict[str, Any]) -> Dict[str, Any]:
    statuses = side.get("statuses")
    if not isinstance(statuses, dict):
        statuses = {}
        side["statuses"] = statuses
    return statuses


def _side_slots(side: Dict[str, Any]) -> List[Any]:
    slots = side.get("field")
    if not isinstance(slots, list):
        slots = []
    slots = list(slots[:3])
    while len(slots) < 3:
        slots.append(None)
    return slots


def _sync_side_field(side: Dict[str, Any]) -> None:
    slots = _side_slots(side)
    normalized = []
    for index, card in enumerate(slots):
        if not isinstance(card, dict):
            slots[index] = None
            continue
        card["field_slot"] = index
        card["slot"] = index + 1
        normalized.append(card)
    side["field"] = slots
    side["battlefield"] = normalized


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
        side_name = _side_name(event)
        if side_name:
            _side_statuses(next_state[side_name]).pop(str(payload.get("status") or "shield"), None)
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


def reduce_cards_drawn(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    if not side_name:
        return next_state
    side = next_state[side_name]
    amount = max(0, int(payload.get("amount", payload.get("drawn", 0)) or 0))
    wanted_ids = [str(card_id) for card_id in payload.get("card_ids", []) if card_id]
    drawn = []
    deck = list(side.get("deck") or [])
    remaining = []
    for card in deck:
        if amount <= len(drawn):
            remaining.append(card)
            continue
        if wanted_ids and str(card.get("id")) not in wanted_ids:
            remaining.append(card)
            continue
        drawn.append(card)
    side["deck"] = remaining
    side.setdefault("hand", []).extend(drawn)
    return next_state


def reduce_status_applied(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    status_name = str(payload.get("status") or "").strip().lower()
    if not status_name:
        return next_state
    turns = max(1, int(payload.get("turns", payload.get("duration_turns", 1)) or 1))
    potency = max(1, int(payload.get("potency", payload.get("amount", 1)) or 1))
    target_card = _find_card(next_state, event.get("target_id") or payload.get("instance_id") or payload.get("target_instance_id"))
    if target_card:
        current = _statuses(target_card).get(status_name, {})
        _statuses(target_card)[status_name] = {
            **current,
            "turns": max(turns, int(current.get("turns", 0) or 0)),
            "potency": max(potency, int(current.get("potency", 0) or 0)),
            "source_card_id": event.get("source_card_id"),
        }
        return next_state
    side_name = _side_name(event)
    if side_name:
        current = _side_statuses(next_state[side_name]).get(status_name, {})
        _side_statuses(next_state[side_name])[status_name] = {
            **current,
            "turns": max(turns, int(current.get("turns", 0) or 0)),
            "potency": max(potency, int(current.get("potency", 0) or 0)),
        }
    return next_state


def reduce_status_cleansed(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    target_card = _find_card(next_state, event.get("target_id") or _payload(event).get("instance_id"))
    if target_card:
        _statuses(target_card).clear()
        return next_state
    side_name = _side_name(event)
    if side_name:
        _side_statuses(next_state[side_name]).clear()
    return next_state


def reduce_damage_resolved(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    if not side_name or "amount" not in payload:
        return next_state
    side = next_state[side_name]
    amount = max(0, int(payload.get("amount", 0) or 0))
    shield = _side_statuses(side).get("shield")
    if shield and amount:
        absorbed = min(amount, max(0, int(shield.get("potency", shield.get("amount", 0)) or 0)))
        amount -= absorbed
        shield["potency"] = max(0, int(shield.get("potency", 0) or 0) - absorbed)
        if shield["potency"] <= 0:
            _side_statuses(side).pop("shield", None)
    side["hp"] = max(0, int(side.get("hp", 0) or 0) - amount)
    side["wounded"] = amount > 0
    return next_state


def reduce_health_recovered(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    if not side_name:
        return next_state
    side = next_state[side_name]
    amount = max(0, int(payload.get("amount", 0) or 0))
    side["hp"] = min(int(side.get("max_hp", side.get("hp", 0)) or 0), int(side.get("hp", 0) or 0) + amount)
    return next_state


def reduce_shield_applied(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    if not side_name:
        return next_state
    amount = max(1, int(payload.get("amount", payload.get("potency", 1)) or 1))
    turns = max(1, int(payload.get("turns", 1) or 1))
    _side_statuses(next_state[side_name])["shield"] = {"turns": turns, "potency": amount}
    return next_state


def reduce_card_discarded(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    card = payload.get("card")
    if not side_name or not isinstance(card, dict):
        return next_state
    next_state[side_name].setdefault("discard", []).append(deepcopy(card))
    return next_state


def reduce_unit_destroyed(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    target_id = event.get("target_id") or payload.get("instance_id")
    if not side_name or not target_id:
        return next_state
    side = next_state[side_name]
    defeated = None
    slots = _side_slots(side)
    for index, card in enumerate(slots):
        if isinstance(card, dict) and (card.get("instance_id") == target_id or card.get("id") == target_id):
            defeated = deepcopy(card)
            slots[index] = None
            break
    side["field"] = slots
    side["battlefield"] = [
        card
        for card in side.get("battlefield", [])
        if not isinstance(card, dict) or (card.get("instance_id") != target_id and card.get("id") != target_id)
    ]
    _sync_side_field(side)
    if defeated:
        defeated["defeated"] = True
        side.setdefault("discard", []).append(defeated)
    return next_state


def reduce_turn_status_ticked(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    side_name = _side_name(event)
    if not side_name:
        return next_state
    side = next_state[side_name]
    statuses = _side_statuses(side)
    damage = 0
    for status_name in ("burn", "decay"):
        status = statuses.get(status_name)
        if status:
            damage += max(1, int(status.get("potency", 1) or 1))
    if damage:
        side["hp"] = max(0, int(side.get("hp", 0) or 0) - damage)
        side["wounded"] = True
    expired = []
    for status_name, status in list(statuses.items()):
        turns = int(status.get("turns", 1) or 1) - 1
        if turns <= 0:
            expired.append(status_name)
        else:
            status["turns"] = turns
    for status_name in expired:
        statuses.pop(status_name, None)
    return next_state


def reduce_noop(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    return _copy_state(state)


REDUCER_REGISTRY: Dict[str, Reducer] = {
    "CARD_DISCARDED": reduce_card_discarded,
    "CARDS_DRAWN": reduce_cards_drawn,
    "DAMAGE_RESOLVED": reduce_damage_resolved,
    "HEALTH_RECOVERED": reduce_health_recovered,
    "RESOURCE_CONSUMED": reduce_resource_consumed,
    "SHIELD_APPLIED": reduce_shield_applied,
    "STAT_MODIFIER_APPLIED": reduce_stat_modifier_applied,
    "STATUS_APPLIED": reduce_status_applied,
    "STATUS_CLEANSED": reduce_status_cleansed,
    "SHIELD_GRANTED": reduce_shield_granted,
    "TURN_STATUS_TICKED": reduce_turn_status_ticked,
    "UNIT_DESTROYED": reduce_unit_destroyed,
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
