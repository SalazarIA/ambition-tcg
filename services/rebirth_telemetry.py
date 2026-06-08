"""Telemetry payload builders for Rebirth.

Persistence still belongs to the repository; this module owns event shape.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Dict, Optional


REBIRTH_CLIENT_TELEMETRY_EVENTS = {
    "match_abandoned",
    "client_error",
    "tutorial_step_viewed",
    "feedback_opened",
    "first_session_action",
}


def build_match_telemetry_payload(
    match: Dict[str, Any],
    event_type: str,
    *,
    elapsed_ms: Optional[int] = None,
    total_elapsed_ms: Optional[int] = None,
    release_version: Optional[str] = None,
    authenticated: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result = match.get("result") or {}
    events = match.get("events") or []
    initial = match.get("initial") or {}
    player_deck_ids = [str(card_id) for card_id in (initial.get("player_card_ids") or []) if card_id]
    chain_ids = {event.get("effect_chain_id") for event in events if event.get("effect_chain_id")}
    chain_lengths: Dict[str, int] = {}
    for event in events:
        chain_id = event.get("effect_chain_id")
        if chain_id:
            chain_lengths[chain_id] = chain_lengths.get(chain_id, 0) + 1
    bot_profile_id = (match.get("bot_profile") or {}).get("id") or match.get("bot_profile_id")
    payload = {
        "match_id": str(match.get("match_id") or ""),
        "turn": int(match.get("turn", 0) or 0),
        "phase": match.get("phase"),
        "is_finished": bool(match.get("is_finished")),
        "winner": match.get("winner"),
        "outcome": result.get("outcome"),
        "player_hp": int((match.get("player") or {}).get("hp", 0) or 0),
        "bot_hp": int((match.get("bot") or {}).get("hp", 0) or 0),
        "event_count": len(events),
        "chain_count": len(chain_ids),
        "max_chain_length": max(chain_lengths.values()) if chain_lengths else 0,
        "bot_profile_id": bot_profile_id,
        "match_duration_ms": total_elapsed_ms if event_type in {"match_finished", "match_abandoned"} or match.get("is_finished") else None,
        "player_deck_size": len(player_deck_ids) if player_deck_ids else None,
        "player_deck_signature": sha256(",".join(player_deck_ids).encode("utf-8")).hexdigest()[:16] if player_deck_ids else None,
        "first_duel": bool(match.get("first_duel")),
        "decision_elapsed_ms": elapsed_ms,
        "campaign_version": match.get("campaign_version"),
        "campaign_node": match.get("campaign_node"),
        "campaign_attempt": match.get("campaign_attempt"),
        "node_retry_count": max(0, int(match.get("campaign_attempt", 1) or 1) - 1) if match.get("campaign_node") else None,
        "abandon_turn": int(match.get("turn", 0) or 0) if event_type == "match_abandoned" else None,
        "first_loss_node": match.get("campaign_node")
        if match.get("campaign_node")
        and match.get("is_finished")
        and match.get("winner") == "bot"
        and int(match.get("campaign_attempt", 1) or 1) == 1
        else None,
        "victory_duration": total_elapsed_ms
        if match.get("campaign_node") and match.get("is_finished") and match.get("winner") == "player"
        else None,
        "average_turns": int(match.get("turn", 0) or 0) if match.get("campaign_node") and match.get("is_finished") else None,
        "rebirth_release_version": release_version,
        "cohort": "account" if authenticated else "guest",
    }
    payload.update({key: value for key, value in (extra or {}).items() if value is not None})
    return {key: value for key, value in payload.items() if value is not None}


def client_telemetry_payload(event_type: str, payload: Dict[str, Any], *, user: Optional[Dict[str, Any]] = None, release_version: Optional[str] = None) -> Dict[str, Any]:
    clean = {
        "event_type": event_type,
        "rebirth_release_version": release_version,
        "authenticated": bool(user),
        "cohort": "account" if user else "guest",
        "match_id": str(payload.get("match_id") or "").strip() or None,
        "surface": str(payload.get("surface") or "").strip()[:80] or None,
        "reason": str(payload.get("reason") or "").strip()[:240] or None,
        "step": payload.get("step"),
        "message": str(payload.get("message") or "").strip()[:1000] or None,
        "first_session_key": str(payload.get("first_session_key") or "").strip()[:80] or None,
    }
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        clean["metadata"] = {str(key)[:60]: str(value)[:240] for key, value in metadata.items() if value is not None}
    return {key: value for key, value in clean.items() if value is not None}
