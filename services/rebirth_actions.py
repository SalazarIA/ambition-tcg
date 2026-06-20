"""Canonical legal-action and safe-simulation API for Ambitionz Rebirth."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Dict, Iterable, Mapping

from services.rebirth_cards import is_monster, is_spell, is_trap
from services.rebirth_contracts import PHASE_CHOOSE, PHASE_RESULT, RebirthError
from services.rebirth_dispatcher import (
    DeclareAttackCommand,
    EndTurnCommand,
    EvolveDuplicateCommand,
    MulliganCommand,
    RebirthCommand,
    SummonCardCommand,
    dispatch_command,
)
from services.rebirth_engine import mulligan_available
from services.rebirth_state import FIELD_SLOT_COUNT, available_evolutions


ACTION_VERSION = 1
SUPPORTED_ACTORS = frozenset({"player"})
ACTION_TYPES = frozenset({"mulligan", "play_card", "attack", "evolve", "end_turn"})

_ACTION_PAYLOAD_FIELDS = {
    "mulligan": (),
    "play_card": ("card_instance_id", "card_id", "field_slot", "target_instance_id"),
    "attack": ("attacker_instance_id", "target_instance_id"),
    "evolve": ("card_id",),
    "end_turn": ("turn",),
}
_ACTION_ORDER = {
    "mulligan": 0,
    "evolve": 1,
    "play_card": 2,
    "attack": 3,
    "end_turn": 4,
}


def canonical_action(action_type: str, *, actor: str = "player", **payload: Any) -> Dict[str, Any]:
    """Return the stable, JSON-serializable representation of one action."""
    normalized_type = str(action_type or "").strip().lower()
    normalized_actor = str(actor or "").strip().lower()
    if normalized_type not in ACTION_TYPES:
        raise ValueError(f"Tipo de ação Rebirth não suportado: {action_type!r}")
    if normalized_actor not in SUPPORTED_ACTORS:
        raise ValueError(f"Ator Rebirth não suportado: {actor!r}")

    allowed_fields = _ACTION_PAYLOAD_FIELDS[normalized_type]
    unknown = sorted(set(payload) - set(allowed_fields))
    if unknown:
        raise ValueError(f"Campos inválidos para {normalized_type}: {', '.join(unknown)}")
    normalized_payload = {
        field: deepcopy(payload[field])
        for field in allowed_fields
        if field in payload and payload[field] is not None
    }
    action = {
        "version": ACTION_VERSION,
        "type": normalized_type,
        "actor": normalized_actor,
        "payload": normalized_payload,
    }
    # Fail immediately if a caller tries to put runtime objects in an action.
    json.dumps(action, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return action


def normalize_action(action: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize canonical actions and a small, convenient flat-dict form."""
    if not isinstance(action, Mapping):
        raise TypeError("A ação Rebirth deve ser um objeto mapeável.")
    version = action.get("version", ACTION_VERSION)
    if version != ACTION_VERSION:
        raise ValueError(f"Versão de ação Rebirth não suportada: {version!r}")

    action_type = str(action.get("type") or action.get("action_type") or "").strip().lower()
    actor = str(action.get("actor") or "player").strip().lower()
    raw_payload = action.get("payload") or {}
    if not isinstance(raw_payload, Mapping):
        raise TypeError("O payload da ação Rebirth deve ser um objeto mapeável.")
    payload = dict(raw_payload)
    for field in _ACTION_PAYLOAD_FIELDS.get(action_type, ()):
        if field in action and field not in payload:
            payload[field] = action[field]
    return canonical_action(action_type, actor=actor, **payload)


def action_to_command(action: Mapping[str, Any]) -> RebirthCommand:
    """Translate a canonical action into the real dispatcher command."""
    normalized = normalize_action(action)
    actor = normalized["actor"]
    payload = normalized["payload"]
    action_type = normalized["type"]
    if action_type == "mulligan":
        return MulliganCommand(actor=actor)
    if action_type == "play_card":
        return SummonCardCommand(
            actor=actor,
            card_instance_id=payload.get("card_instance_id"),
            card_id=payload.get("card_id"),
            field_slot=payload.get("field_slot"),
            target_instance_id=payload.get("target_instance_id"),
        )
    if action_type == "attack":
        return DeclareAttackCommand(
            actor=actor,
            attacker_instance_id=payload.get("attacker_instance_id"),
            target_instance_id=payload.get("target_instance_id"),
        )
    if action_type == "evolve":
        return EvolveDuplicateCommand(actor=actor, card_id=payload.get("card_id"))
    if action_type == "end_turn":
        return EndTurnCommand(actor=actor, turn=payload.get("turn"))
    raise ValueError(f"Tipo de ação Rebirth não suportado: {action_type!r}")


def command_for_action(action: Mapping[str, Any]) -> RebirthCommand:
    """Compatibility name for :func:`action_to_command`."""
    return action_to_command(action)


def _error_payload(exc: Exception) -> Dict[str, Any]:
    if isinstance(exc, RebirthError):
        return {"code": exc.code, "message": str(exc), "status": exc.status}
    return {
        "code": "invalid_action",
        "message": str(exc),
        "status": 400,
    }


def simulate_action(match: Mapping[str, Any], action: Mapping[str, Any]) -> Dict[str, Any]:
    """Dispatch one action on a deepcopy, preserving the supplied match."""
    baseline = deepcopy(match)
    simulated = deepcopy(match)
    try:
        command = action_to_command(action)
        result = dispatch_command(simulated, command)
    except Exception as exc:  # The simulation boundary always returns an error envelope.
        return {"state": baseline, "result": None, "error": _error_payload(exc)}
    return {"state": simulated, "result": deepcopy(result), "error": None}


