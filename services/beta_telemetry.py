from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


ALLOWED_BETA_TELEMETRY_EVENTS = {
    "visit_home",
    "start_training",
    "finish_match",
    "claim_daily",
    "open_shop",
    "buy_booster",
    "open_booster",
    "save_deck",
    "view_collection",
    "view_roadmap",
    "dismiss_first_session_quest",
}

ALLOWED_BETA_FEEDBACK_TYPES = {"bug", "balance", "suggestion", "praise", "other"}


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: Any, limit: int, fallback: str = "") -> str:
    text = str(value if value is not None else fallback).strip()
    return text[:limit]


def safe_metadata(value: Any, max_keys: int = 24, value_limit: int = 240) -> Dict[str, str]:
    if not isinstance(value, dict):
        return {}

    cleaned: Dict[str, str] = {}

    for key, item in list(value.items())[:max_keys]:
        safe_key = safe_text(key, 80)

        if not safe_key:
            continue

        if isinstance(item, (dict, list, tuple)):
            safe_value = json.dumps(item, ensure_ascii=False, default=str)
        else:
            safe_value = str(item if item is not None else "")

        cleaned[safe_key] = safe_value[:value_limit]

    return cleaned


def normalize_telemetry_payload(payload: Any) -> Tuple[Dict[str, Any], str]:
    if not isinstance(payload, dict):
        return {}, "invalid_payload"

    event = safe_text(payload.get("event") or payload.get("event_key"), 80)

    if event not in ALLOWED_BETA_TELEMETRY_EVENTS:
        return {}, "invalid_event"

    page = safe_text(payload.get("page") or payload.get("path"), 220, "/")
    metadata = safe_metadata(payload.get("metadata") or {})
    source = safe_text(payload.get("source"), 80, "web")

    if source:
        metadata.setdefault("source", source)

    return {
        "event": event,
        "page": page or "/",
        "metadata": metadata,
    }, ""


def normalize_feedback_payload(payload: Any) -> Tuple[Dict[str, Any], str]:
    if not isinstance(payload, dict):
        return {}, "invalid_payload"

    feedback_type = safe_text(payload.get("type") or payload.get("category"), 40, "other")

    if feedback_type not in ALLOWED_BETA_FEEDBACK_TYPES:
        feedback_type = "other"

    message = safe_text(payload.get("message"), 2000)

    if len(message) < 8:
        return {}, "message_too_short"

    page = safe_text(payload.get("page") or payload.get("path"), 220, "")

    return {
        "type": feedback_type,
        "message": message,
        "page": page,
    }, ""


def append_jsonl(app, filename: str, record: Dict[str, Any]) -> Path:
    base = Path(getattr(app, "instance_path", "") or ".")
    base.mkdir(parents=True, exist_ok=True)
    path = base / filename

    safe_record = dict(record or {})
    safe_record.setdefault("recorded_at", utc_iso())

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe_record, ensure_ascii=False, default=str) + "\n")

    return path
