"""Real-player telemetry reports for balance and beta operations."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import fmean
from typing import Any, Dict, Iterable, List, Optional


LIVE_BALANCE_VERSION = "live-balance-v1"
HUMAN_MATCH_TARGET = 500


def _payload(event: Dict[str, Any]) -> Dict[str, Any]:
    payload = event.get("payload") or {}
    return payload if isinstance(payload, dict) else {}


def _terminal_events(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_match: Dict[str, Dict[str, Any]] = {}
    unkeyed: List[Dict[str, Any]] = []
    priority = {"match_abandoned": 1, "match_finished": 2}
    for event in events:
        if event.get("event_type") not in {"match_finished", "match_abandoned"}:
            continue
        match_id = str(_payload(event).get("match_id") or "").strip()
        if not match_id:
            unkeyed.append(event)
            continue
        existing = by_match.get(match_id)
        if not existing or (priority.get(event.get("event_type"), 0), int(event.get("id", 0) or 0)) >= (
            priority.get(existing.get("event_type"), 0),
            int(existing.get("id", 0) or 0),
        ):
            by_match[match_id] = event
    return list(by_match.values()) + unkeyed


def _rate(part: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return round(part / total, 3)


def _profile_summary(label: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    finished = [event for event in events if event.get("event_type") == "match_finished" and _payload(event).get("is_finished")]
    abandoned = [event for event in events if event.get("event_type") == "match_abandoned"]
    turns = [int(_payload(event).get("turn", 0) or 0) for event in finished]
    durations = [
        int(_payload(event).get("match_duration_ms", 0) or 0)
        for event in finished + abandoned
        if _payload(event).get("match_duration_ms") is not None
    ]
    player_wins = sum(1 for event in finished if _payload(event).get("winner") == "player")
    bot_wins = sum(1 for event in finished if _payload(event).get("winner") == "bot")
    total = len(finished) + len(abandoned)
    flags: List[str] = []
    player_win_rate = _rate(player_wins, len(finished))
    if player_win_rate is not None and player_win_rate > 0.6:
        flags.append("player_win_rate_high")
    if player_win_rate is not None and player_win_rate < 0.4:
        flags.append("player_win_rate_low")
    average_turns = round(fmean(turns), 2) if turns else None
    if average_turns is not None and average_turns > 24:
        flags.append("long_matches")
    if len(finished) < 30:
        flags.append("low_sample_size")
    return {
        "label": label,
        "matches_started": total,
        "matches_finished": len(finished),
        "matches_abandoned": len(abandoned),
        "player_wins": player_wins,
        "bot_wins": bot_wins,
        "player_win_rate": player_win_rate,
        "bot_win_rate": _rate(bot_wins, len(finished)),
        "abandon_rate": _rate(len(abandoned), total),
        "average_turns": average_turns,
        "average_match_duration_ms": round(fmean(durations), 2) if durations else None,
        "flags": flags,
    }


def live_balance_report(events: Iterable[Dict[str, Any]], *, release_version: Optional[str] = None) -> Dict[str, Any]:
    events = list(events or [])
    terminal = _terminal_events(events)
    profile_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    cohort_counts = Counter()
    card_play_counts = Counter()
    card_dead_counts = Counter()
    deck_counts = Counter()
    evolution_counts = Counter()
    fusion_count = 0
    win_events = 0
    loss_events = 0
    release_counts = Counter()

    for event in events:
        payload = _payload(event)
        release = payload.get("rebirth_release_version") or payload.get("release_version")
        if release:
            release_counts[str(release)] += 1
        cohort = payload.get("cohort") or ("guest" if payload.get("guest") else "account")
        cohort_counts[str(cohort)] += 1
        if event.get("event_type") == "card_played" and payload.get("card_id"):
            card_play_counts[str(payload["card_id"])] += 1
        if event.get("event_type") == "card_dead_in_hand" and payload.get("card_id"):
            card_dead_counts[str(payload["card_id"])] += 1
        if payload.get("player_deck_signature"):
            deck_counts[str(payload["player_deck_signature"])] += 1
        if event.get("event_type") == "card_evolved" and payload.get("card_id"):
            evolution_counts[str(payload["card_id"])] += 1
        if event.get("event_type") == "field_pair_fused":
            fusion_count += 1
        if event.get("event_type") == "match_won":
            win_events += 1
        if event.get("event_type") == "match_lost":
            loss_events += 1

    for event in terminal:
        profile = _payload(event).get("bot_profile_id") or "unknown"
        profile_events[str(profile)].append(event)

    overall = _profile_summary("overall", terminal)
    by_profile = [_profile_summary(profile, items) for profile, items in sorted(profile_events.items())]
    readiness_state = "ready" if overall["matches_finished"] >= HUMAN_MATCH_TARGET else "insufficient_sample"
    flags = list(overall["flags"])
    if readiness_state != "ready":
        flags.append("needs_human_telemetry")
    if not card_play_counts:
        flags.append("needs_card_play_samples")
    return {
        "version": LIVE_BALANCE_VERSION,
        "release_version": release_version,
        "sample_size": len(events),
        "human_match_gate": {
            "state": readiness_state,
            "required_finished_matches": HUMAN_MATCH_TARGET,
            "observed_finished_matches": overall["matches_finished"],
        },
        "overall": overall,
        "by_profile": by_profile,
        "cohorts": dict(sorted(cohort_counts.items())),
        "release_versions": dict(release_counts.most_common(5)),
        "terminal_events": {
            "wins": win_events,
            "losses": loss_events,
        },
        "card_usage": [
            {"card_id": card_id, "plays": count, "dead_in_hand": card_dead_counts.get(card_id, 0)}
            for card_id, count in card_play_counts.most_common(12)
        ],
        "deck_usage": [
            {"deck_signature": signature, "samples": count}
            for signature, count in deck_counts.most_common(12)
        ],
        "evolution_usage": [
            {"card_id": card_id, "count": count}
            for card_id, count in evolution_counts.most_common(12)
        ],
        "fusion_count": fusion_count,
        "flags": flags,
    }


def live_balance_payload(
    repo,
    *,
    limit: int = 5000,
    since: Optional[str] = None,
    release_version: Optional[str] = None,
) -> Dict[str, Any]:
    events = repo.query_telemetry_events(limit=limit, since=since)
    report = live_balance_report(events, release_version=release_version)
    report["since"] = since
    return report
