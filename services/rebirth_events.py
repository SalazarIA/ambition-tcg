import hashlib
import json
from copy import deepcopy

from services.rebirth_domain import (
    CARD_SET_VERSION,
    ENGINE_VERSION,
    SNAPSHOT_FORMAT_VERSION,
    canonical_state_hash,
    compress_canonical_state,
)


def _safe_payload(payload=None):
    if payload is None:
        return {}
    return deepcopy(payload)


def _next_version(match):
    match["version"] = int(match.get("version", 0) or 0) + 1
    return match["version"]


def ensure_event_contract(match):
    match.setdefault("version", 0)
    match.setdefault("commands", [])
    match.setdefault("events", [])
    match.setdefault("snapshots", [])
    return match


def append_command(match, command_type, *, actor="player", payload=None):
    ensure_event_contract(match)
    version = _next_version(match)
    command = {
        "id": len(match["commands"]) + 1,
        "version": version,
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "correlation_id": f"{match.get('match_id', 'match')}:{version}",
        "turn": int(match.get("turn", 0) or 0),
        "type": str(command_type),
        "actor": str(actor),
        "payload": _safe_payload(payload),
    }
    match["commands"].append(command)
    return command


def append_event(match, event_type, *, actor="system", payload=None, message=None):
    ensure_event_contract(match)
    version = _next_version(match)
    event = {
        "id": len(match["events"]) + 1,
        "version": version,
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "correlation_id": f"{match.get('match_id', 'match')}:{version}",
        "turn": int(match.get("turn", 0) or 0),
        "type": str(event_type),
        "actor": str(actor),
        "payload": _safe_payload(payload),
    }
    if message:
        event["message"] = str(message)
    match["events"].append(event)
    return event


def state_hash(match):
    publicish = {
        "match_id": match.get("match_id"),
        "version": match.get("version"),
        "turn": match.get("turn"),
        "phase": match.get("phase"),
        "winner": match.get("winner"),
        "is_finished": bool(match.get("is_finished")),
        "player": {
            "hp": (match.get("player") or {}).get("hp"),
            "deck_count": len((match.get("player") or {}).get("deck", [])),
            "hand_ids": [card.get("id") for card in (match.get("player") or {}).get("hand", [])],
            "discard_count": len((match.get("player") or {}).get("discard", [])),
            "played": ((match.get("player") or {}).get("played_card") or {}).get("id"),
        },
        "bot": {
            "hp": (match.get("bot") or {}).get("hp"),
            "deck_count": len((match.get("bot") or {}).get("deck", [])),
            "hand_count": len((match.get("bot") or {}).get("hand", [])),
            "discard_count": len((match.get("bot") or {}).get("discard", [])),
            "played": ((match.get("bot") or {}).get("played_card") or {}).get("id"),
        },
        "last_event": (match.get("events") or [{}])[-1].get("type"),
    }
    encoded = json.dumps(publicish, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def append_snapshot(match, reason):
    ensure_event_contract(match)
    snapshot = {
        "format_version": SNAPSHOT_FORMAT_VERSION,
        "version": int(match.get("version", 0) or 0),
        "turn": int(match.get("turn", 0) or 0),
        "phase": match.get("phase"),
        "reason": str(reason),
        "state_hash": state_hash(match),
        "canonical_state_hash": canonical_state_hash(match),
        "state_encoding": "gzip+base64+json",
        "canonical_state": compress_canonical_state(match),
    }
    match["snapshots"].append(snapshot)
    match["snapshots"] = match["snapshots"][-20:]
    return snapshot
