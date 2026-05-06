# =========================================================
# Ambitionz Match Rewards V1
# Persists Arena V1 training rewards and match history safely.
# =========================================================

import json
from datetime import datetime, timezone

from models import db, MatchHistory
from game.progression import award_xp, increment_mission


TRAINING_REWARDS = {
    "win": {"xp": 70, "coins": 35},
    "loss": {"xp": 35, "coins": 15},
    "draw": {"xp": 45, "coins": 20},
}


def get_result_for_viewer(match, viewer_key):
    winner = match.get("winner")

    if winner == "draw":
        return "draw"

    if winner == viewer_key:
        return "win"

    return "loss"


def get_training_reward(result):
    return dict(TRAINING_REWARDS.get(result, TRAINING_REWARDS["loss"]))


def match_reward_key(match, viewer_key):
    match_id = str(match.get("id") or match.get("room") or "unknown")
    return f"arena_v1_rewarded_{match_id}_{viewer_key}"


def already_rewarded(match, viewer_key):
    rewarded = match.setdefault("rewarded_viewers", {})
    return bool(rewarded.get(viewer_key))


def mark_rewarded(match, viewer_key, reward_payload):
    rewarded = match.setdefault("rewarded_viewers", {})
    rewarded[viewer_key] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "reward": reward_payload,
    }


def persist_match_history_v1(match, user, viewer_key, result, reward):
    if not user:
        return None

    try:
        opponent_key = "p2" if viewer_key == "p1" else "p1"
        opponent = match.get(opponent_key) or {}

        payload = {
            "schema": "arena_v1_match_history",
            "match_id": match.get("id") or match.get("room"),
            "mode": "training" if match.get("training") else "pvp",
            "viewer_key": viewer_key,
            "result": result,
            "winner": match.get("winner"),
            "round": match.get("round"),
            "reward": reward,
            "events": match.get("events", [])[-12:],
        }

        history = MatchHistory(
            user_id=user.id,
            opponent_name=opponent.get("name") or "Ambitionz Bot",
            result=result.upper(),
            mode="training" if match.get("training") else "pvp",
            summary_json=json.dumps(payload, ensure_ascii=False),
        )

        db.session.add(history)
        return history
    except Exception as error:
        print("MATCH_HISTORY_V1 PERSIST ERROR:", type(error).__name__, error)
        return None


def persist_rewards_for_user(match, user, viewer_key):
    if not user:
        return {
            "available": False,
            "persisted": False,
            "reason": "No user.",
            "xp": 0,
            "coins": 0,
            "result": None,
        }

    if match.get("phase") != "finished":
        return {
            "available": False,
            "persisted": False,
            "reason": "Match not finished.",
            "xp": 0,
            "coins": 0,
            "result": None,
        }

    result = get_result_for_viewer(match, viewer_key)
    reward = get_training_reward(result)

    if already_rewarded(match, viewer_key):
        previous = match.get("rewarded_viewers", {}).get(viewer_key, {}).get("reward", reward)
        return {
            "available": True,
            "persisted": False,
            "already_claimed": True,
            "xp": previous.get("xp", reward["xp"]),
            "coins": previous.get("coins", reward["coins"]),
            "result": result,
            "title": title_for_result(result),
        }

    try:
        user.coins = int(user.coins or 0) + int(reward["coins"])
        award_xp(user, reward["xp"])

        increment_mission(user, "play_1_training", 1)

        if result == "win":
            increment_mission(user, "win_1_training", 1)

        persist_match_history_v1(match, user, viewer_key, result, reward)

        mark_rewarded(match, viewer_key, reward)

        db.session.commit()

        return {
            "available": True,
            "persisted": True,
            "already_claimed": False,
            "xp": reward["xp"],
            "coins": reward["coins"],
            "result": result,
            "title": title_for_result(result),
        }

    except Exception as error:
        db.session.rollback()
        print("MATCH_REWARD_V1 PERSIST ERROR:", type(error).__name__, error)

        return {
            "available": True,
            "persisted": False,
            "error": str(error),
            "xp": reward["xp"],
            "coins": reward["coins"],
            "result": result,
            "title": title_for_result(result),
        }


def preview_reward_for_match(match, viewer_key):
    if match.get("phase") != "finished":
        return {
            "available": False,
            "persisted": False,
            "xp": 0,
            "coins": 0,
            "result": None,
            "title": "Battle in progress",
        }

    result = get_result_for_viewer(match, viewer_key)
    reward = get_training_reward(result)
    already = already_rewarded(match, viewer_key)

    return {
        "available": True,
        "persisted": already,
        "already_claimed": already,
        "xp": reward["xp"],
        "coins": reward["coins"],
        "result": result,
        "title": title_for_result(result),
    }


def title_for_result(result):
    if result == "win":
        return "Victory"

    if result == "draw":
        return "Draw"

    return "Defeat"
