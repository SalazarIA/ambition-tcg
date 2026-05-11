"""Canonical arena command contract for BE2 clients.

The command envelope is intentionally small: it identifies one player action
and carries only the fields the BE2 facade can validate server-side.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


ARENA_COMMAND_SCHEMA = "arena_command_v1"

VALID_ARENA_COMMANDS = {
    "start_training",
    "request_state",
    "set_intent",
    "play_card",
    "ready",
    "unleash",
}

COMMAND_ALIASES = {
    "az48_start_training": "start_training",
    "start": "start_training",
    "start-training": "start_training",
    "az48_request_state": "request_state",
    "request-state": "request_state",
    "state": "request_state",
    "az48_set_intent": "set_intent",
    "set-intent": "set_intent",
    "choose_intent": "set_intent",
    "choose-intent": "set_intent",
    "az48_play_card": "play_card",
    "play-card": "play_card",
    "play_to_field": "play_card",
    "play-to-field": "play_card",
    "az48_declare_ready": "ready",
    "declare_ready": "ready",
    "declare-ready": "ready",
    "az48_unleash": "unleash",
    "toggle_unleash": "unleash",
    "toggle-unleash": "unleash",
}


class ArenaCommandError(ValueError):
    pass


def _clean_action(value: Any) -> str:
    action = str(value or "").strip()
    action = action.replace("-", "_")
    return COMMAND_ALIASES.get(action, action)


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception as error:
        raise ArenaCommandError("Invalid card index.") from error


def normalize_arena_command(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    data = payload or {}
    if not isinstance(data, dict):
        raise ArenaCommandError("Arena command payload must be an object.")

    action = _clean_action(data.get("action") or data.get("command") or data.get("type"))
    if action not in VALID_ARENA_COMMANDS:
        raise ArenaCommandError("Invalid arena command.")

    command = {
        "schema": ARENA_COMMAND_SCHEMA,
        "action": action,
        "client_command_id": _optional_str(data.get("client_command_id") or data.get("idempotency_key")),
    }

    if action == "set_intent":
        command["intent"] = _optional_str(data.get("intent")) or "Focus"

    if action == "play_card":
        card_id = _optional_str(data.get("card_id") or data.get("id"))
        card_index = _optional_int(data.get("card_index", data.get("index")))
        if card_id is None and card_index is None:
            raise ArenaCommandError("Card selection required.")
        command.update({
            "card_id": card_id,
            "card_index": card_index,
            "lane": _optional_str(data.get("lane")),
            "target": _optional_str(data.get("target")),
        })

    if action in {"start_training", "request_state"}:
        command["difficulty"] = _optional_str(data.get("difficulty"))

    return command


def arena_command_error_payload(error: Exception, code: str = "ARENA_COMMAND_FAILED") -> Dict[str, str]:
    return {
        "schema": ARENA_COMMAND_SCHEMA,
        "code": code,
        "message": str(error),
    }
