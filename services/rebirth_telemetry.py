"""Telemetry payload builders for Rebirth.

Persistence still belongs to the repository; this module owns event shape.
"""

from __future__ import annotations

from hashlib import sha256
from math import isfinite
from typing import Any, Dict, Optional


REBIRTH_DECISION_TELEMETRY_EVENT = "decision_made"

REBIRTH_CLIENT_TELEMETRY_EVENTS = {
    "match_abandoned",
    "client_error",
    "tutorial_step_viewed",
    "feedback_opened",
    "first_session_action",
}


def _clean_decision_token(value: Any, *, limit: int) -> Optional[str]:
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return None
    clean = "".join(character for character in str(value).strip() if character.isprintable())
    return clean[:limit] or None


def _clean_nonnegative_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _clean_score(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return round(score, 6) if isfinite(score) else None


def _clean_decision_actor(value: Any) -> Optional[str]:
    actor = _clean_decision_token(value, limit=20)
    if not actor:
        return None
    actor = actor.lower()
    if actor in {"human", "player"}:
        return "human"
    if actor in {"bot", "ai", "automated"}:
        return "bot"
    return None


def build_decision_telemetry_payload(
    decision: Optional[Dict[str, Any]] = None,
    *,
    actor: Any = None,
    action_type: Any = None,
    legal_action_count: Any = None,
    chosen_action_id: Any = None,
    chosen_action_fingerprint: Any = None,
    best_action_id: Any = None,
    chosen_score: Any = None,
    best_score: Any = None,
    regret: Any = None,
    decision_elapsed_ms: Any = None,
    elapsed_ms: Any = None,
    turn: Any = None,
    profile: Any = None,
    profile_id: Any = None,
    bot_profile_id: Any = None,
    difficulty: Any = None,
    archetype: Any = None,
) -> Dict[str, Any]:
    """Build the allowlisted, non-sensitive payload for ``decision_made``."""
    source = decision if isinstance(decision, dict) else {}

    def supplied(value: Any, key: str) -> Any:
        return value if value is not None else source.get(key)

    clean_chosen_score = _clean_score(supplied(chosen_score, "chosen_score"))
    clean_best_score = _clean_score(supplied(best_score, "best_score"))
    clean_regret = _clean_score(supplied(regret, "regret"))
    if clean_regret is None and clean_chosen_score is not None and clean_best_score is not None:
        clean_regret = max(0.0, round(clean_best_score - clean_chosen_score, 6))
    elif clean_regret is not None:
        clean_regret = max(0.0, clean_regret)

    profile_value = profile if profile is not None else profile_id
    if profile_value is None:
        profile_value = bot_profile_id
    if profile_value is None:
        profile_value = source.get("profile_id") or source.get("bot_profile_id")
    elapsed_value = decision_elapsed_ms if decision_elapsed_ms is not None else elapsed_ms
    if elapsed_value is None:
        elapsed_value = source.get("decision_elapsed_ms")
    if elapsed_value is None:
        elapsed_value = source.get("elapsed_ms")

    payload = {
        "actor": _clean_decision_actor(supplied(actor, "actor")),
        "action_type": _clean_decision_token(supplied(action_type, "action_type"), limit=80),
        "legal_action_count": _clean_nonnegative_int(supplied(legal_action_count, "legal_action_count")),
        "chosen_action_id": _clean_decision_token(supplied(chosen_action_id, "chosen_action_id"), limit=160),
        "chosen_action_fingerprint": _clean_decision_token(
            supplied(chosen_action_fingerprint, "chosen_action_fingerprint"),
            limit=128,
        ),
        "best_action_id": _clean_decision_token(supplied(best_action_id, "best_action_id"), limit=160),
        "chosen_score": clean_chosen_score,
        "best_score": clean_best_score,
        "regret": clean_regret,
        "decision_elapsed_ms": _clean_nonnegative_int(elapsed_value),
        "turn": _clean_nonnegative_int(supplied(turn, "turn")),
        "profile": _clean_decision_token(profile_value, limit=80),
        "difficulty": _clean_decision_token(supplied(difficulty, "difficulty"), limit=80),
        "archetype": _clean_decision_token(supplied(archetype, "archetype"), limit=40),
    }
    return {key: value for key, value in payload.items() if value is not None}


# Explicit alias for callers that name builders after the event rather than the domain.
build_decision_made_payload = build_decision_telemetry_payload


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
    bot_difficulty_id = (match.get("bot_difficulty") or {}).get("id") or match.get("bot_difficulty_id")
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
        "bot_difficulty_id": bot_difficulty_id,
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
