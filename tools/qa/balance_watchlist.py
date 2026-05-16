#!/usr/bin/env python3
"""Generate a public beta balance watchlist from local telemetry and BE2 sims."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.qa.battle_balance_sim import run_simulation  # noqa: E402


WATCH_EVENTS = {
    "finish_match",
    "start_training",
    "buy_booster",
    "open_booster",
    "visit_home",
    "view_collection",
    "view_roadmap",
    "claim_daily",
    "save_deck",
}


def _json_loads(value: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def load_db_events(limit: int = 5000) -> Tuple[List[Dict[str, Any]], str]:
    try:
        from app import app
        from models import RetentionEvent

        with app.app_context():
            rows = (
                RetentionEvent.query
                .order_by(RetentionEvent.id.desc())
                .limit(limit)
                .all()
            )
            events = []
            for row in rows:
                events.append({
                    "event": row.event_key,
                    "page": row.page or "",
                    "metadata": _json_loads(row.metadata_json or "{}"),
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                    "source": "db",
                })
            return events, ""
    except Exception as error:
        return [], f"{type(error).__name__}: {error}"


def load_jsonl_events() -> Tuple[List[Dict[str, Any]], str]:
    events: List[Dict[str, Any]] = []
    checked = []
    for path in [
        ROOT / "instance" / "beta_telemetry.jsonl",
        ROOT / "logs" / "beta_telemetry.jsonl",
    ]:
        checked.append(str(path.relative_to(ROOT)))
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    events.append({
                        "event": parsed.get("event") or parsed.get("event_key") or "",
                        "page": parsed.get("page") or "",
                        "metadata": parsed.get("metadata") if isinstance(parsed.get("metadata"), dict) else {},
                        "created_at": parsed.get("recorded_at") or parsed.get("created_at") or "",
                        "source": "jsonl",
                    })
        except Exception as error:
            return events, f"{path}: {type(error).__name__}: {error}"
    return events, "checked " + ", ".join(checked)


def summarize_events(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    event_counts = Counter()
    intent_counts = Counter()
    card_counts = Counter()
    difficulty_counts = Counter()

    for event in events:
        name = str(event.get("event") or "")
        if name:
            event_counts[name] += 1
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}

        for key in ("intent", "player_intent", "bot_intent"):
            if metadata.get(key):
                intent_counts[str(metadata[key])] += 1
        for key in ("card", "card_id", "played_card"):
            if metadata.get(key):
                card_counts[str(metadata[key])] += 1
        if metadata.get("difficulty"):
            difficulty_counts[str(metadata["difficulty"])] += 1

    watched = {key: event_counts.get(key, 0) for key in sorted(WATCH_EVENTS)}
    return {
        "total_events": sum(event_counts.values()),
        "event_counts": dict(event_counts.most_common(20)),
        "watched_events": watched,
        "intent_counts": dict(intent_counts.most_common(10)),
        "card_counts": dict(card_counts.most_common(10)),
        "difficulty_counts": dict(difficulty_counts.most_common(10)),
    }


def build_alerts(sim_metrics: Dict[str, Any], event_summary: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    win_rate = float(sim_metrics.get("win_rate") or 0)
    average_rounds = float(sim_metrics.get("average_rounds") or 0)
    timeout_count = int(sim_metrics.get("timeout_count") or 0)

    if win_rate < 0.35:
        alerts.append("Player win rate is below 35%; watch early pressure and bot aggression.")
    elif win_rate > 0.65:
        alerts.append("Player win rate is above 65%; watch bot survival and card pressure.")

    if average_rounds > 20:
        alerts.append("Average match length is high; watch for stalled board states.")

    if timeout_count > 0:
        alerts.append("Timeouts were detected in simulation and should be investigated before public beta.")

    watched = event_summary.get("watched_events") or {}
    if not any(watched.values()):
        alerts.append("No live beta telemetry events found yet; using simulation as the primary signal.")

    intent_counts = event_summary.get("intent_counts") or {}
    total_intents = sum(intent_counts.values())
    if total_intents:
        top_intent, top_count = max(intent_counts.items(), key=lambda item: item[1])
        if top_count / max(1, total_intents) > 0.75:
            alerts.append(f"Intent variety may be narrow in telemetry: {top_intent} is over 75% of tracked intent events.")

    return alerts or ["No balance blocker detected from local signals."]


def markdown_report(sim_metrics: Dict[str, Any], event_summary: Dict[str, Any], alerts: List[str], db_note: str, jsonl_note: str) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    top_cards = sim_metrics.get("top_cards_played") or []
    intent_counts = sim_metrics.get("intent_counts") or {}

    lines = [
        "# Ambitionz Beta Balance Watchlist",
        "",
        f"Generated: {generated}",
        "",
        "## Simulation Snapshot",
        "",
        f"- total_matches: {sim_metrics.get('total_matches')}",
        f"- player_wins: {sim_metrics.get('player_wins')}",
        f"- bot_wins: {sim_metrics.get('bot_wins')}",
        f"- win_rate: {sim_metrics.get('win_rate')}",
        f"- average_rounds: {sim_metrics.get('average_rounds')}",
        f"- timeout_count: {sim_metrics.get('timeout_count')}",
        f"- integrity_error_count: {sim_metrics.get('integrity_error_count')}",
        "",
        "## Intent Signals",
        "",
    ]

    if intent_counts:
        for key, value in sorted(intent_counts.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No intent signal found.")

    lines.extend(["", "## Top Cards Played", ""])
    if top_cards:
        for card_id, count in top_cards[:10]:
            lines.append(f"- {card_id}: {count}")
    else:
        lines.append("- No card play signal found.")

    lines.extend(["", "## Local Telemetry", ""])
    lines.append(f"- total_events: {event_summary.get('total_events')}")
    lines.append(f"- db_source: {db_note or 'ok'}")
    lines.append(f"- jsonl_source: {jsonl_note or 'ok'}")

    for key, count in (event_summary.get("watched_events") or {}).items():
        lines.append(f"- {key}: {count}")

    lines.extend(["", "## Alerts", ""])
    for alert in alerts:
        lines.append(f"- {alert}")

    lines.extend([
        "",
        "## Notes",
        "",
        "- This watchlist is local and defensive; it does not require an external analytics provider.",
        "- RC V6 includes Intent Balance V2: Strike is leaner, Guard absorbs more damage and Focus generates clearer Ambition value.",
        "- Confirm post-deploy telemetry before declaring Strike usage fixed; local historical events may still overrepresent old behavior.",
        "- Gold, boosters and rewards are internal beta systems with no real-money payment flow.",
        "- Use this file to decide what to inspect before changing card balance or bot behavior.",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Ambitionz beta balance watchlist.")
    parser.add_argument("--matches", type=int, default=100)
    parser.add_argument("--seed", type=int, default=99104)
    parser.add_argument("--max-rounds", type=int, default=30)
    parser.add_argument("--output", default="docs/BALANCE_WATCHLIST.md")
    args = parser.parse_args()

    db_events, db_note = load_db_events()
    jsonl_events, jsonl_note = load_jsonl_events()
    events = db_events + jsonl_events
    event_summary = summarize_events(events)
    sim_metrics = run_simulation(max(1, args.matches), args.seed, max(1, args.max_rounds))
    alerts = build_alerts(sim_metrics, event_summary)

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown_report(sim_metrics, event_summary, alerts, db_note, jsonl_note), encoding="utf-8")

    print("=== Ambitionz Beta Balance Watchlist ===")
    print(f"report: {output_path.relative_to(ROOT)}")
    print(f"total_matches: {sim_metrics.get('total_matches')}")
    print(f"win_rate: {sim_metrics.get('win_rate')}")
    print(f"average_rounds: {sim_metrics.get('average_rounds')}")
    print(f"timeout_count: {sim_metrics.get('timeout_count')}")
    print(f"telemetry_events: {event_summary.get('total_events')}")
    for alert in alerts:
        print(f"alert: {alert}")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
