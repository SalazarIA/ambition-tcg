"""Defensive JSONL match history for Ascension Duel."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


HISTORY_FILENAME = "ascension_history.jsonl"


def history_path(base_path):
    path = Path(base_path or ".")
    path.mkdir(parents=True, exist_ok=True)
    return path / HISTORY_FILENAME


def decisive_card_for_match(match, perspective="player"):
    side_state = match.get(perspective, {})
    for action in reversed(side_state.get("last_actions") or []):
        if action.get("card_id"):
            return action.get("card_id")
    for event in reversed(match.get("chronicle") or []):
        payload = event.get("payload") or {}
        if payload.get("card"):
            return payload.get("card")
    active = side_state.get("active_champion") or {}
    return active.get("id") or "ambition_core"


def build_history_record(match, reward=None, perspective="player"):
    side_state = match.get(perspective, {})
    opponent = match.get("opponent" if perspective == "player" else "player", {})
    winner = match.get("winner")
    result = "DRAW" if winner == "draw" else "WIN" if winner == perspective else "LOSS"
    champion = side_state.get("active_champion") or {}
    return {
        "match_id": match.get("id"),
        "version": match.get("version"),
        "result": result,
        "winner": winner,
        "rounds": match.get("round", 0),
        "champion": champion.get("name") or "Unclaimed Champion",
        "champion_id": champion.get("id"),
        "opponent": opponent.get("name") or "Rival",
        "bot_profile": match.get("bot_profile", "Controller"),
        "decisive_card": decisive_card_for_match(match, perspective=perspective),
        "reward": reward or match.get("ascension_reward") or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def append_history_record(base_path, record):
    path = history_path(base_path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
    return record


def read_history_records(base_path, limit=25):
    path = history_path(base_path)
    if not path.exists():
        return []

    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    records.reverse()
    return records[:limit]
