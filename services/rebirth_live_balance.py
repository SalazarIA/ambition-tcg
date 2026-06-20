"""Real-player telemetry reports for balance and beta operations."""

from __future__ import annotations

from collections import Counter, defaultdict
from math import ceil, isfinite
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


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def _decision_regret(payload: Dict[str, Any]) -> Optional[float]:
    regret = _number(payload.get("regret"))
    if regret is not None:
        return max(0.0, regret)
    chosen_score = _number(payload.get("chosen_score"))
    best_score = _number(payload.get("best_score"))
    if chosen_score is None or best_score is None:
        return None
    return max(0.0, best_score - chosen_score)


def _decision_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    regrets = sorted(
        regret
        for event in events
        if (regret := _decision_regret(_payload(event))) is not None
    )
    elapsed = [
        value
        for event in events
        if (value := _number(_payload(event).get("decision_elapsed_ms"))) is not None and value >= 0
    ]
    suboptimal_count = sum(1 for regret in regrets if regret > 0)
    p95_index = max(0, ceil(len(regrets) * 0.95) - 1) if regrets else None
    return {
        "decision_count": len(events),
        "scored_decision_count": len(regrets),
        "average_regret": round(fmean(regrets), 4) if regrets else None,
        "regret_p95": round(regrets[p95_index], 4) if p95_index is not None else None,
        "max_regret": round(regrets[-1], 4) if regrets else None,
        "suboptimal_decision_count": suboptimal_count,
        "suboptimal_decision_rate": _rate(suboptimal_count, len(regrets)),
        "average_decision_elapsed_ms": round(fmean(elapsed), 2) if elapsed else None,
    }


def _decision_breakdown(
    events: List[Dict[str, Any]],
    *,
    field: str,
    aliases: tuple[str, ...] = (),
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in events:
        payload = _payload(event)
        value = payload.get(field)
        if value is None:
            value = next((payload.get(alias) for alias in aliases if payload.get(alias) is not None), None)
        grouped[str(value or "unknown")].append(event)
    return [
        {field: label, **_decision_summary(items)}
        for label, items in sorted(grouped.items())
    ]


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


def _outcome_count(
    events: List[Dict[str, Any]],
    terminal: List[Dict[str, Any]],
    *,
    event_type: str,
    winner: str,
) -> int:
    terminal_match_ids = {
        str(_payload(event).get("match_id") or "").strip()
        for event in terminal
        if str(_payload(event).get("match_id") or "").strip()
    }
    count = sum(
        1
        for event in terminal
        if event.get("event_type") == "match_finished" and _payload(event).get("winner") == winner
    )
    legacy_match_ids = set()
    for event in events:
        if event.get("event_type") != event_type:
            continue
        match_id = str(_payload(event).get("match_id") or "").strip()
        if match_id:
            if match_id in terminal_match_ids or match_id in legacy_match_ids:
                continue
            legacy_match_ids.add(match_id)
        count += 1
    return count


def live_balance_report(events: Iterable[Dict[str, Any]], *, release_version: Optional[str] = None) -> Dict[str, Any]:
    events = list(events or [])
    terminal = _terminal_events(events)
    decision_events = [event for event in events if event.get("event_type") == "decision_made"]
    profile_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    cohort_counts = Counter()
    card_play_counts = Counter()
    card_dead_counts = Counter()
    deck_counts = Counter()
    evolution_counts = Counter()
    fusion_count = 0
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
    for event in terminal:
        profile = _payload(event).get("bot_profile_id") or "unknown"
        profile_events[str(profile)].append(event)

    overall = _profile_summary("overall", terminal)
    win_events = _outcome_count(events, terminal, event_type="match_won", winner="player")
    loss_events = _outcome_count(events, terminal, event_type="match_lost", winner="bot")
    by_profile = [_profile_summary(profile, items) for profile, items in sorted(profile_events.items())]
    readiness_state = "ready" if overall["matches_finished"] >= HUMAN_MATCH_TARGET else "insufficient_sample"
    flags = list(overall["flags"])
    if readiness_state != "ready":
        flags.append("needs_human_telemetry")
    if not card_play_counts:
        flags.append("needs_card_play_samples")
    decisions = {
        **_decision_summary(decision_events),
        "by_actor": _decision_breakdown(decision_events, field="actor"),
        "by_action_type": _decision_breakdown(decision_events, field="action_type"),
        "by_profile": _decision_breakdown(
            decision_events,
            field="profile",
            aliases=("profile_id", "bot_profile_id"),
        ),
        "by_difficulty": _decision_breakdown(decision_events, field="difficulty"),
    }
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
        "decisions": decisions,
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
    try:
        terminal_events = repo.query_telemetry_events(
            event_types=("match_finished", "match_abandoned"),
            limit=None,
            since=since,
        )
    except TypeError:
        # Compatibility with lightweight repositories that predate event-type
        # filtering. They still receive the original bounded query above.
        terminal_events = []
    if terminal_events:
        by_id = {event.get("id"): event for event in events}
        for event in terminal_events:
            by_id[event.get("id")] = event
        events = sorted(
            by_id.values(),
            key=lambda event: int(event.get("id", 0) or 0),
            reverse=True,
        )
    report = live_balance_report(events, release_version=release_version)
    report["since"] = since
    return report
