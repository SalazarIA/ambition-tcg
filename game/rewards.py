from services.reward_tuning import calculate_reward


def get_match_rewards(is_bot_match, did_win, difficulty=None, result=None):
    mode = "training" if is_bot_match else "pvp"
    outcome = result or ("win" if did_win else "loss")
    return calculate_reward(mode, outcome, difficulty)


def apply_match_rewards(user, is_bot_match, did_win, award_xp_function, difficulty=None, result=None):
    if not user:
        return {
            "coins": 0,
            "xp": 0,
        }

    rewards = get_match_rewards(is_bot_match, did_win, difficulty=difficulty, result=result)

    user.coins += rewards["coins"]
    award_xp_function(user, rewards["xp"])

    return rewards


# =========================================================
# AMBITIONZ V1.05 — REWARD BASELINE
# =========================================================

V105_REWARD_BASELINE = {
    "pvp_win": {"coins": 80, "xp": 120},
    "pvp_loss": {"coins": 25, "xp": 45},
    "pvp_draw": {"coins": 40, "xp": 70},
    "training_win": {"coins": 35, "xp": 70},
    "training_loss": {"coins": 15, "xp": 35},
    "training_draw": {"coins": 20, "xp": 45},
}
