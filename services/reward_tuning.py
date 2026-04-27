# Ambitionz V1.05 reward tuning baseline.
# This file centralizes expected reward values for reports and future migration.
# It intentionally does not force reward mutation unless called explicitly.

REWARD_TABLE = {
    "pvp": {
        "win": {"coins": 80, "xp": 120},
        "loss": {"coins": 25, "xp": 45},
        "draw": {"coins": 40, "xp": 70},
    },
    "training": {
        "win": {"coins": 35, "xp": 70},
        "loss": {"coins": 15, "xp": 35},
        "draw": {"coins": 20, "xp": 45},
    },
}

DIFFICULTY_MULTIPLIER = {
    "easy": 0.85,
    "normal": 1.0,
    "hard": 1.25,
}


def calculate_reward(mode="pvp", result="win", difficulty=None):
    mode = "training" if mode == "training" else "pvp"
    result = result if result in {"win", "loss", "draw"} else "loss"

    base = REWARD_TABLE[mode][result].copy()

    if mode == "training":
        multiplier = DIFFICULTY_MULTIPLIER.get(difficulty or "normal", 1.0)
        base["coins"] = int(round(base["coins"] * multiplier))
        base["xp"] = int(round(base["xp"] * multiplier))

    return base


def reward_line(player_name, mode, result, difficulty=None):
    reward = calculate_reward(mode, result, difficulty)
    return f"{player_name} reward baseline: +{reward['coins']} coins / +{reward['xp']} XP."
