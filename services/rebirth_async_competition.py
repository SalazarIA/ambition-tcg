"""Async competition contracts built on deterministic Rebirth replays."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Dict, List

from services.rebirth_domain import canonical_state_hash
from services.rebirth_replay import build_replay_envelope, verify_replay


ASYNC_COMPETITION_VERSION = "async-competition-v1"


def _public_share_code(match: Dict[str, Any], state_hash: str) -> str:
    seed = f"{match.get('match_id')}:{state_hash}:{match.get('card_set_version')}:{match.get('engine_version')}"
    return sha256(seed.encode("utf-8")).hexdigest()[:18]


def replay_share_payload(match: Dict[str, Any]) -> Dict[str, Any]:
    """Return a privacy-safe replay share contract for async competition."""

    state_hash = canonical_state_hash(match)
    verification = verify_replay(match)
    envelope = build_replay_envelope(match, include_stream=False)
    return {
        "version": ASYNC_COMPETITION_VERSION,
        "mode": "replay_share",
        "share_code": _public_share_code(match, state_hash),
        "match_id": match.get("match_id"),
        "state_hash": state_hash,
        "verified": bool(verification.get("ok")),
        "winner": match.get("winner"),
        "turn": int(match.get("turn", 0) or 0),
        "bot_profile_id": (match.get("bot_profile") or {}).get("id") or match.get("bot_profile_id"),
        "command_count": len(match.get("commands") or []),
        "replay_frame_count": len(match.get("events") or []),
        "replay": {
            "format_version": envelope.get("format_version"),
            "engine_version": envelope.get("engine_version"),
            "card_set_version": envelope.get("card_set_version"),
            "ruleset_version": envelope.get("ruleset_version"),
            "command_count": len(envelope.get("commands") or []),
        },
        "privacy": {
            "contains_email": False,
            "contains_account_id": False,
            "contains_private_collection": False,
        },
    }


def ghost_challenge_payload(match: Dict[str, Any]) -> Dict[str, Any]:
    initial = match.get("initial") or {}
    return {
        "version": ASYNC_COMPETITION_VERSION,
        "mode": "ghost_challenge",
        "share_code": replay_share_payload(match)["share_code"],
        "seed": str(match.get("game_seed") or match.get("seed") or ""),
        "player_deck_size": len(initial.get("player_card_ids") or []),
        "bot_profile_id": initial.get("bot_profile_id") or (match.get("bot_profile") or {}).get("id"),
        "rules": [
            "Replay is server-verifiable before it can enter any async ladder.",
            "Shared payload omits email, account id and full private collection.",
            "Ghost battles stay PvE until reconnect, anti-cheat and live ops are mature.",
        ],
    }


def async_competition_payload(match: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "share": replay_share_payload(match),
        "ghost": ghost_challenge_payload(match),
    }


def async_history_payload(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    shares = []
    for match in matches or []:
        state = match.get("state") if "state" in match else match
        if not state:
            continue
        shares.append(replay_share_payload(state))
    return {
        "version": ASYNC_COMPETITION_VERSION,
        "shares": shares,
        "count": len(shares),
    }
