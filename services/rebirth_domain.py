"""Deterministic domain contracts for the active Rebirth engine.

The values in this module are intentionally transport-neutral. Flask routes,
browser rendering and future realtime servers can wrap them, but replay,
integrity checks and bot simulation should all agree on these contracts.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from copy import deepcopy
from typing import Any, Dict


ENGINE_VERSION = "rebirth_engine_v62"
CARD_SET_VERSION = "rebirth_card_set_v66"
REPLAY_FORMAT_VERSION = "rebirth_replay_v2"
REPLAY_SCHEMA_VERSION = "rebirth_replay_schema_v62"
SNAPSHOT_FORMAT_VERSION = "rebirth_snapshot_v2"
RULESET_VERSION = "rebirth_ruleset_v62"
REDUCER_VERSION = "rebirth_reducer_v62"
MAX_EFFECT_CHAIN_DEPTH = 8
MAX_CAUSAL_CHAIN_DEPTH = 12
MAX_INTERRUPT_DEPTH = 4
MAX_PHASE_ITERATIONS = 24

CANONICAL_CARD_FIELDS = (
    "id",
    "instance_id",
    "owner",
    "sequence",
    "type",
    "card_type",
    "family",
    "tier",
    "cost",
    "attack",
    "power",
    "guard",
    "current_guard",
    "max_guard",
    "attack_adjustment",
    "guard_adjustment",
    "base_attack",
    "base_guard",
    "permanent_attack_bonus",
    "temporary_guard_bonus",
    "shield_expires_on",
    "element",
    "ability_key",
    "evolution_id",
    "field_slot",
    "slot",
    "exhausted",
    "has_attacked",
    "has_acted",
    "wounded",
    "defeated",
    "armed",
    "revealed",
    "face_down",
    "owner_side",
    "trigger_phase",
    "trigger",
    "trap_effect",
    "effect_chain_id",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable_value(item) for item in value]
    if isinstance(value, tuple):
        return [_stable_value(item) for item in value]
    return deepcopy(value)


def canonical_card(card: Any) -> Any:
    if not card:
        return None
    if not isinstance(card, dict):
        return _stable_value(card)
    payload = {
        field: _stable_value(card[field])
        for field in CANONICAL_CARD_FIELDS
        if field in card
    }
    if "statuses" in card:
        payload["statuses"] = _stable_value(card.get("statuses") or {})
    if "status_effects" in card:
        payload["status_effects"] = _stable_value(card.get("status_effects") or [])
    if "stack_effects" in card:
        payload["stack_effects"] = _stable_value(card.get("stack_effects") or [])
    if "heuristic_vector" in card:
        payload["heuristic_vector"] = _stable_value(card.get("heuristic_vector") or {})
    return payload


def canonical_side(side: Dict[str, Any]) -> Dict[str, Any]:
    side = side or {}
    return {
        "name": side.get("name"),
        "hp": int(side.get("hp", 0) or 0),
        "max_hp": int(side.get("max_hp", side.get("hp", 0)) or 0),
        "energy": int(side.get("energy", 0) or 0),
        "max_energy": int(side.get("max_energy", 0) or 0),
        "wounded": bool(side.get("wounded")),
        "statuses": _stable_value(side.get("statuses") or {}),
        "deck": [canonical_card(card) for card in side.get("deck", [])],
        "hand": [canonical_card(card) for card in side.get("hand", [])],
        "battlefield": [canonical_card(card) for card in side.get("battlefield", [])],
        "field": [canonical_card(card) for card in side.get("field", [])],
        "discard": [canonical_card(card) for card in side.get("discard", [])],
        "played_card": canonical_card(side.get("played_card")),
        "traps": [canonical_card(card) for card in side.get("traps", [])],
    }


def _canonical_result(value: Any) -> Any:
    if not isinstance(value, dict):
        return _stable_value(value)
    payload = deepcopy(value)
    # Human text can change without changing game semantics.
    payload.pop("message", None)
    payload.pop("ability_events", None)
    if "player_card" in payload:
        payload["player_card"] = canonical_card(payload.get("player_card"))
    if "bot_card" in payload:
        payload["bot_card"] = canonical_card(payload.get("bot_card"))
    return _stable_value(payload)


def canonical_state(match: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "ruleset_version": match.get("ruleset_version") or RULESET_VERSION,
        "reducer_version": match.get("reducer_version") or REDUCER_VERSION,
        "game_seed": str(match.get("game_seed", match.get("seed", "")) or ""),
        "turn": int(match.get("turn", 0) or 0),
        "phase": match.get("phase"),
        "turn_phase": match.get("turn_phase"),
        "winner": match.get("winner"),
        "is_finished": bool(match.get("is_finished")),
        "player": canonical_side(match.get("player") or {}),
        "bot": canonical_side(match.get("bot") or {}),
        "bot_profile_id": (match.get("bot_profile") or {}).get("id"),
        "result": _canonical_result(match.get("result")),
        "last_clash": _canonical_result(match.get("last_clash")),
    }


def canonical_state_hash(match: Dict[str, Any]) -> str:
    encoded = serialize_canonical_state(match)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def serialize_canonical_state(match: Dict[str, Any]) -> str:
    return canonical_json(canonical_state(match))


def compress_canonical_state(match: Dict[str, Any]) -> str:
    raw = serialize_canonical_state(match).encode("utf-8")
    return base64.b64encode(gzip.compress(raw)).decode("ascii")


def decompress_snapshot_state(encoded: str) -> Dict[str, Any]:
    raw = gzip.decompress(base64.b64decode(str(encoded).encode("ascii")))
    return json.loads(raw.decode("utf-8"))
