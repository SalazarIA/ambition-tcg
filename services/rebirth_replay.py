"""Deterministic replay helpers for Rebirth matches."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable

from services.rebirth_domain import (
    CARD_SET_VERSION,
    ENGINE_VERSION,
    REPLAY_FORMAT_VERSION,
    canonical_state_hash,
)
from services.rebirth_engine import declare_attack, evolve_duplicate, next_turn, play_card, start_match
from services.rebirth_contracts import RebirthError


SUPPORTED_COMMANDS = {"PLAY_CARD", "DECLARE_ATTACK", "EVOLVE_DUPLICATE", "NEXT_TURN"}


def build_replay_envelope(match: Dict[str, Any]) -> Dict[str, Any]:
    initial = deepcopy(match.get("initial") or {})
    return {
        "format_version": REPLAY_FORMAT_VERSION,
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "match_id": match.get("match_id"),
        "game_seed": str(match.get("game_seed", match.get("seed", "")) or ""),
        "display_seed": str(match.get("seed", "") or ""),
        "initial": {
            "player_card_ids": list(initial.get("player_card_ids") or []),
            "player_name": initial.get("player_name") or (match.get("player") or {}).get("name") or "Voc\u00ea",
            "bot_profile_id": initial.get("bot_profile_id") or (match.get("bot_profile") or {}).get("id"),
        },
        "commands": deepcopy(match.get("commands") or []),
        "expected_canonical_state_hash": canonical_state_hash(match),
    }


def _commands_from(source: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    commands = source.get("commands") or []
    return sorted(commands, key=lambda command: int(command.get("id", 0) or 0))


def _assert_replay_versions(envelope: Dict[str, Any]) -> None:
    engine_version = envelope.get("engine_version")
    card_set_version = envelope.get("card_set_version")
    if engine_version != ENGINE_VERSION:
        raise RebirthError(f"Replay engine incompativel: {engine_version}", "replay_engine_mismatch", status=409)
    if card_set_version != CARD_SET_VERSION:
        raise RebirthError(f"Replay card set incompativel: {card_set_version}", "replay_card_set_mismatch", status=409)


def replay_match(source: Dict[str, Any]) -> Dict[str, Any]:
    envelope = build_replay_envelope(source) if source.get("match_id") and "format_version" not in source else deepcopy(source)
    _assert_replay_versions(envelope)
    initial = envelope.get("initial") or {}
    match = start_match(
        seed=envelope.get("game_seed"),
        player_card_ids=initial.get("player_card_ids") or None,
        player_name=initial.get("player_name") or "Voc\u00ea",
        bot_profile_id=initial.get("bot_profile_id"),
    )
    match["seed"] = str(envelope.get("display_seed", "") or "")

    for command in _commands_from(envelope):
        command_type = str(command.get("type") or "")
        payload = command.get("payload") or {}
        if command_type not in SUPPORTED_COMMANDS:
            raise RebirthError(f"Comando de replay nao suportado: {command_type}", "replay_command_unsupported", status=409)
        if command_type == "PLAY_CARD":
            play_card(
                match,
                card_instance_id=payload.get("card_instance_id"),
                card_id=payload.get("card_id"),
                field_slot=payload.get("field_slot"),
            )
        elif command_type == "DECLARE_ATTACK":
            declare_attack(
                match,
                attacker_instance_id=payload.get("attacker_instance_id"),
                target_instance_id=payload.get("target_instance_id"),
            )
        elif command_type == "EVOLVE_DUPLICATE":
            evolve_duplicate(match, payload.get("card_id"))
        elif command_type == "NEXT_TURN":
            next_turn(match)
    return match


def verify_replay(source: Dict[str, Any]) -> Dict[str, Any]:
    envelope = build_replay_envelope(source) if source.get("match_id") and "format_version" not in source else deepcopy(source)
    replayed = replay_match(envelope)
    actual = canonical_state_hash(replayed)
    expected = envelope.get("expected_canonical_state_hash")
    return {
        "ok": actual == expected,
        "expected_canonical_state_hash": expected,
        "actual_canonical_state_hash": actual,
        "command_count": len(list(_commands_from(envelope))),
        "engine_version": ENGINE_VERSION,
        "card_set_version": CARD_SET_VERSION,
    }
