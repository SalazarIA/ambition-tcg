#!/usr/bin/env python3
"""Run deterministic bot-vs-bot pacing checks for Rebirth product health."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_balance import simulate_balance


def health_report(matches: int = 60):
    simulation = simulate_balance(matches=matches)
    summary = simulation["summary"]
    problem_cards = [
        {
            "card_id": card["card_id"],
            "name": card["name"],
            "plays": card["plays"],
            "win_rate": card["win_rate"],
            "flags": card["flags"],
        }
        for card in simulation["card_stats"]
        if card["flags"] and card["flags"] != ["unused"]
    ]
    risks = []
    if summary["stalemate_frequency"] > 0.15:
        risks.append("stalemate_frequency_high")
    average_turns_max = 24
    max_chain_events = 15
    profile_spread_max = 0.35
    if summary["average_turns"] > average_turns_max:
        risks.append("match_duration_high")
    if max(summary["player_win_rate"], summary["bot_win_rate"]) > 0.7:
        risks.append("outcome_dominance_high")
    if summary["dead_turn_rate"] > 0.22:
        risks.append("dead_turn_rate_high")
    if summary["trigger_events_per_turn"] > 4:
        risks.append("trigger_density_high")
    if summary["max_chain_events"] > max_chain_events:
        risks.append("chain_readability_risk")
    profile_rates = [float(item.get("player_win_rate", 0) or 0) for item in simulation["profile_results"]]
    if profile_rates and max(profile_rates) - min(profile_rates) > profile_spread_max:
        risks.append("bot_profile_difficulty_spread_high")
    quality_score = 100 if not risks else max(0, 100 - 25 * len(risks))
    if not risks:
        risks.append("no_critical_pacing_flag")
    return {
        "matches": simulation["matches"],
        "targets": {
            "average_turns_max": average_turns_max,
            "profile_win_rate_spread_max": profile_spread_max,
            "max_chain_events": max_chain_events,
        },
        "quality_score": quality_score,
        "match_quality_metrics": summary,
        "problem_cards": problem_cards[:12],
        "top_ability_events": simulation["top_ability_events"],
        "profile_results": simulation["profile_results"],
        "health_flags": risks,
    }


def main():
    matches = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    print(json.dumps(health_report(matches=matches), indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
