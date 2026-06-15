"""First-session funnel + D1/D7 retention analysis (cohort by user×day).

Audit/Codex gap: the existing telemetry analyzer aggregates by bot_profile, not
by user×day, so D1/D7 retention and the first-session funnel were never
measured. This module is a pure function over telemetry event records, so it is
testable with synthetic data and can run against any export of the events.

Expected event record shape (a superset of build_match_telemetry_payload):

    {
        "user_id": "u1" | None,        # None => guest/anonymous
        "event_type": "match_started" | "match_abandoned" | "card_played" | ...,
        "created_at": "2026-06-15T12:00:00+00:00",  # ISO 8601
        "payload": {                    # event-specific (telemetry payload)
            "match_id": "...",
            "is_finished": bool,
            "winner": "player" | "bot" | None,
            "abandon_turn": int | None,
            "match_duration_ms": int | None,
        },
    }

Completion/win/loss are DERIVED from is_finished + winner, so no change to the
match flow is required to start measuring the funnel.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import median
from typing import Any, Dict, Iterable, List, Optional


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _payload(event: Dict[str, Any]) -> Dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def funnel_summary(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """First-session funnel: starts -> completion, abandons, duration, win/loss."""
    started_matches: set = set()
    finished_matches: set = set()
    started_users: set = set()
    finished_users: set = set()
    abandon_turns: Counter = Counter()
    durations: List[int] = []
    winners: Counter = Counter()

    for event in events:
        etype = event.get("event_type")
        payload = _payload(event)
        user = event.get("user_id") or f"guest:{payload.get('match_id')}"
        match_id = payload.get("match_id")
        if etype == "match_started" and match_id:
            started_matches.add(match_id)
            started_users.add(user)
        if payload.get("is_finished") and match_id:
            finished_matches.add(match_id)
            finished_users.add(user)
            winner = payload.get("winner")
            if winner:
                winners[winner] += 1
            if isinstance(payload.get("match_duration_ms"), int):
                durations.append(int(payload["match_duration_ms"]))
        if etype == "match_abandoned":
            turn = payload.get("abandon_turn")
            if isinstance(turn, int):
                abandon_turns[turn] += 1

    started = len(started_matches)
    finished = len(finished_matches)
    return {
        "matches_started": started,
        "matches_finished": finished,
        "match_completion_rate": round(finished / started, 3) if started else 0.0,
        "first_match_completion_rate": round(len(finished_users) / len(started_users), 3) if started_users else 0.0,
        "abandons": sum(abandon_turns.values()),
        "abandon_by_turn": dict(sorted(abandon_turns.items())),
        "median_duration_ms": int(median(durations)) if durations else None,
        "wins_player": winners.get("player", 0),
        "wins_bot": winners.get("bot", 0),
    }


def retention_cohorts(events: Iterable[Dict[str, Any]], *, reference: Optional[datetime] = None) -> Dict[str, Any]:
    """D1/D7 retention keyed by each signed-in user's first-seen day."""
    active_days: Dict[str, set] = defaultdict(set)
    for event in events:
        user = event.get("user_id")
        if not user:  # retention is only meaningful for identified accounts
            continue
        stamp = _parse_dt(event.get("created_at"))
        if stamp is None:
            continue
        active_days[user].add(stamp.date())

    cohorts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"users": 0, "d1": 0, "d7": 0})
    for user, days in active_days.items():
        signup = min(days)
        bucket = cohorts[signup.isoformat()]
        bucket["users"] += 1
        deltas = {(day - signup).days for day in days}
        if 1 in deltas:
            bucket["d1"] += 1
        if 7 in deltas:
            bucket["d7"] += 1

    total_users = sum(c["users"] for c in cohorts.values())
    total_d1 = sum(c["d1"] for c in cohorts.values())
    total_d7 = sum(c["d7"] for c in cohorts.values())
    return {
        "tracked_users": total_users,
        "d1_retention": round(total_d1 / total_users, 3) if total_users else 0.0,
        "d7_retention": round(total_d7 / total_users, 3) if total_users else 0.0,
        "cohorts": {day: dict(metrics) for day, metrics in sorted(cohorts.items())},
    }


def build_report(events: List[Dict[str, Any]], *, reference: Optional[datetime] = None) -> Dict[str, Any]:
    events = list(events)
    return {
        "events_analyzed": len(events),
        "funnel": funnel_summary(events),
        "retention": retention_cohorts(events, reference=reference),
    }
