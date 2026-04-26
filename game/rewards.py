from game.balance import (
    PVE_LOSS_XP,
    PVE_WIN_COINS,
    PVE_WIN_XP,
    PVP_LOSS_XP,
    PVP_WIN_COINS,
    PVP_WIN_XP,
)


def get_match_rewards(is_bot_match, did_win):
    if is_bot_match:
        if did_win:
            return {
                "coins": PVE_WIN_COINS,
                "xp": PVE_WIN_XP,
            }

        return {
            "coins": 0,
            "xp": PVE_LOSS_XP,
        }

    if did_win:
        return {
            "coins": PVP_WIN_COINS,
            "xp": PVP_WIN_XP,
        }

    return {
        "coins": 0,
        "xp": PVP_LOSS_XP,
    }


def apply_match_rewards(user, is_bot_match, did_win, award_xp_function):
    if not user:
        return {
            "coins": 0,
            "xp": 0,
        }

    rewards = get_match_rewards(is_bot_match, did_win)

    user.coins += rewards["coins"]
    award_xp_function(user, rewards["xp"])

    return rewards
