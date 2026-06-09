"""Public beta KPI gates derived from Rebirth telemetry."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from services.rebirth_live_balance import HUMAN_MATCH_TARGET, live_balance_report


PUBLIC_BETA_GATE_VERSION = "public-beta-gate-v1"
PUBLIC_BETA_TARGETS = {
    "tutorial_completion_min": 0.80,
    "first_match_completion_min": 0.70,
    "d1_retention_min": 0.35,
    "d7_retention_min": 0.20,
    "crash_rate_max": 0.01,
    "crash_rate_min_events": 100,
    "human_finished_matches_min": HUMAN_MATCH_TARGET,
}
REQUIRED_TELEMETRY_EVENTS = (
    "match_started",
    "match_finished",
    "match_abandoned",
    "match_won",
    "match_lost",
    "card_played",
    "card_evolved",
    "field_pair_fused",
)
ERROR_EVENTS = {"client_error", "server_error"}
CRITICAL_BALANCE_FLAGS = {
    "player_win_rate_high",
    "player_win_rate_low",
    "long_matches",
    "abandon_rate_high",
    "average_turns_above_target",
    "player_win_rate_below_target",
    "player_win_rate_above_target",
    "profile_difficulty_spread_high",
}


def _cohort_window_gate(since: Optional[str]) -> Dict[str, Any]:
    value = str(since or "").strip()
    return {
        "key": "cohort_window",
        "label": "Coorte",
        "state": "passed" if value else "blocked",
        "value": value or "sem janela",
        "target": "--since <cohort-start-iso>",
    }


def _payload(event: Dict[str, Any]) -> Dict[str, Any]:
    payload = event.get("payload") or {}
    return payload if isinstance(payload, dict) else {}


def _parse_time(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _now_from_events(events: Sequence[Dict[str, Any]], now: Optional[datetime]) -> datetime:
    if now is not None:
        return _parse_time(now) or datetime.now(timezone.utc)
    observed = [_parse_time(event.get("created_at")) for event in events]
    observed = [item for item in observed if item is not None]
    return max(observed) if observed else datetime.now(timezone.utc)


def _rate(part: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return round(part / total, 3)


def _state_for_min_rate(rate: Optional[float], target: float) -> str:
    if rate is None:
        return "pending"
    return "passed" if rate >= target else "blocked"


def _state_for_max_rate(rate: Optional[float], target: float) -> str:
    if rate is None:
        return "pending"
    return "passed" if rate <= target else "blocked"


def _display_rate(rate: Optional[float]) -> str:
    if rate is None:
        return "sem amostra"
    return f"{round(rate * 100)}%"


def _match_ids(events: Sequence[Dict[str, Any]], event_type: str, *, first_duel: bool = False) -> Set[str]:
    ids: Set[str] = set()
    for event in events:
        if event.get("event_type") != event_type:
            continue
        payload = _payload(event)
        if first_duel and not payload.get("first_duel"):
            continue
        match_id = str(payload.get("match_id") or "").strip()
        if match_id:
            ids.add(match_id)
        else:
            ids.add(f"event:{event.get('id')}")
    return ids


def _tutorial_gate(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    started_users = {
        int(event["user_id"])
        for event in events
        if event.get("user_id") is not None
        and event.get("event_type") in {"tutorial_step_viewed", "tutorial_step_completed"}
    }
    completed_users = {
        int(event["user_id"])
        for event in events
        if event.get("user_id") is not None
        and event.get("event_type") == "tutorial_step_completed"
        and int(_payload(event).get("step", 0) or 0) >= 4
    }
    started_users |= completed_users
    rate = _rate(len(completed_users), len(started_users))
    return {
        "key": "tutorial_completion",
        "label": "Tutorial",
        "state": _state_for_min_rate(rate, PUBLIC_BETA_TARGETS["tutorial_completion_min"]),
        "value": _display_rate(rate),
        "target": ">=80%",
        "rate": rate,
        "started_users": len(started_users),
        "completed_users": len(completed_users),
    }


def _first_match_gate(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    started = _match_ids(events, "match_started", first_duel=True)
    finished = _match_ids(events, "match_finished", first_duel=True)
    completed = finished & started if started else set()
    rate = _rate(len(completed), len(started))
    return {
        "key": "first_match_completion",
        "label": "1a partida",
        "state": _state_for_min_rate(rate, PUBLIC_BETA_TARGETS["first_match_completion_min"]),
        "value": _display_rate(rate),
        "target": ">=70%",
        "rate": rate,
        "started_matches": len(started),
        "finished_matches": len(completed),
    }


def _retention_gate(events: Sequence[Dict[str, Any]], *, days: int, target: float, now: datetime) -> Dict[str, Any]:
    by_user: Dict[int, List[datetime]] = defaultdict(list)
    for event in events:
        if event.get("user_id") is None:
            continue
        created_at = _parse_time(event.get("created_at"))
        if created_at is not None:
            by_user[int(event["user_id"])].append(created_at)

    eligible = 0
    retained = 0
    for timestamps in by_user.values():
        ordered = sorted(timestamps)
        if not ordered:
            continue
        first_seen = ordered[0]
        target_time = first_seen + timedelta(days=days)
        if now < target_time:
            continue
        eligible += 1
        if any(item >= target_time for item in ordered[1:]):
            retained += 1

    rate = _rate(retained, eligible)
    return {
        "key": f"d{days}_retention",
        "label": f"D{days}",
        "state": _state_for_min_rate(rate, target),
        "value": _display_rate(rate),
        "target": f">={round(target * 100)}%",
        "rate": rate,
        "eligible_users": eligible,
        "retained_users": retained,
    }


def _crash_gate(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    errors = sum(1 for event in events if event.get("event_type") in ERROR_EVENTS)
    total = len(events)
    rate = _rate(errors, total)
    state = _state_for_max_rate(rate, PUBLIC_BETA_TARGETS["crash_rate_max"])
    if total < PUBLIC_BETA_TARGETS["crash_rate_min_events"]:
        state = "pending"
    return {
        "key": "crash_rate",
        "label": "Crash/Error",
        "state": state,
        "value": _display_rate(rate),
        "target": "<=1%",
        "rate": rate,
        "error_events": errors,
        "sample_size": total,
        "minimum_events": PUBLIC_BETA_TARGETS["crash_rate_min_events"],
    }


def _telemetry_gate(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    observed = {str(event.get("event_type") or "").strip().lower() for event in events}
    missing = [event_type for event_type in REQUIRED_TELEMETRY_EVENTS if event_type not in observed]
    state = "passed" if events and not missing else "pending" if not events else "blocked"
    return {
        "key": "telemetry_active",
        "label": "Telemetria",
        "state": state,
        "value": "ativa" if state == "passed" else "incompleta",
        "target": "eventos obrigatorios",
        "observed_events": sorted(observed),
        "missing_events": missing,
    }


def _human_match_gate(live_balance: Dict[str, Any]) -> Dict[str, Any]:
    human_gate = live_balance.get("human_match_gate") or {}
    observed = int(human_gate.get("observed_finished_matches", 0) or 0)
    required = int(human_gate.get("required_finished_matches", HUMAN_MATCH_TARGET) or HUMAN_MATCH_TARGET)
    state = "passed" if observed >= required else "blocked"
    return {
        "key": "human_telemetry_sample",
        "label": "Partidas humanas",
        "state": state,
        "value": f"{observed}/{required}",
        "target": f">={required}",
        "observed_finished_matches": observed,
        "required_finished_matches": required,
    }


def _balance_gate(live_balance: Dict[str, Any]) -> Dict[str, Any]:
    human_gate = live_balance.get("human_match_gate") or {}
    observed = int(human_gate.get("observed_finished_matches", 0) or 0)
    required = int(human_gate.get("required_finished_matches", HUMAN_MATCH_TARGET) or HUMAN_MATCH_TARGET)
    flags = list(live_balance.get("flags") or [])
    critical_flags = [flag for flag in flags if flag in CRITICAL_BALANCE_FLAGS]
    if observed < required:
        state = "blocked"
        value = "sem amostra"
    elif critical_flags:
        state = "blocked"
        value = "ajustar"
    else:
        state = "passed"
        value = "saudavel"
    return {
        "key": "healthy_balance",
        "label": "Balance",
        "state": state,
        "value": value,
        "target": "sem flags criticas",
        "flags": flags,
        "critical_flags": critical_flags,
    }


def public_beta_gate_report(
    events: Iterable[Dict[str, Any]],
    *,
    live_balance: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
    release_version: Optional[str] = None,
    since: Optional[str] = None,
) -> Dict[str, Any]:
    events = list(events or [])
    observed_now = _now_from_events(events, now)
    live_balance = live_balance or live_balance_report(events, release_version=release_version)
    checks = [
        _cohort_window_gate(since),
        _telemetry_gate(events),
        _human_match_gate(live_balance),
        _tutorial_gate(events),
        _first_match_gate(events),
        _retention_gate(events, days=1, target=PUBLIC_BETA_TARGETS["d1_retention_min"], now=observed_now),
        _retention_gate(events, days=7, target=PUBLIC_BETA_TARGETS["d7_retention_min"], now=observed_now),
        _crash_gate(events),
        _balance_gate(live_balance),
    ]
    blockers = [check["key"] for check in checks if check["state"] != "passed"]
    return {
        "version": PUBLIC_BETA_GATE_VERSION,
        "release_version": release_version,
        "since": since,
        "updated_at": observed_now.isoformat(timespec="seconds"),
        "ready": not blockers,
        "targets": PUBLIC_BETA_TARGETS,
        "checks": checks,
        "blockers": blockers,
        "sample_size": len(events),
    }


def public_beta_gate_payload(
    repo,
    *,
    limit: int = 5000,
    since: Optional[str] = None,
    release_version: Optional[str] = None,
    live_balance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    events = repo.query_telemetry_events(limit=limit, since=since)
    return public_beta_gate_report(
        events,
        live_balance=live_balance,
        release_version=release_version,
        since=since,
    )
