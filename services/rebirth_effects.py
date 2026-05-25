"""Canonical deterministic effect bus for Rebirth gameplay.

This module owns triggered passive resolution. It deliberately does not know
about Flask, sockets or browser rendering; callers provide an authoritative
match dict and receive serializable GameEvents through ``append_event``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from services.rebirth_contracts import RebirthError
from services.rebirth_domain import (
    MAX_EFFECT_CHAIN_DEPTH,
    MAX_INTERRUPT_DEPTH,
    MAX_PHASE_ITERATIONS,
    canonical_json,
    canonical_state_hash,
)
from services.rebirth_events import append_event, new_effect_chain_id
from services.rebirth_profiler import current_profiler
from services.rebirth_reducers import apply_event_in_place, reduce_event
from services.rebirth_state import field_slots


LEGENDARY_INFERNUS = "infernus_core"
LEGENDARY_AEGIS = "aegis_sentinel"
LEGENDARY_SHADOW = "shadow_reaper"

PHASE_ORDER = (
    "PRE_RESOLUTION",
    "TRIGGER_COLLECTION",
    "PRIORITY_SORT",
    "REDUCER_PHASE",
    "POST_RESOLUTION",
    "CLEANUP_PHASE",
)

PRIORITY_REPLACEMENT = 1
PRIORITY_INTERRUPT = 2
PRIORITY_REACTIVE_SPELL = 3
PRIORITY_ACTIVE_SPELL = 4
PRIORITY_PASSIVE_TRIGGER = 5
PRIORITY_DELAYED_EXPIRATION = 6

PRIORITY_MODEL = {
    "replacement": PRIORITY_REPLACEMENT,
    "interrupt": PRIORITY_INTERRUPT,
    "trap": PRIORITY_INTERRUPT,
    "reactive_spell": PRIORITY_REACTIVE_SPELL,
    "active_spell": PRIORITY_ACTIVE_SPELL,
    "passive": PRIORITY_PASSIVE_TRIGGER,
    "delayed": PRIORITY_DELAYED_EXPIRATION,
    "expiration": PRIORITY_DELAYED_EXPIRATION,
}

RUNTIME_CACHE_LIMIT = 16


def apply_reducers_inline(match: Dict[str, Any]) -> bool:
    return bool(match.get("_apply_reducers_inline", True))


def _pending_hash_ids(match: Dict[str, Any]) -> set[int]:
    return set(int(event_id) for event_id in match.setdefault("_pending_hash_event_ids", []))


def mark_canonical_hash_dirty(match: Dict[str, Any], event_ids: Iterable[int]) -> None:
    ids = _pending_hash_ids(match)
    ids.update(int(event_id) for event_id in event_ids if event_id)
    match["_pending_hash_event_ids"] = sorted(ids)
    invalidate_canonical_state_hash(match, origin="event_flush")


def invalidate_canonical_state_hash(match: Dict[str, Any], *, origin: Optional[str] = None) -> None:
    match["_canonical_hash_dirty"] = True
    match["_last_canonical_state_hash"] = None
    if origin and (match.get("_debug_mutation_tracking") or match.get("_parity_tracking_enabled")):
        match["_mutation_dirty"] = True
        match.setdefault("_mutation_origins", []).append(str(origin))


def finalize_canonical_state_hash(match: Dict[str, Any], event_ids: Optional[Iterable[int]] = None) -> Optional[str]:
    ids = _pending_hash_ids(match)
    if event_ids is not None:
        ids.update(int(event_id) for event_id in event_ids if event_id)
    if not ids and not match.get("_canonical_hash_dirty"):
        return match.get("_last_canonical_state_hash")
    final_hash = canonical_state_hash(match)
    match["_last_canonical_state_hash"] = final_hash
    for event in match.get("events", []):
        if int(event.get("event_id", 0) or 0) in ids:
            event["canonical_state_hash"] = final_hash
    match["_pending_hash_event_ids"] = []
    match["_canonical_hash_dirty"] = False
    return final_hash


def purge_effect_runtime_caches(match: Dict[str, Any], *, keep_last: int = RUNTIME_CACHE_LIMIT) -> Dict[str, Any]:
    for cache_key in ("_effect_dispatch_keys", "_effect_activation_keys"):
        cache = match.get(cache_key)
        if not isinstance(cache, dict):
            continue
        if keep_last <= 0:
            match[cache_key] = {}
            continue
        if len(cache) <= keep_last:
            continue
        keep = set(sorted(cache)[-keep_last:])
        match[cache_key] = {key: cache[key] for key in sorted(cache) if key in keep}
    return match


def _frozen_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return deepcopy(payload or {})


def _card_key(card: Optional[Dict[str, Any]]) -> str:
    if not card:
        return ""
    return str(card.get("instance_id") or card.get("id") or "")


def _status_bucket(card: Dict[str, Any]) -> Dict[str, Any]:
    statuses = card.get("statuses") or {}
    return statuses if isinstance(statuses, dict) else {}


def _effective_attack(card: Dict[str, Any]) -> int:
    return max(0, int(card.get("attack", card.get("power", 0)) or 0) + int(card.get("attack_adjustment", 0) or 0))


def _current_guard(card: Dict[str, Any]) -> int:
    return int(card.get("current_guard", card.get("guard", 0)) or 0)


def _owner_side(card: Dict[str, Any], fallback: str) -> str:
    owner = str(card.get("owner_side") or card.get("owner") or fallback or "")
    return owner if owner in {"player", "bot"} else fallback


def _opponent(side_name: str) -> str:
    return "bot" if side_name == "player" else "player"


def _field_cards(match: Dict[str, Any], side_name: str) -> List[Dict[str, Any]]:
    return [card for card in field_slots(match[side_name]) if card]


def _is_legendary(card: Optional[Dict[str, Any]], ability_key: str) -> bool:
    if not card:
        return False
    return str(card.get("ability_key") or "") == ability_key


def _card_event_payload(card: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    payload = {
        "card_id": card.get("id"),
        "instance_id": card.get("instance_id"),
        "field_slot": card.get("field_slot"),
    }
    payload.update(extra)
    return payload


class EffectBus:
    """Queues GameEvents, applies pure reducers, then stores causal traces."""

    def __init__(
        self,
        match: Dict[str, Any],
        *,
        effect_chain_id: Optional[str] = None,
        parent_event_id: Optional[int] = None,
        root_event_id: Optional[int] = None,
    ):
        self.match = match
        self.effect_chain_id = effect_chain_id or new_effect_chain_id(match, "effect")
        self.parent_event_id = parent_event_id
        self.root_event_id = root_event_id
        self._queue: List[Dict[str, Any]] = []
        self._dispatch_keys = set(match.setdefault("_effect_dispatch_keys", {}).setdefault(self.effect_chain_id, []))
        self._phase_iterations = 0

    def dispatch(
        self,
        event_type: str,
        *,
        actor: str = "system",
        source_card_id: Optional[str] = None,
        target_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        order: int = 0,
        parent_event_id: Optional[int] = None,
        root_event_id: Optional[int] = None,
        chain_from_previous: bool = False,
        apply_reducer: bool = True,
        priority_level: int = PRIORITY_PASSIVE_TRIGGER,
        trigger_timestamp: Optional[int] = None,
        slot_index: int = 0,
        stable_entity_id: Optional[str] = None,
        resolution_phase: str = "REDUCER_PHASE",
    ) -> bool:
        depth = int(self.match.get("_event_dispatch_depth", 0) or 0)
        if depth >= MAX_EFFECT_CHAIN_DEPTH:
            raise RebirthError("Profundidade máxima da cadeia de efeitos excedida.", "effect_chain_depth_exceeded")
        priority_level = int(priority_level)
        if priority_level == PRIORITY_INTERRUPT:
            interrupt_depth = int(self.match.get("_interrupt_depth", 0) or 0)
            if interrupt_depth >= MAX_INTERRUPT_DEPTH:
                raise RebirthError("Profundidade máxima de interrupt excedida.", "interrupt_depth_exceeded")
        payload = _frozen_payload(payload)
        phase = str(resolution_phase or "REDUCER_PHASE")
        if phase not in PHASE_ORDER:
            raise RebirthError(f"Fase de resolução inválida: {phase}", "invalid_resolution_phase")
        dispatch_key = canonical_json(
            {
                "event_type": str(event_type),
                "source_card_id": source_card_id,
                "target_id": target_id,
                "owner_id": owner_id if owner_id is not None else actor,
                "payload": payload,
                "parent_event_id": parent_event_id if parent_event_id is not None else self.parent_event_id,
                "priority_level": priority_level,
                "resolution_phase": phase,
            }
        )
        if dispatch_key in self._dispatch_keys:
            return False
        self._dispatch_keys.add(dispatch_key)
        self.match.setdefault("_effect_dispatch_keys", {})[self.effect_chain_id] = sorted(self._dispatch_keys)
        self._queue.append(
            {
                "order": int(order),
                "event_type": str(event_type),
                "actor": str(actor),
                "source_card_id": source_card_id,
                "target_id": target_id,
                "owner_id": owner_id if owner_id is not None else actor,
                "payload": payload,
                "message": str(message) if message else None,
                "parent_event_id": parent_event_id,
                "root_event_id": root_event_id,
                "chain_from_previous": bool(chain_from_previous),
                "apply_reducer": bool(apply_reducer),
                "priority_level": priority_level,
                "trigger_timestamp": int(trigger_timestamp if trigger_timestamp is not None else order),
                "slot_index": int(slot_index),
                "stable_entity_id": str(stable_entity_id or target_id or source_card_id or ""),
                "resolution_phase": phase,
            }
        )
        return True

    def flush(self) -> List[Dict[str, Any]]:
        self._phase_iterations += 1
        if self._phase_iterations > MAX_PHASE_ITERATIONS:
            raise RebirthError("Limite de iterações de fase excedido.", "phase_iteration_limit_exceeded")
        profiler = current_profiler()
        ordered = sorted(
            self._queue,
            key=lambda item: (
                int(item.get("priority_level", PRIORITY_PASSIVE_TRIGGER)),
                int(item.get("trigger_timestamp", item["order"])),
                int(item.get("slot_index", 0)),
                str(item.get("stable_entity_id") or ""),
                item["event_type"],
                item.get("source_card_id") or "",
                item.get("target_id") or "",
                canonical_json(item.get("payload") or {}),
            ),
        )
        self._queue = []
        self.match["_event_dispatch_depth"] = int(self.match.get("_event_dispatch_depth", 0) or 0) + 1
        if profiler:
            profiler.observe_effect_chain_depth(int(self.match.get("_event_dispatch_depth", 0) or 0))
        has_interrupt = any(int(item.get("priority_level", 0) or 0) == PRIORITY_INTERRUPT for item in ordered)
        if has_interrupt:
            self.match["_interrupt_depth"] = int(self.match.get("_interrupt_depth", 0) or 0) + 1
        try:
            emitted = []
            previous_event_id = None
            flush_timer = profiler.timer("phase_cost", detail="EffectBus.flush") if profiler else None
            if flush_timer:
                flush_timer.__enter__()
            try:
                for item in ordered:
                    parent_event_id = item.get("parent_event_id")
                    if item.get("chain_from_previous") and previous_event_id is not None:
                        parent_event_id = previous_event_id
                    if parent_event_id is None:
                        parent_event_id = self.parent_event_id
                    event = append_event(
                        self.match,
                        item["event_type"],
                        actor=item["actor"],
                        payload=item["payload"],
                        message=item.get("message"),
                        source_card_id=item.get("source_card_id"),
                        target_id=item.get("target_id"),
                        owner_id=item.get("owner_id"),
                        effect_chain_id=self.effect_chain_id,
                        parent_event_id=parent_event_id,
                        root_event_id=item.get("root_event_id") or self.root_event_id,
                        resolution_phase=item.get("resolution_phase"),
                        priority_level=item.get("priority_level"),
                    )
                    if item.get("apply_reducer"):
                        if profiler:
                            with profiler.timer("phase_cost", detail=item.get("resolution_phase") or "REDUCER_PHASE"):
                                with profiler.timer("reducer_cost", detail=item["event_type"]):
                                    if apply_reducers_inline(self.match):
                                        reduced = reduce_event(self.match, event)
                                        self.match.clear()
                                        self.match.update(reduced)
                                    else:
                                        invalidate_canonical_state_hash(self.match, origin=f"in_place:{item['event_type']}")
                                        apply_event_in_place(self.match, event)
                        elif apply_reducers_inline(self.match):
                            reduced = reduce_event(self.match, event)
                            self.match.clear()
                            self.match.update(reduced)
                        else:
                            invalidate_canonical_state_hash(self.match, origin=f"in_place:{item['event_type']}")
                            apply_event_in_place(self.match, event)
                    emitted.append(self.match["events"][-1])
                    previous_event_id = emitted[-1]["event_id"]
            finally:
                if flush_timer:
                    flush_timer.__exit__(None, None, None)
            emitted_ids = {int(event["event_id"]) for event in emitted}
            if emitted_ids:
                mark_canonical_hash_dirty(self.match, emitted_ids)
                if int(self.match.get("_command_dispatch_depth", 0) or 0) <= 0:
                    finalize_canonical_state_hash(self.match)
            return emitted
        finally:
            self.match["_event_dispatch_depth"] = max(0, int(self.match.get("_event_dispatch_depth", 1) or 1) - 1)
            if has_interrupt:
                self.match["_interrupt_depth"] = max(0, int(self.match.get("_interrupt_depth", 1) or 1) - 1)
            if int(self.match.get("_command_dispatch_depth", 0) or 0) <= 0:
                purge_effect_runtime_caches(self.match)


def _message_list(events: Iterable[Dict[str, Any]]) -> List[str]:
    return [event["message"] for event in events if event.get("message")]


def status_label(status_name: str) -> str:
    labels = {
        "burn": "queimadura",
        "decay": "deterioração",
        "shield": "escudo",
        "weaken": "fraqueza",
        "freeze": "congelamento",
    }
    return labels.get(str(status_name or ""), str(status_name or "efeito"))


def _effect_side(owner_side: str, effect: Dict[str, Any]) -> str:
    target = str(effect.get("target") or effect.get("side") or "self").strip().lower()
    if target in {"self", "owner", "ally"}:
        return owner_side
    if target in {"opponent", "enemy", "attacker"}:
        return _opponent(owner_side)
    if target in {"player", "bot"}:
        return target
    return owner_side


def _status_tick_message(side: Dict[str, Any], statuses: Dict[str, Any]) -> Optional[str]:
    messages: List[str] = []
    burn = statuses.get("burn")
    if burn:
        amount = max(1, int(burn.get("potency", 1) or 1))
        messages.append(f"{side['name']} sofre {amount} de dano de queimadura.")
    decay = statuses.get("decay")
    if decay:
        amount = max(1, int(decay.get("potency", 1) or 1))
        messages.append(f"{side['name']} sofre {amount} de dano de deterioração.")
    for status_name, status in sorted(statuses.items()):
        turns = int(status.get("turns", 1) or 1) - 1
        if turns <= 0:
            messages.append(f"{status_label(status_name).capitalize()} de {side['name']} se dissipa.")
    return " ".join(messages) if messages else None


def _dispatch_effect(
    match: Dict[str, Any],
    bus: EffectBus,
    owner_side: str,
    effect: Dict[str, Any],
    *,
    order: int,
    priority_level: int,
    parent_event_id: Optional[int],
    root_event_id: Optional[int],
    source_card: Optional[Dict[str, Any]],
) -> None:
    effect_type = str(effect.get("type") or effect.get("effect_type") or "").strip().lower()
    side_name = _effect_side(owner_side, effect)
    side = match.get(side_name) if side_name in {"player", "bot"} else None
    if side is None:
        return
    source_card_id = (source_card or {}).get("id")
    stable_entity_id = (source_card or {}).get("instance_id") or side_name

    if effect_type == "draw":
        amount = max(1, int(effect.get("amount", 1) or 1))
        cards = list((side.get("deck") or [])[:amount])
        if not cards:
            return
        suffix = "carta" if len(cards) == 1 else "cartas"
        bus.dispatch(
            "CARDS_DRAWN",
            actor=side_name,
            source_card_id=source_card_id,
            target_id=side_name,
            owner_id=side_name,
            payload={"side": side_name, "amount": len(cards), "card_ids": [card.get("id") for card in cards]},
            message=f"{side['name']} compra {len(cards)} {suffix}.",
            order=order,
            priority_level=priority_level,
            trigger_timestamp=order,
            stable_entity_id=stable_entity_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
        )
        return

    if effect_type == "cleanse":
        statuses = side.get("statuses") or {}
        if not statuses:
            return
        removed = sorted(statuses)
        bus.dispatch(
            "STATUS_CLEANSED",
            actor=side_name,
            source_card_id=source_card_id,
            target_id=side_name,
            owner_id=side_name,
            payload={"side": side_name, "removed": removed},
            message=f"{side['name']} remove {', '.join(status_label(item) for item in removed)}.",
            order=order,
            priority_level=priority_level,
            trigger_timestamp=order,
            stable_entity_id=stable_entity_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
        )
        return

    if effect_type == "destroy_shield":
        target_id = side_name
        status_name = "shield"
        message = f"O escudo de {side['name']} foi destruído."
        payload = {"side": side_name, "status": status_name}
        if "shield" not in (side.get("statuses") or {}):
            shielded_units = sorted(
                (
                    card
                    for card in _field_cards(match, side_name)
                    if "aegis_sentinel_shield" in _status_bucket(card)
                ),
                key=lambda card: (int(card.get("field_slot", 0) or 0), _card_key(card)),
            )
            if not shielded_units:
                return
            protected = shielded_units[0]
            target_id = protected.get("instance_id")
            status_name = "aegis_sentinel_shield"
            status = _status_bucket(protected).get(status_name) or {}
            payload = _card_event_payload(
                protected,
                side=side_name,
                status=status_name,
                guard_bonus=max(0, int(status.get("guard", 0) or 0)),
                armor_break=True,
            )
            message = f"{protected['name']} perde sua armadura temporária."
        bus.dispatch(
            "SHIELD_BROKEN",
            actor=side_name,
            source_card_id=source_card_id,
            target_id=target_id,
            owner_id=side_name,
            payload=payload,
            message=message,
            order=order,
            priority_level=priority_level,
            trigger_timestamp=order,
            stable_entity_id=stable_entity_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
        )
        return

    if effect_type == "status":
        status_name = str(effect.get("status") or "").strip().lower()
        if not status_name:
            return
        turns = max(1, int(effect.get("turns", 1) or 1))
        potency = max(1, int(effect.get("potency", 1) or 1))
        bus.dispatch(
            "STATUS_APPLIED",
            actor=side_name,
            source_card_id=source_card_id,
            target_id=side_name,
            owner_id=side_name,
            payload={"side": side_name, "status": status_name, "turns": turns, "potency": potency},
            message=f"{side['name']} é afetado por {status_label(status_name)}.",
            order=order,
            priority_level=priority_level,
            trigger_timestamp=order,
            stable_entity_id=stable_entity_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
        )
        return

    if effect_type == "damage":
        amount = max(0, int(effect.get("amount", 0) or 0))
        if amount <= 0:
            return
        bus.dispatch(
            "DAMAGE_RESOLVED",
            actor=owner_side,
            source_card_id=source_card_id,
            target_id=side_name,
            owner_id=owner_side,
            payload={"side": side_name, "amount": amount},
            message=f"{side['name']} sofre {amount} de dano da pilha.",
            order=order,
            priority_level=priority_level,
            trigger_timestamp=order,
            stable_entity_id=stable_entity_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
        )
        return

    if effect_type == "heal":
        amount = max(0, int(effect.get("amount", 0) or 0))
        if amount <= 0:
            return
        bus.dispatch(
            "HEALTH_RECOVERED",
            actor=side_name,
            source_card_id=source_card_id,
            target_id=side_name,
            owner_id=side_name,
            payload={"side": side_name, "amount": amount},
            message=f"{side['name']} recupera {amount} PV.",
            order=order,
            priority_level=priority_level,
            trigger_timestamp=order,
            stable_entity_id=stable_entity_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
        )
        return

    if effect_type == "shield":
        amount = max(1, int(effect.get("amount", 1) or 1))
        turns = max(1, int(effect.get("turns", 1) or 1))
        bus.dispatch(
            "SHIELD_APPLIED",
            actor=side_name,
            source_card_id=source_card_id,
            target_id=side_name,
            owner_id=side_name,
            payload={"side": side_name, "amount": amount, "turns": turns},
            message=f"{side['name']} recebe um escudo de {amount} pontos.",
            order=order,
            priority_level=priority_level,
            trigger_timestamp=order,
            stable_entity_id=stable_entity_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
        )
        return

    if effect_type == "weaken":
        amount = max(1, int(effect.get("amount", 1) or 1))
        turns = max(1, int(effect.get("turns", 1) or 1))
        bus.dispatch(
            "STATUS_APPLIED",
            actor=side_name,
            source_card_id=source_card_id,
            target_id=side_name,
            owner_id=side_name,
            payload={"side": side_name, "status": "weaken", "turns": turns, "potency": amount},
            message=f"{side['name']} sofre fraqueza de {amount}.",
            order=order,
            priority_level=priority_level,
            trigger_timestamp=order,
            stable_entity_id=stable_entity_id,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
        )


def resolve_effect_sequence(
    match: Dict[str, Any],
    owner_side: str,
    effects: Iterable[Dict[str, Any]],
    *,
    effect_chain_id: Optional[str] = None,
    parent_event_id: Optional[int] = None,
    root_event_id: Optional[int] = None,
    priority_level: int = PRIORITY_ACTIVE_SPELL,
    source_card: Optional[Dict[str, Any]] = None,
) -> List[str]:
    bus = EffectBus(match, effect_chain_id=effect_chain_id, parent_event_id=parent_event_id, root_event_id=root_event_id)
    for index, effect in enumerate(list(effects or [])):
        _dispatch_effect(
            match,
            bus,
            owner_side,
            dict(effect or {}),
            order=100 + index,
            priority_level=priority_level,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
            source_card=source_card,
        )
    return _message_list(bus.flush())


def resolve_status_ticks(
    match: Dict[str, Any],
    *,
    effect_chain_id: Optional[str] = None,
    parent_event_id: Optional[int] = None,
    root_event_id: Optional[int] = None,
) -> List[str]:
    bus = EffectBus(match, effect_chain_id=effect_chain_id, parent_event_id=parent_event_id, root_event_id=root_event_id)
    for index, side_name in enumerate(("player", "bot")):
        side = match[side_name]
        statuses = side.get("statuses") or {}
        message = _status_tick_message(side, statuses)
        if not message:
            continue
        expired = sorted(status_name for status_name, status in statuses.items() if int(status.get("turns", 1) or 1) <= 1)
        bus.dispatch(
            "TURN_STATUS_TICKED",
            actor="system",
            target_id=side_name,
            owner_id=side_name,
            payload={"side": side_name, "expired": expired, "statuses": sorted(statuses)},
            message=message,
            order=400 + index,
            priority_level=PRIORITY_DELAYED_EXPIRATION,
            trigger_timestamp=400 + index,
            stable_entity_id=side_name,
            parent_event_id=parent_event_id,
            root_event_id=root_event_id,
            resolution_phase="CLEANUP_PHASE",
        )
    return _message_list(bus.flush())


def cleanup_defeated_units(
    match: Dict[str, Any],
    *,
    effect_chain_id: Optional[str] = None,
    parent_event_id: Optional[int] = None,
    root_event_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    bus = EffectBus(match, effect_chain_id=effect_chain_id, parent_event_id=parent_event_id, root_event_id=root_event_id)
    defeated: List[Dict[str, Any]] = []
    order = 600
    for side_name in ("player", "bot"):
        for card in _field_cards(match, side_name):
            if _current_guard(card) > 0:
                continue
            snapshot = deepcopy(card)
            defeated.append(snapshot)
            bus.dispatch(
                "UNIT_DESTROYED",
                actor="system",
                source_card_id=card.get("id"),
                target_id=card.get("instance_id"),
                owner_id=side_name,
                payload=_card_event_payload(card, side=side_name),
                message=f"{card['name']} foi destruído.",
                order=order,
                priority_level=PRIORITY_DELAYED_EXPIRATION,
                trigger_timestamp=order,
                slot_index=int(card.get("field_slot", 0) or 0),
                stable_entity_id=_card_key(card),
                parent_event_id=parent_event_id,
                root_event_id=root_event_id,
                resolution_phase="CLEANUP_PHASE",
            )
            order += 1
    bus.flush()
    return defeated


def _infernus_survived(match: Dict[str, Any], bus: EffectBus, context: Dict[str, Any]) -> None:
    attacker = context.get("attacker_card")
    side_name = context.get("attacker_side") or _owner_side(attacker or {}, "player")
    if not _is_legendary(attacker, LEGENDARY_INFERNUS):
        return
    if _current_guard(attacker) <= 0:
        return
    side = match[side_name]
    if int(side.get("energy", 0) or 0) < 1:
        return
    activation_key = f"infernus:{_card_key(attacker)}"
    if activation_key in set(match.setdefault("_effect_activation_keys", {}).setdefault(bus.effect_chain_id, [])):
        return
    match["_effect_activation_keys"][bus.effect_chain_id] = sorted(
        set(match["_effect_activation_keys"][bus.effect_chain_id]) | {activation_key}
    )

    common = _card_event_payload(attacker, mana=1, attack_bonus=2)
    bus.dispatch(
        "RESOURCE_CONSUMED",
        actor=side_name,
        source_card_id=attacker.get("id"),
        target_id=attacker.get("instance_id"),
        owner_id=side_name,
        payload={**common, "resource": "mana", "amount": 1},
        message=f"{attacker['name']} consome 1 mana para alimentar o núcleo.",
        order=10,
    )
    bus.dispatch(
        "STAT_MODIFIER_APPLIED",
        actor=side_name,
        source_card_id=attacker.get("id"),
        target_id=attacker.get("instance_id"),
        owner_id=side_name,
        payload={**common, "stat": "attack", "amount": 2, "duration": "permanent"},
        message=f"{attacker['name']} recebe +2 ATK permanente.",
        order=20,
        chain_from_previous=True,
    )
    bus.dispatch(
        "EFFECT_RESOLVED",
        actor=side_name,
        source_card_id=attacker.get("id"),
        target_id=attacker.get("instance_id"),
        owner_id=side_name,
        payload={**common, "trigger": "UNIT_SURVIVED_COMBAT", "effect": LEGENDARY_INFERNUS},
        message=f"{attacker['name']} resolveu Infernus Core.",
        order=30,
        chain_from_previous=True,
        apply_reducer=False,
    )


def _aegis_turn_ended(match: Dict[str, Any], bus: EffectBus) -> None:
    order = 100
    for side_name in ("player", "bot"):
        for card in _field_cards(match, side_name):
            if not _is_legendary(card, LEGENDARY_AEGIS):
                continue
            if bool(card.get("has_acted", card.get("has_attacked", False))):
                continue
            statuses = _status_bucket(card)
            if "aegis_sentinel_shield" in statuses:
                continue

            payload = _card_event_payload(card, guard_bonus=2, expires_on="DAMAGE_RESOLVED", status="aegis_sentinel_shield")
            bus.dispatch(
                "SHIELD_GRANTED",
                actor=side_name,
                source_card_id=card.get("id"),
                target_id=card.get("instance_id"),
                owner_id=side_name,
                payload=payload,
                message=f"{card['name']} ergue +2 GRD temporário.",
                order=order,
            )
            bus.dispatch(
                "STATUS_APPLIED",
                actor=side_name,
                source_card_id=card.get("id"),
                target_id=card.get("instance_id"),
                owner_id=side_name,
                payload={**payload, "status": "aegis_sentinel_shield"},
                message=f"{card['name']} recebeu status de escudo temporário.",
                order=order + 1,
                chain_from_previous=True,
                apply_reducer=False,
            )
            bus.dispatch(
                "EFFECT_RESOLVED",
                actor=side_name,
                source_card_id=card.get("id"),
                target_id=card.get("instance_id"),
                owner_id=side_name,
                payload={**payload, "trigger": "TURN_ENDED", "effect": LEGENDARY_AEGIS},
                message=f"{card['name']} resolveu Aegis Sentinel.",
                order=order + 2,
                chain_from_previous=True,
                apply_reducer=False,
            )
            order += 10


def _select_shadow_target(match: Dict[str, Any], side_name: str) -> Optional[Dict[str, Any]]:
    candidates = [
        card
        for card in _field_cards(match, _opponent(side_name))
        if _current_guard(card) > 0
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda card: (-_effective_attack(card), int(card.get("field_slot", 0) or 0), _card_key(card)))[0]


def _shadow_card_summoned(match: Dict[str, Any], bus: EffectBus, context: Dict[str, Any]) -> None:
    source = context.get("source_card")
    side_name = context.get("owner_side") or _owner_side(source or {}, "player")
    if not _is_legendary(source, LEGENDARY_SHADOW):
        return
    target = _select_shadow_target(match, side_name)
    if not target:
        return

    payload = {
        "source_card_id": source.get("id"),
        "source_instance_id": source.get("instance_id"),
        "target_card_id": target.get("id"),
        "target_instance_id": target.get("instance_id"),
        "target_slot_index": int(target.get("field_slot", 0) or 0),
        "target_attack": _effective_attack(target),
        "duration_turns": 1,
    }
    bus.dispatch(
        "TARGET_SELECTED",
        actor=side_name,
        source_card_id=source.get("id"),
        target_id=target.get("instance_id"),
        owner_id=side_name,
        payload=payload,
        message=f"{source['name']} seleciona {target['name']} como maior ameaça.",
        order=200,
    )
    bus.dispatch(
        "UNIT_EXHAUSTED",
        actor=side_name,
        source_card_id=source.get("id"),
        target_id=target.get("instance_id"),
        owner_id=side_name,
        payload=payload,
        message=f"{target['name']} fica exausto por 1 turno.",
        order=201,
        chain_from_previous=True,
    )
    bus.dispatch(
        "STATUS_APPLIED",
        actor=side_name,
        source_card_id=source.get("id"),
        target_id=target.get("instance_id"),
        owner_id=side_name,
        payload={**payload, "status": "shadow_reaper_exhausted"},
        message=f"{target['name']} recebeu status de exaustão.",
        order=202,
        chain_from_previous=True,
        apply_reducer=False,
    )
    bus.dispatch(
        "EFFECT_RESOLVED",
        actor=side_name,
        source_card_id=source.get("id"),
        target_id=target.get("instance_id"),
        owner_id=side_name,
        payload={**payload, "trigger": "CARD_SUMMONED", "effect": LEGENDARY_SHADOW},
        message=f"{source['name']} resolveu Shadow Reaper.",
        order=203,
        chain_from_previous=True,
        apply_reducer=False,
    )


def apply_legendary_passives(match: Dict[str, Any], trigger: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
    context = dict(context or {})
    bus = EffectBus(
        match,
        effect_chain_id=context.get("effect_chain_id"),
        parent_event_id=context.get("parent_event_id"),
        root_event_id=context.get("root_event_id"),
    )
    trigger = str(trigger or "")
    if trigger == "UNIT_SURVIVED_COMBAT":
        _infernus_survived(match, bus, context)
    elif trigger == "TURN_ENDED":
        _aegis_turn_ended(match, bus)
    elif trigger == "CARD_SUMMONED":
        _shadow_card_summoned(match, bus, context)
    return _message_list(bus.flush())


def _expire_aegis_shields(match: Dict[str, Any], bus: EffectBus) -> None:
    order = 300
    for side_name in ("player", "bot"):
        for card in _field_cards(match, side_name):
            status = _status_bucket(card).get("aegis_sentinel_shield")
            if not status:
                continue
            amount = max(0, int(status.get("guard", 0) or 0))

            payload = _card_event_payload(card, status="aegis_sentinel_shield", guard_bonus=amount, expired_on="DAMAGE_RESOLVED")
            bus.dispatch(
                "SHIELD_BROKEN",
                actor=side_name,
                source_card_id=card.get("id"),
                target_id=card.get("instance_id"),
                owner_id=side_name,
                payload=payload,
                message=f"O escudo de {card['name']} se desfaz após o dano.",
                order=order,
                priority_level=PRIORITY_DELAYED_EXPIRATION,
                resolution_phase="CLEANUP_PHASE",
            )
            bus.dispatch(
                "STATUS_EXPIRED",
                actor=side_name,
                source_card_id=card.get("id"),
                target_id=card.get("instance_id"),
                owner_id=side_name,
                payload=payload,
                message=f"O status de escudo de {card['name']} expirou.",
                order=order + 1,
                priority_level=PRIORITY_DELAYED_EXPIRATION,
                resolution_phase="CLEANUP_PHASE",
                chain_from_previous=True,
                apply_reducer=False,
            )
            order += 10


def _expire_shadow_exhausted(match: Dict[str, Any], bus: EffectBus) -> None:
    order = 400
    for side_name in ("player", "bot"):
        for card in _field_cards(match, side_name):
            if "shadow_reaper_exhausted" not in _status_bucket(card):
                continue

            payload = _card_event_payload(card, status="shadow_reaper_exhausted", expired_on="TURN_STARTED")
            bus.dispatch(
                "STATUS_EXPIRED",
                actor=side_name,
                source_card_id=card.get("id"),
                target_id=card.get("instance_id"),
                owner_id=side_name,
                payload=payload,
                message=f"A exaustão de {card['name']} expirou.",
                order=order,
                priority_level=PRIORITY_DELAYED_EXPIRATION,
                resolution_phase="CLEANUP_PHASE",
            )
            order += 10


def expire_statuses_for_trigger(match: Dict[str, Any], trigger: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
    context = dict(context or {})
    bus = EffectBus(
        match,
        effect_chain_id=context.get("effect_chain_id"),
        parent_event_id=context.get("parent_event_id"),
        root_event_id=context.get("root_event_id"),
    )
    trigger = str(trigger or "")
    if trigger == "DAMAGE_RESOLVED":
        _expire_aegis_shields(match, bus)
    elif trigger == "TURN_STARTED":
        _expire_shadow_exhausted(match, bus)
    return _message_list(bus.flush())
