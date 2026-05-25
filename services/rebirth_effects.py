"""Canonical deterministic effect bus for Rebirth gameplay.

This module owns triggered passive resolution. It deliberately does not know
about Flask, sockets or browser rendering; callers provide an authoritative
match dict and receive serializable GameEvents through ``append_event``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from services.rebirth_contracts import RebirthError
from services.rebirth_domain import MAX_EFFECT_CHAIN_DEPTH, canonical_json, canonical_state_hash
from services.rebirth_events import append_event, new_effect_chain_id
from services.rebirth_reducers import reduce_event
from services.rebirth_state import field_slots


LEGENDARY_INFERNUS = "infernus_core"
LEGENDARY_AEGIS = "aegis_sentinel"
LEGENDARY_SHADOW = "shadow_reaper"


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
    ) -> bool:
        depth = int(self.match.get("_event_dispatch_depth", 0) or 0)
        if depth >= MAX_EFFECT_CHAIN_DEPTH:
            raise RebirthError("Profundidade máxima da cadeia de efeitos excedida.", "effect_chain_depth_exceeded")
        payload = _frozen_payload(payload)
        dispatch_key = canonical_json(
            {
                "event_type": str(event_type),
                "source_card_id": source_card_id,
                "target_id": target_id,
                "owner_id": owner_id if owner_id is not None else actor,
                "payload": payload,
                "parent_event_id": parent_event_id if parent_event_id is not None else self.parent_event_id,
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
            }
        )
        return True

    def flush(self) -> List[Dict[str, Any]]:
        ordered = sorted(
            self._queue,
            key=lambda item: (
                item["order"],
                item["event_type"],
                item.get("source_card_id") or "",
                item.get("target_id") or "",
                canonical_json(item.get("payload") or {}),
            ),
        )
        self._queue = []
        self.match["_event_dispatch_depth"] = int(self.match.get("_event_dispatch_depth", 0) or 0) + 1
        try:
            emitted = []
            previous_event_id = None
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
                )
                if item.get("apply_reducer"):
                    reduced = reduce_event(self.match, event)
                    self.match.clear()
                    self.match.update(reduced)
                    self.match["events"][-1]["canonical_state_hash"] = canonical_state_hash(self.match)
                emitted.append(self.match["events"][-1])
                previous_event_id = emitted[-1]["event_id"]
            return emitted
        finally:
            self.match["_event_dispatch_depth"] = max(0, int(self.match.get("_event_dispatch_depth", 1) or 1) - 1)


def _message_list(events: Iterable[Dict[str, Any]]) -> List[str]:
    return [event["message"] for event in events if event.get("message")]


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
