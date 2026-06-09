"""External gate evidence validation for Rebirth beta readiness.

The evidence file is intentionally small and secret-free. It proves that a
human/operator completed checks outside this repository without storing raw
credentials, DSNs or database identifiers in source control.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping


LEGAL_SCOPE = {"terms", "privacy", "data_deletion", "billing_disabled"}
BACKUP_RESTORE_MAX_AGE_DAYS = 30
ERROR_TRACKING_MAX_AGE_DAYS = 14


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on", "passed"}


def _parse_iso(value: Any) -> datetime | None:
    if not _present(value):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: Any) -> bool:
    return _parse_iso(value) is not None


def _fresh_iso(value: Any, *, now: datetime, max_age_days: int) -> bool:
    parsed = _parse_iso(value)
    if not parsed:
        return False
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    age = now - parsed
    return 0 <= age.total_seconds() <= max_age_days * 24 * 60 * 60


def _has_any_secret_text(values: Iterable[Any]) -> bool:
    text = "\n".join(str(value or "") for value in values).lower()
    secret_markers = ("postgres://", "postgresql://", "sk_live_", "sk_test_", "sentry_dsn=", "password=", "pwd=")
    return any(marker in text for marker in secret_markers)


def _result(valid: bool, errors: List[str]) -> Dict[str, Any]:
    return {"valid": bool(valid), "errors": errors}


def _legal(evidence: Mapping[str, Any], *, example: bool) -> Dict[str, Any]:
    data = evidence.get("legal_review") or {}
    errors: List[str] = []
    if example:
        errors.append("example_evidence_file")
    if not _bool(data.get("approved")):
        errors.append("approved_required")
    if not _present(data.get("reviewer")):
        errors.append("reviewer_required")
    if not _iso(data.get("approved_at")):
        errors.append("approved_at_iso_required")
    scope = {str(item).strip() for item in data.get("scope") or []}
    missing = sorted(LEGAL_SCOPE - scope)
    if missing:
        errors.append("scope_missing:" + ",".join(missing))
    if not _present(data.get("evidence_ref")):
        errors.append("evidence_ref_required")
    return _result(not errors, errors)


def _backup_restore(evidence: Mapping[str, Any], *, example: bool, now: datetime) -> Dict[str, Any]:
    data = evidence.get("backup_restore") or {}
    errors: List[str] = []
    if example:
        errors.append("example_evidence_file")
    if not _bool(data.get("validated")):
        errors.append("validated_required")
    if not _iso(data.get("drill_at")):
        errors.append("drill_at_iso_required")
    elif not _fresh_iso(data.get("drill_at"), now=now, max_age_days=BACKUP_RESTORE_MAX_AGE_DAYS):
        errors.append(f"drill_at_stale:>{BACKUP_RESTORE_MAX_AGE_DAYS}d")
    for key in ("operator", "source_commit", "restore_target", "evidence_ref"):
        if not _present(data.get(key)):
            errors.append(f"{key}_required")
    try:
        if int(data.get("dump_bytes", 0) or 0) <= 0:
            errors.append("dump_bytes_positive_required")
    except (TypeError, ValueError):
        errors.append("dump_bytes_positive_required")
    for key in ("schema_check", "health_check", "support_export_check"):
        if str(data.get(key) or "").strip().lower() != "passed":
            errors.append(f"{key}_passed_required")
    if _has_any_secret_text(data.values()):
        errors.append("secret_like_value_detected")
    return _result(not errors, errors)


def _error_tracking(evidence: Mapping[str, Any], *, example: bool, now: datetime) -> Dict[str, Any]:
    data = evidence.get("error_tracking") or {}
    errors: List[str] = []
    if example:
        errors.append("example_evidence_file")
    if not _bool(data.get("validated")):
        errors.append("validated_required")
    for key in ("provider", "environment", "test_event_id", "tested_at", "evidence_ref"):
        if not _present(data.get(key)):
            errors.append(f"{key}_required")
    if _present(data.get("tested_at")) and not _iso(data.get("tested_at")):
        errors.append("tested_at_iso_required")
    elif _present(data.get("tested_at")) and not _fresh_iso(data.get("tested_at"), now=now, max_age_days=ERROR_TRACKING_MAX_AGE_DAYS):
        errors.append(f"tested_at_stale:>{ERROR_TRACKING_MAX_AGE_DAYS}d")
    if _has_any_secret_text(data.values()):
        errors.append("secret_like_value_detected")
    return _result(not errors, errors)


def validate_external_gate_evidence(evidence: Mapping[str, Any] | None, *, now: datetime | None = None) -> Dict[str, Any]:
    """Validate an external evidence payload without trusting source-control examples."""

    evidence = evidence or {}
    now = now or datetime.now(timezone.utc)
    if not evidence:
        return {
            "legal_review": _result(False, ["evidence_missing"]),
            "backup_restore": _result(False, ["evidence_missing"]),
            "error_tracking": _result(False, ["evidence_missing"]),
        }
    example = _bool(evidence.get("example"))
    return {
        "legal_review": _legal(evidence, example=example),
        "backup_restore": _backup_restore(evidence, example=example, now=now),
        "error_tracking": _error_tracking(evidence, example=example, now=now),
    }