def _card_can_target_enemy_unit(card: Mapping[str, Any]) -> bool:
    if not is_spell(card):
        return False
    for effect in card.get("stack_effects") or []:
        effect_type = str(effect.get("type") or "").strip().lower()
        target = str(effect.get("target") or "opponent").strip().lower()
        if effect_type == "damage" and target in {"opponent", "enemy"}:
            return True
    return False


def _live_field_cards(side: Mapping[str, Any]) -> list[Dict[str, Any]]:
    cards: list[Dict[str, Any]] = []
    seen = set()
    sources: Iterable[Any] = list(side.get("field") or []) + list(side.get("battlefield") or [])
    for card in sources:
        if not isinstance(card, dict):
            continue
        instance_id = card.get("instance_id")
        identity = instance_id or card.get("id") or id(card)
        if identity in seen:
            continue
        seen.add(identity)
        current_guard = int(card.get("current_guard", card.get("guard", 1)) or 0)
        if current_guard > 0:
            cards.append(card)
    return sorted(
        cards,
        key=lambda card: (
            int(card.get("field_slot", FIELD_SLOT_COUNT) or 0),
            str(card.get("instance_id") or ""),
        ),
    )


def _empty_slots(side: Mapping[str, Any]) -> list[int]:
    occupied = {
        int(card.get("field_slot"))
        for card in _live_field_cards(side)
        if isinstance(card.get("field_slot"), int) and 0 <= int(card["field_slot"]) < FIELD_SLOT_COUNT
    }
    return [slot for slot in range(FIELD_SLOT_COUNT) if slot not in occupied]


def _candidate_actions(match: Mapping[str, Any], actor: str) -> list[Dict[str, Any]]:
    if match.get("is_finished") or match.get("phase") not in {PHASE_CHOOSE, PHASE_RESULT}:
        return []

    actions: list[Dict[str, Any]] = []
    player = match.get(actor) or {}
    opponent = match.get("bot") or {}
    energy = int(player.get("energy", player.get("max_energy", 0)) or 0)
    enemy_units = _live_field_cards(opponent)

    if mulligan_available(match):
        actions.append(canonical_action("mulligan", actor=actor))

    for evolution in sorted(available_evolutions(player), key=lambda item: str(item.get("card_id") or "")):
        actions.append(canonical_action("evolve", actor=actor, card_id=evolution.get("card_id")))

    for card in sorted(
        player.get("hand") or [],
        key=lambda item: (str(item.get("instance_id") or ""), str(item.get("id") or "")),
    ):
        if int(card.get("cost", 0) or 0) > energy:
            continue
        common = {
            "card_instance_id": card.get("instance_id"),
            "card_id": card.get("id"),
        }
        if is_monster(card):
            for slot in _empty_slots(player):
                actions.append(canonical_action("play_card", actor=actor, field_slot=slot, **common))
        elif is_spell(card):
            actions.append(canonical_action("play_card", actor=actor, **common))
            if _card_can_target_enemy_unit(card):
                for target in enemy_units:
                    actions.append(
                        canonical_action(
                            "play_card",
                            actor=actor,
                            target_instance_id=target.get("instance_id"),
                            **common,
                        )
                    )
        elif is_trap(card):
            actions.append(canonical_action("play_card", actor=actor, **common))

    from services.rebirth_keywords import can_attack_this_turn, forces_target, has_taunt_on_side

    attack_targets = (
        [card for card in enemy_units if forces_target(card)]
        if has_taunt_on_side(enemy_units)
        else enemy_units
    )
    for attacker in _live_field_cards(player):
        attacker_id = attacker.get("instance_id")
        if not attacker_id:
            continue
        if attacker.get("exhausted") or attacker.get("has_attacked") or attacker.get("has_acted"):
            continue
        if not can_attack_this_turn(attacker, just_summoned=bool(attacker.get("just_summoned"))):
            continue
        if attack_targets:
            for target in attack_targets:
                actions.append(
                    canonical_action(
                        "attack",
                        actor=actor,
                        attacker_instance_id=attacker_id,
                        target_instance_id=target.get("instance_id"),
                    )
                )
        else:
            actions.append(canonical_action("attack", actor=actor, attacker_instance_id=attacker_id))

    actions.append(canonical_action("end_turn", actor=actor, turn=match.get("turn")))
    return actions


def _action_sort_key(action: Mapping[str, Any]) -> tuple[int, str]:
    return (
        _ACTION_ORDER.get(str(action.get("type") or ""), len(_ACTION_ORDER)),
        json.dumps(action.get("payload") or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
    )


def legal_actions(
    match: Mapping[str, Any],
    actor: str = "player",
    *,
    verify: bool = True,
) -> list[Dict[str, Any]]:
    """Enumerate dispatcher-proven legal actions without mutating ``match``."""
    normalized_actor = str(actor or "").strip().lower()
    if normalized_actor not in SUPPORTED_ACTORS:
        raise ValueError(f"Ator Rebirth não suportado: {actor!r}")

    snapshot = deepcopy(match)
    legal = []
    seen = set()
    for action in _candidate_actions(snapshot, normalized_actor):
        serialized = json.dumps(action, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if serialized in seen:
            continue
        seen.add(serialized)
        if not verify or simulate_action(snapshot, action)["error"] is None:
            legal.append(action)
    return sorted(legal, key=_action_sort_key)


__all__ = [
    "ACTION_TYPES",
    "ACTION_VERSION",
    "action_to_command",
    "canonical_action",
    "command_for_action",
    "legal_actions",
    "normalize_action",
    "simulate_action",
]
