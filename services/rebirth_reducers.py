"""Pure deterministic reducers for Rebirth event sourcing.

Reducers never emit events, read globals, call random, or mutate canonical
gameplay entities owned by the caller. Each reducer receives a serializable
state snapshot and one GameEvent, then returns a new gameplay state while
sharing append-only transport history.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, List, Optional

from services.rebirth_domain import REDUCER_VERSION
from services.rebirth_profiler import current_profiler


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


def _matching_cards(state: Dict[str, Any], target_id: Optional[str]) -> List[Dict[str, Any]]:
    if not target_id:
        return []
    matches = []
    seen = set()
    for container in _iter_card_containers(state):
        for card in container:
            if not isinstance(card, dict):
                continue
            if card.get("instance_id") != target_id and card.get("id") != target_id:
                continue
            marker = id(card)
            if marker in seen:
                continue
            seen.add(marker)
            matches.append(card)
    return matches


def _remove_card_from_list(cards: List[Any], *, instance_id: Optional[str] = None, card_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            continue
        if instance_id and card.get("instance_id") == instance_id:
            return cards.pop(index)
        if not instance_id and card_id and card.get("id") == card_id:
            return cards.pop(index)
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
    """Copy canonical gameplay state without cloning append-only history.

    Event, command and snapshot streams become particularly large during
    replay reconstruction, but reducers never mutate their historical rows.
    Copying only mutable canonical entities keeps reducer isolation while
    avoiding a growing full-match deepcopy for every event.
    """
    profiler = current_profiler()
    if profiler:
        with profiler.timer("clone_cost", detail="gameplay_entities"):
            copied = dict(state)
            copied["player"] = deepcopy(state.get("player") or {})
            copied["bot"] = deepcopy(state.get("bot") or {})
            copied["result"] = deepcopy(state.get("result"))
            copied["last_clash"] = deepcopy(state.get("last_clash"))
    else:
        copied = dict(state)
        copied["player"] = deepcopy(state.get("player") or {})
        copied["bot"] = deepcopy(state.get("bot") or {})
        copied["result"] = deepcopy(state.get("result"))
        copied["last_clash"] = deepcopy(state.get("last_clash"))
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
    cards = _matching_cards(next_state, event.get("target_id") or payload.get("instance_id"))
    if not cards:
        return next_state
    stat = str(payload.get("stat") or "").lower()
    amount = int(payload.get("amount", 0) or 0)
    for card in cards:
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
    explicit_cards = [deepcopy(card) for card in payload.get("cards", []) if isinstance(card, dict)]
    wanted_instances = [str(instance_id) for instance_id in payload.get("instance_ids", []) if instance_id]
    wanted_ids = [str(card_id) for card_id in payload.get("card_ids", []) if card_id]
    if explicit_cards:
        wanted_instances = [str(card.get("instance_id")) for card in explicit_cards if card.get("instance_id")]
    drawn = []
    deck = list(side.get("deck") or [])
    remaining = []
    for card in deck:
        if amount <= len(drawn):
            remaining.append(card)
            continue
        if wanted_instances and str(card.get("instance_id")) not in wanted_instances:
            remaining.append(card)
            continue
        if not wanted_instances and wanted_ids and str(card.get("id")) not in wanted_ids:
            remaining.append(card)
            continue
        drawn.append(card)
    if explicit_cards and not drawn:
        drawn = explicit_cards[:amount]
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
    guard_damage = payload.get("guard_damage") or {}
    hero_damage = payload.get("hero_damage") or {}
    for side_name in ("player", "bot"):
        amount = None
        if payload.get("side") == side_name and "amount" in payload:
            amount = max(0, int(payload.get("amount", 0) or 0))
        elif side_name in payload and not payload.get("persistent_field"):
            amount = max(0, int(payload.get(side_name, 0) or 0))
        elif payload.get("persistent_field") and side_name in hero_damage:
            amount = max(0, int(hero_damage.get(side_name, 0) or 0))
        if amount is not None and amount > 0:
            side = next_state[side_name]
            shield = _side_statuses(side).get("shield")
            if shield:
                absorbed = min(amount, max(0, int(shield.get("potency", shield.get("amount", 0)) or 0)))
                amount -= absorbed
                shield["potency"] = max(0, int(shield.get("potency", 0) or 0) - absorbed)
                if shield["potency"] <= 0:
                    _side_statuses(side).pop("shield", None)
            side["hp"] = max(0, int(side.get("hp", 0) or 0) - amount)
            side["wounded"] = amount > 0
        card_damage = int((guard_damage or {}).get(side_name, 0) or 0)
        instance_id = payload.get(f"{side_name}_instance_id")
        cards = _matching_cards(next_state, instance_id)
        if cards and card_damage:
            for card in cards:
                card["current_guard"] = int(card.get("current_guard", card.get("guard", 0)) or 0) - card_damage
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


def reduce_card_played(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    if not side_name:
        return next_state
    side = next_state[side_name]
    _remove_card_from_list(side.setdefault("hand", []), instance_id=payload.get("instance_id"), card_id=payload.get("card_id"))
    cost = max(0, int(payload.get("cost", 0) or 0))
    if cost:
        side["energy"] = max(0, int(side.get("energy", 0) or 0) - cost)
    return next_state


def reduce_monster_summoned(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    card = deepcopy(payload.get("card") or {})
    if not side_name or not card:
        return next_state
    slot = int(payload.get("field_slot", card.get("field_slot", 0)) or 0)
    card["field_slot"] = slot
    card["slot"] = slot + 1
    card["current_guard"] = int(card.get("current_guard", card.get("guard", 0)) or 0)
    card["max_guard"] = int(card.get("max_guard", card.get("guard", 0)) or 0)
    side = next_state[side_name]
    slots = _side_slots(side)
    slots[slot] = card
    side["field"] = slots
    _sync_side_field(side)
    side["played_card"] = deepcopy(card)
    next_state["last_clash"] = None
    next_state["phase"] = "choose"
    next_state["turn_phase"] = "MAIN_PHASE"
    next_state["result"] = {"outcome": "Summon", "winner": None, "damage": {"player": 0, "bot": 0}, "effective_attack": {"player": 0, "bot": 0}}
    return next_state


def reduce_trap_armed(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    card = deepcopy(payload.get("card") or {})
    if not side_name or not card:
        return next_state
    side = next_state[side_name]
    _remove_card_from_list(side.setdefault("hand", []), instance_id=payload.get("instance_id"), card_id=payload.get("card_id"))
    cost = max(0, int(payload.get("cost", card.get("cost", 0)) or 0))
    if cost:
        side["energy"] = max(0, int(side.get("energy", 0) or 0) - cost)
    side.setdefault("traps", []).append(card)
    next_state["last_clash"] = None
    next_state["phase"] = "choose"
    next_state["turn_phase"] = "MAIN_PHASE"
    next_state["result"] = {"outcome": "Trap Armed", "winner": None, "damage": {"player": 0, "bot": 0}, "effective_attack": {"player": 0, "bot": 0}}
    return next_state


def reduce_trap_triggered(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    if not side_name:
        return next_state
    side = next_state[side_name]
    trap = _remove_card_from_list(side.setdefault("traps", []), instance_id=payload.get("instance_id"), card_id=payload.get("card_id"))
    discarded = deepcopy(payload.get("card") or trap or {})
    if discarded:
        discarded["armed"] = False
        discarded["revealed"] = True
        discarded["face_down"] = False
        side.setdefault("discard", []).append(discarded)
    return next_state


def reduce_attack_declared(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    attacker_side = str(event.get("owner_id") or event.get("actor") or "player")
    attacker_side = attacker_side if attacker_side in {"player", "bot"} else "player"
    defender_side = "bot" if attacker_side == "player" else "player"
    attacker = _find_card(next_state, payload.get("attacker_instance_id") or event.get("source_card_id"))
    if attacker:
        attacker["exhausted"] = True
        attacker["has_attacked"] = True
        attacker["has_acted"] = True
        next_state[attacker_side]["played_card"] = deepcopy(attacker)
    target = _find_card(next_state, payload.get("target_instance_id"))
    if target:
        next_state[defender_side]["played_card"] = deepcopy(target)
    next_state["turn_phase"] = "COMBAT_PHASE"
    return next_state


def reduce_spell_resolved(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    next_state["last_clash"] = None
    next_state["phase"] = "choose"
    next_state["turn_phase"] = "MAIN_PHASE"
    next_state["result"] = {"outcome": "Spell", "winner": None, "damage": {"player": 0, "bot": 0}, "effective_attack": {"player": 0, "bot": 0}}
    return next_state


def reduce_clash_resolved(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    result = {
        "outcome": payload.get("outcome"),
        "winner": payload.get("winner"),
        "damage": deepcopy(payload.get("damage") or {"player": 0, "bot": 0}),
        "effective_attack": deepcopy(payload.get("effective_attack") or {"player": 0, "bot": 0}),
    }
    if payload.get("hero_damage") is not None:
        result["hero_damage"] = deepcopy(payload.get("hero_damage") or {"player": 0, "bot": 0})
    next_state["result"] = result
    next_state["last_clash"] = {
        "player_card": deepcopy(payload.get("player_card")),
        "bot_card": deepcopy(payload.get("bot_card")),
        "outcome": payload.get("outcome"),
        "effective_attack": deepcopy(result["effective_attack"]),
    }
    next_state["phase"] = "result"
    next_state["turn_phase"] = "END_PHASE"
    return next_state


def reduce_turn_ended(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    next_state["turn_phase"] = "END_PHASE"
    return next_state


def reduce_played_cards_cleared(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    next_state["player"]["played_card"] = None
    next_state["bot"]["played_card"] = None
    return next_state


def reduce_units_readied(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    side_name = _side_name(event)
    if side_name:
        for card in _side_slots(next_state[side_name]):
            if isinstance(card, dict):
                card["exhausted"] = False
                card["has_attacked"] = False
                card["has_acted"] = False
        _sync_side_field(next_state[side_name])
    return next_state


def reduce_energy_refreshed(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    energy = int(payload.get("energy", 0) or 0)
    for side_name in ("player", "bot"):
        next_state[side_name]["max_energy"] = energy
        next_state[side_name]["energy"] = energy
    return next_state


def reduce_turn_started(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    next_state["turn"] = int(payload.get("turn", next_state.get("turn", 0)) or 0)
    next_state["phase"] = "choose"
    next_state["turn_phase"] = "MAIN_PHASE"
    next_state["result"] = None
    next_state["last_clash"] = None
    return next_state


def reduce_match_finished(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    winner = payload.get("winner")
    next_state["winner"] = winner
    next_state["is_finished"] = True
    next_state["phase"] = "finished"
    next_state["turn_phase"] = "END_PHASE"
    result = deepcopy(next_state.get("result") or {})
    if result:
        result["winner"] = winner if winner in {"player", "bot"} else None
        next_state["result"] = result
    return next_state


def reduce_card_evolved(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    next_state = _copy_state(state)
    payload = _payload(event)
    side_name = _side_name(event)
    if not side_name:
        return next_state
    side = next_state[side_name]
    consumed_ids = set(payload.get("consumed_instance_ids") or [])
    consumed = []
    remaining = []
    for card in side.get("hand", []):
        if card.get("instance_id") in consumed_ids:
            consumed.append(card)
        else:
            remaining.append(card)
    side["hand"] = remaining
    side.setdefault("discard", []).extend(deepcopy(consumed))
    evolved = deepcopy(payload.get("evolved_card") or {})
    if evolved:
        side["hand"].insert(0, evolved)
    return next_state


def reduce_noop(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    return _copy_state(state)


def apply_event_in_place(state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    """Apply reducer semantics directly to the authoritative runtime state."""
    event_type = str(event.get("event_type") or event.get("type") or "")
    payload = _payload(event)

    if event_type == "RESOURCE_CONSUMED":
        side_name = _side_name(event)
        if side_name:
            resource = str(payload.get("resource") or "mana")
            amount = max(0, int(payload.get("amount", payload.get("mana", 1)) or 0))
            if resource in {"mana", "energy"}:
                side = state[side_name]
                side["energy"] = max(0, int(side.get("energy", 0) or 0) - amount)
        return state

    if event_type == "STAT_MODIFIER_APPLIED":
        cards = _matching_cards(state, event.get("target_id") or payload.get("instance_id"))
        stat = str(payload.get("stat") or "").lower()
        amount = int(payload.get("amount", 0) or 0)
        for card in cards:
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
        return state

    if event_type == "SHIELD_GRANTED":
        card = _find_card(state, event.get("target_id") or payload.get("instance_id"))
        if card:
            amount = max(0, int(payload.get("guard_bonus", payload.get("amount", 0)) or 0))
            status_name = str(payload.get("status") or "aegis_sentinel_shield")
            if status_name not in _statuses(card):
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
        return state

    if event_type == "UNIT_EXHAUSTED":
        card = _find_card(state, event.get("target_id") or payload.get("target_instance_id"))
        if card:
            card["exhausted"] = True
            card["has_acted"] = True
            _statuses(card)["shadow_reaper_exhausted"] = {
                "turns": max(1, int(payload.get("duration_turns", 1) or 1)),
                "source_card_id": event.get("source_card_id"),
                "expires_on": "TURN_STARTED",
                "lifecycle": "next_turn_started",
            }
        return state

    if event_type == "SHIELD_BROKEN":
        card = _find_card(state, event.get("target_id") or payload.get("instance_id"))
        if not card:
            side_name = _side_name(event)
            if side_name:
                _side_statuses(state[side_name]).pop(str(payload.get("status") or "shield"), None)
            return state
        status_name = str(payload.get("status") or "aegis_sentinel_shield")
        status = _statuses(card).pop(status_name, None) or {}
        amount = max(0, int(payload.get("guard_bonus", status.get("guard", 0)) or 0))
        card["temporary_guard_bonus"] = max(0, int(card.get("temporary_guard_bonus", 0) or 0) - amount)
        card["max_guard"] = max(int(card.get("guard", 0) or 0), int(card.get("max_guard", card.get("guard", 0)) or 0) - amount)
        card["current_guard"] = max(0, int(card.get("current_guard", card.get("guard", 0)) or 0) - amount)
        card.pop("shield_expires_on", None)
        return state

    if event_type == "STATUS_EXPIRED":
        card = _find_card(state, event.get("target_id") or payload.get("instance_id"))
        if card:
            status_name = str(payload.get("status") or "")
            if status_name:
                _statuses(card).pop(status_name, None)
            if status_name == "shadow_reaper_exhausted":
                card["exhausted"] = False
        return state

    if event_type == "CARDS_DRAWN":
        side_name = _side_name(event)
        if side_name:
            side = state[side_name]
            amount = max(0, int(payload.get("amount", payload.get("drawn", 0)) or 0))
            explicit_cards = [deepcopy(card) for card in payload.get("cards", []) if isinstance(card, dict)]
            wanted_instances = [str(instance_id) for instance_id in payload.get("instance_ids", []) if instance_id]
            wanted_ids = [str(card_id) for card_id in payload.get("card_ids", []) if card_id]
            if explicit_cards:
                wanted_instances = [str(card.get("instance_id")) for card in explicit_cards if card.get("instance_id")]
            drawn = []
            remaining = []
            for card in list(side.get("deck") or []):
                if amount <= len(drawn):
                    remaining.append(card)
                    continue
                if wanted_instances and str(card.get("instance_id")) not in wanted_instances:
                    remaining.append(card)
                    continue
                if not wanted_instances and wanted_ids and str(card.get("id")) not in wanted_ids:
                    remaining.append(card)
                    continue
                drawn.append(card)
            if explicit_cards and not drawn:
                drawn = explicit_cards[:amount]
            side["deck"] = remaining
            side.setdefault("hand", []).extend(drawn)
        return state

    if event_type == "STATUS_APPLIED":
        status_name = str(payload.get("status") or "").strip().lower()
        if not status_name:
            return state
        turns = max(1, int(payload.get("turns", payload.get("duration_turns", 1)) or 1))
        potency = max(1, int(payload.get("potency", payload.get("amount", 1)) or 1))
        target_card = _find_card(state, event.get("target_id") or payload.get("instance_id") or payload.get("target_instance_id"))
        if target_card:
            current = _statuses(target_card).get(status_name, {})
            _statuses(target_card)[status_name] = {
                **current,
                "turns": max(turns, int(current.get("turns", 0) or 0)),
                "potency": max(potency, int(current.get("potency", 0) or 0)),
                "source_card_id": event.get("source_card_id"),
            }
            return state
        side_name = _side_name(event)
        if side_name:
            current = _side_statuses(state[side_name]).get(status_name, {})
            _side_statuses(state[side_name])[status_name] = {
                **current,
                "turns": max(turns, int(current.get("turns", 0) or 0)),
                "potency": max(potency, int(current.get("potency", 0) or 0)),
            }
        return state

    if event_type == "STATUS_CLEANSED":
        target_card = _find_card(state, event.get("target_id") or payload.get("instance_id"))
        if target_card:
            _statuses(target_card).clear()
            return state
        side_name = _side_name(event)
        if side_name:
            _side_statuses(state[side_name]).clear()
        return state

    if event_type == "DAMAGE_RESOLVED":
        guard_damage = payload.get("guard_damage") or {}
        hero_damage = payload.get("hero_damage") or {}
        for side_name in ("player", "bot"):
            amount = None
            if payload.get("side") == side_name and "amount" in payload:
                amount = max(0, int(payload.get("amount", 0) or 0))
            elif side_name in payload and not payload.get("persistent_field"):
                amount = max(0, int(payload.get(side_name, 0) or 0))
            elif payload.get("persistent_field") and side_name in hero_damage:
                amount = max(0, int(hero_damage.get(side_name, 0) or 0))
            if amount is not None and amount > 0:
                side = state[side_name]
                shield = _side_statuses(side).get("shield")
                if shield:
                    absorbed = min(amount, max(0, int(shield.get("potency", shield.get("amount", 0)) or 0)))
                    amount -= absorbed
                    shield["potency"] = max(0, int(shield.get("potency", 0) or 0) - absorbed)
                    if shield["potency"] <= 0:
                        _side_statuses(side).pop("shield", None)
                side["hp"] = max(0, int(side.get("hp", 0) or 0) - amount)
                side["wounded"] = amount > 0
            card_damage = int((guard_damage or {}).get(side_name, 0) or 0)
            instance_id = payload.get(f"{side_name}_instance_id")
            cards = _matching_cards(state, instance_id)
            if cards and card_damage:
                for card in cards:
                    card["current_guard"] = int(card.get("current_guard", card.get("guard", 0)) or 0) - card_damage
        return state

    if event_type == "HEALTH_RECOVERED":
        side_name = _side_name(event)
        if side_name:
            side = state[side_name]
            amount = max(0, int(payload.get("amount", 0) or 0))
            side["hp"] = min(int(side.get("max_hp", side.get("hp", 0)) or 0), int(side.get("hp", 0) or 0) + amount)
        return state

    if event_type == "SHIELD_APPLIED":
        side_name = _side_name(event)
        if side_name:
            amount = max(1, int(payload.get("amount", payload.get("potency", 1)) or 1))
            turns = max(1, int(payload.get("turns", 1) or 1))
            _side_statuses(state[side_name])["shield"] = {"turns": turns, "potency": amount}
        return state

    if event_type == "CARD_DISCARDED":
        side_name = _side_name(event)
        card = payload.get("card")
        if side_name and isinstance(card, dict):
            state[side_name].setdefault("discard", []).append(deepcopy(card))
        return state

    if event_type == "UNIT_DESTROYED":
        side_name = _side_name(event)
        target_id = event.get("target_id") or payload.get("instance_id")
        if side_name and target_id:
            side = state[side_name]
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
        return state

    if event_type == "TURN_STATUS_TICKED":
        side_name = _side_name(event)
        if side_name:
            side = state[side_name]
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
        return state

    return state


REDUCER_REGISTRY: Dict[str, Reducer] = {
    "ATTACK_DECLARED": reduce_attack_declared,
    "CARD_DISCARDED": reduce_card_discarded,
    "CARD_EVOLVED": reduce_card_evolved,
    "CARD_PLAYED": reduce_card_played,
    "CARDS_DRAWN": reduce_cards_drawn,
    "CLASH_RESOLVED": reduce_clash_resolved,
    "DAMAGE_RESOLVED": reduce_damage_resolved,
    "ENERGY_REFRESHED": reduce_energy_refreshed,
    "HEALTH_RECOVERED": reduce_health_recovered,
    "MATCH_FINISHED": reduce_match_finished,
    "MONSTER_SUMMONED": reduce_monster_summoned,
    "PLAYED_CARDS_CLEARED": reduce_played_cards_cleared,
    "RESOURCE_CONSUMED": reduce_resource_consumed,
    "SHIELD_APPLIED": reduce_shield_applied,
    "SPELL_RESOLVED": reduce_spell_resolved,
    "STAT_MODIFIER_APPLIED": reduce_stat_modifier_applied,
    "STATUS_APPLIED": reduce_status_applied,
    "STATUS_CLEANSED": reduce_status_cleansed,
    "SHIELD_GRANTED": reduce_shield_granted,
    "TRAP_ARMED": reduce_trap_armed,
    "TRAP_TRIGGERED": reduce_trap_triggered,
    "TURN_STATUS_TICKED": reduce_turn_status_ticked,
    "TURN_ENDED": reduce_turn_ended,
    "TURN_STARTED": reduce_turn_started,
    "UNITS_READIED": reduce_units_readied,
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
