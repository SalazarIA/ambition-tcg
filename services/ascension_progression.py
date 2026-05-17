"""Ascension Duel rewards and progression compatibility helpers."""

from __future__ import annotations

from services.ascension_taxonomy import card_strategy_role


def _result_for(match, perspective="player"):
    winner = match.get("winner")
    return "DRAW" if winner == "draw" else "WIN" if winner == perspective else "LOSS"


def build_ascension_result_summary(match, perspective="player"):
    winner = match.get("winner")
    result = _result_for(match, perspective=perspective)
    player = match.get(perspective, {})
    opponent = match.get("opponent" if perspective == "player" else "player", {})
    return {
        "mode": "ascension_duel",
        "architecture": match.get("version", "ascension_duel_v1"),
        "result": result,
        "winner": winner,
        "rounds": match.get("round", 0),
        "hp": player.get("hp", 0),
        "opponent_hp": opponent.get("hp", 0),
        "ambition": player.get("ambition", 0),
        "domination_marks": player.get("domination_marks", 0),
    }


def build_ascension_rewards(match, perspective="player"):
    """Return deterministic post-match rewards for Ascension Duel."""

    if not match:
        return {
            "xp": 0,
            "gold": 0,
            "champion_progress": {"champion": "Unclaimed Champion", "amount": 0, "total": 0},
            "unlock_progress": {"target": "First Ascension Cache", "amount": 0, "total": 100},
            "unlock": None,
            "summary": "No duel result was recorded.",
        }

    result = _result_for(match, perspective=perspective)
    player = match.get(perspective, {})
    champion = player.get("active_champion") or {}
    rounds = int(match.get("round") or 0)
    ambition = int(player.get("ambition") or 0)
    ascended = bool(player.get("ascended"))
    dominated = any(event.get("type") == "domination_success" and event.get("side") == perspective for event in match.get("chronicle") or [])

    base_xp = 24 + min(18, rounds * 2)
    base_gold = 18 + min(20, rounds)
    if result == "WIN":
        base_xp += 28
        base_gold += 24
    elif result == "DRAW":
        base_xp += 12
        base_gold += 8

    if ascended:
        base_xp += 10
    if dominated:
        base_xp += 14
        base_gold += 8

    champion_progress = 8 + (8 if result == "WIN" else 3) + (4 if ascended else 0)
    unlock_progress = min(100, 12 + base_xp // 3 + ambition)
    unlock = None
    if result == "WIN" and (ascended or dominated or unlock_progress >= 35):
        unlock = {
            "id": "first_ascension_cache",
            "name": "First Ascension Cache",
            "state": "progressed",
        }

    champion_name = champion.get("name") or "Unclaimed Champion"
    role = card_strategy_role(champion) if champion else "Unclaimed Champion"
    return {
        "xp": base_xp,
        "gold": base_gold,
        "champion_progress": {
            "champion": champion_name,
            "role": role,
            "amount": champion_progress,
            "total": min(100, champion_progress),
        },
        "unlock_progress": {
            "target": "First Ascension Cache",
            "amount": unlock_progress,
            "total": 100,
        },
        "unlock": unlock,
        "summary": f"{result.title()} recorded after {rounds} rounds. {champion_name} gained {champion_progress} Champion progress.",
    }


def progression_event_from_match(match, perspective="player"):
    summary = build_ascension_result_summary(match, perspective=perspective)
    rewards = build_ascension_rewards(match, perspective=perspective)
    return {
        "event_key": "training_result_view",
        "page": "/training",
        "metadata": {
            "mode": summary["mode"],
            "result": summary["result"],
            "rounds": summary["rounds"],
            "architecture": summary["architecture"],
            "xp": rewards["xp"],
            "gold": rewards["gold"],
        },
    }
