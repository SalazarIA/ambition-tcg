#!/usr/bin/env python3
"""Aggregate real-match telemetry into per-profile pacing/balance stats.

Reads `telemetry_events` written by `record_match_telemetry` and produces a
JSON summary that the balancing pass can act on without re-running
simulations. Pair with `tools/rebirth_gameplay_health.py` (simulation-based)
for "real data vs. expected" reads.

Usage:
    REBIRTH_DATABASE_URL=postgresql://... .venv/bin/python tools/rebirth_telemetry_analyzer.py
    REBIRTH_DB_PATH=instance/database.db .venv/bin/python tools/rebirth_telemetry_analyzer.py --limit 500
    .venv/bin/python tools/rebirth_telemetry_analyzer.py --since 2026-05-01
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_persistence import RebirthRepository


PROFILE_TARGETS = {
    "novice":      {"player_win_rate_min": 0.65, "average_turns_max": 14},
    "defensive":   {"player_win_rate_min": 0.45, "average_turns_max": 20},
    "opportunist": {"player_win_rate_min": 0.40, "average_turns_max": 20},
    "aggressive":  {"player_win_rate_min": 0.35, "average_turns_max": 18},
}

GLOBAL_TARGETS = {
    "average_turns_max": 18,
    "player_win_rate_min": 0.40,
    "player_win_rate_max": 0.60,
    "abandon_rate_max": 0.20,
    "profile_spread_max": 0.30,
}


def _open_repo():
    database_url = os.environ.get("REBIRTH_DATABASE_URL")
    if database_url:
        return RebirthRepository(database_url=database_url)
    db_path = os.environ.get("REBIRTH_DB_PATH") or str(ROOT / "instance" / "database.db")
    return RebirthRepository(db_path=db_path)


def _percentile(values, fraction):
    if not values:
        return None
    sorted_values = sorted(values)
    index = max(0, min(len(sorted_values) - 1, int(round(fraction * (len(sorted_values) - 1)))))
    return sorted_values[index]


def _summarize(label, events):
    finished = [event for event in events if event["payload"].get("is_finished")]
    abandoned = [event for event in events if event["event_type"] == "match_abandoned"]
    turns = [int(event["payload"].get("turn", 0) or 0) for event in finished]
    player_wins = sum(1 for event in finished if event["payload"].get("winner") == "player")
    bot_wins = sum(1 for event in finished if event["payload"].get("winner") == "bot")
    chain_lengths = [int(event["payload"].get("max_chain_length", 0) or 0) for event in finished]
    completed = len(finished)
    abandons = len(abandoned)
    started_total = completed + abandons
    flags = []
    summary = {
        "label": label,
        "matches_started": started_total,
        "matches_finished": completed,
        "matches_abandoned": abandons,
        "player_wins": player_wins,
        "bot_wins": bot_wins,
        "clash_or_other": max(0, completed - player_wins - bot_wins),
        "player_win_rate": round(player_wins / completed, 3) if completed else None,
        "bot_win_rate": round(bot_wins / completed, 3) if completed else None,
        "abandon_rate": round(abandons / started_total, 3) if started_total else None,
        "average_turns": round(statistics.fmean(turns), 2) if turns else None,
        "median_turns": statistics.median(turns) if turns else None,
        "p10_turns": _percentile(turns, 0.10),
        "p90_turns": _percentile(turns, 0.90),
        "max_chain_length_avg": round(statistics.fmean(chain_lengths), 2) if chain_lengths else None,
        "max_chain_length_p90": _percentile(chain_lengths, 0.90),
        "flags": flags,
    }
    return summary


def _flag_profile(summary, profile_id):
    targets = PROFILE_TARGETS.get(profile_id, {})
    flags = summary["flags"]
    win_rate = summary["player_win_rate"]
    if win_rate is not None and "player_win_rate_min" in targets and win_rate < targets["player_win_rate_min"]:
        flags.append("player_win_rate_below_target")
    turns = summary["average_turns"]
    if turns is not None and "average_turns_max" in targets and turns > targets["average_turns_max"]:
        flags.append("average_turns_above_target")
    if summary["matches_finished"] < 8:
        flags.append("low_sample_size")
    return summary


def _flag_global(summary, profile_results):
    flags = summary["flags"]
    if summary["average_turns"] is not None and summary["average_turns"] > GLOBAL_TARGETS["average_turns_max"]:
        flags.append("average_turns_above_target")
    win_rate = summary["player_win_rate"]
    if win_rate is not None:
        if win_rate < GLOBAL_TARGETS["player_win_rate_min"]:
            flags.append("player_win_rate_below_target")
        if win_rate > GLOBAL_TARGETS["player_win_rate_max"]:
            flags.append("player_win_rate_above_target")
    abandon = summary["abandon_rate"]
    if abandon is not None and abandon > GLOBAL_TARGETS["abandon_rate_max"]:
        flags.append("abandon_rate_high")
    profile_win_rates = [item["player_win_rate"] for item in profile_results if item.get("player_win_rate") is not None]
    if len(profile_win_rates) >= 2:
        spread = max(profile_win_rates) - min(profile_win_rates)
        if spread > GLOBAL_TARGETS["profile_spread_max"]:
            flags.append("profile_difficulty_spread_high")
    return summary


def analyze(events, *, exclude_first_duel=True):
    relevant = [
        event
        for event in events
        if event["event_type"] in ("match_finished", "match_abandoned")
    ]
    if exclude_first_duel:
        relevant = [event for event in relevant if not event["payload"].get("first_duel")]

    by_profile = {}
    by_campaign_node = {}
    for event in relevant:
        profile_id = event["payload"].get("bot_profile_id") or "unknown"
        by_profile.setdefault(profile_id, []).append(event)
        campaign_node = event["payload"].get("campaign_node")
        if campaign_node:
            by_campaign_node.setdefault(campaign_node, []).append(event)

    overall = _summarize("overall", relevant)
    profile_results = [_flag_profile(_summarize(profile_id, items), profile_id) for profile_id, items in sorted(by_profile.items())]
    overall = _flag_global(overall, profile_results)

    campaign_results = []
    for node_id, items in sorted(by_campaign_node.items()):
        node_summary = _summarize(node_id, items)
        node_summary["flags"].append("campaign_node")
        campaign_results.append(node_summary)

    return {
        "targets": {
            "global": GLOBAL_TARGETS,
            "per_profile": PROFILE_TARGETS,
        },
        "overall": overall,
        "by_profile": profile_results,
        "by_campaign_node": campaign_results,
        "sample_size": len(relevant),
        "exclude_first_duel": exclude_first_duel,
    }


def main():
    parser = argparse.ArgumentParser(description="Aggregate real-match telemetry by bot profile.")
    parser.add_argument("--limit", type=int, default=None, help="Read at most N events (newest first).")
    parser.add_argument("--since", type=str, default=None, help="ISO timestamp lower bound for created_at.")
    parser.add_argument("--include-first-duel", action="store_true", help="Include first-duel matches in stats.")
    args = parser.parse_args()

    repo = _open_repo()
    events = repo.query_telemetry_events(
        event_types=("match_finished", "match_abandoned"),
        limit=args.limit,
        since=args.since,
    )
    report = analyze(events, exclude_first_duel=not args.include_first_duel)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
