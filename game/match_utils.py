def is_bot_player(player):
    return bool(player and player.get("is_bot"))


def safe_user_id(player):
    if is_bot_player(player):
        return None

    user_id = player.get("user_id")

    if user_id is None:
        return None

    try:
        user_id = int(user_id)
    except Exception:
        return None

    if user_id <= 0:
        return None

    return user_id


def player_display_name(player):
    if not player:
        return "Unknown"

    return player.get("name", "Unknown")


def get_match_result_label(winner_key):
    if winner_key == "DRAW":
        return "DRAW"

    if winner_key in ["p1", "p2"]:
        return "FINISHED"

    return "UNKNOWN"
