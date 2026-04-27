from models import db, MatchTelemetry


def safe_player_user_id(player):
    try:
        value = player.get("user_id")
        return int(value) if value is not None else None
    except Exception:
        return None


def safe_player_name(player):
    return str(player.get("name", "Unknown"))


def safe_player_hp(player):
    try:
        return int(player.get("hp", 0) or 0)
    except Exception:
        return 0


def record_match_telemetry(room_id, match, winner_key, loser_key, ending_reason="completed"):
    try:
        winner = match.get(winner_key, {})
        loser = match.get(loser_key, {})

        telemetry = MatchTelemetry(
            room_id=room_id,
            mode="training" if match.get("training") else "pvp",
            winner_user_id=safe_player_user_id(winner),
            loser_user_id=safe_player_user_id(loser),
            winner_name=safe_player_name(winner),
            loser_name=safe_player_name(loser),
            rounds=int(match.get("round", 0) or 0),
            winner_hp=safe_player_hp(winner),
            loser_hp=safe_player_hp(loser),
            bot_difficulty=match.get("bot_difficulty"),
            ending_reason=ending_reason,
        )

        db.session.add(telemetry)
        db.session.commit()

        print(
            "MATCH TELEMETRY RECORDED:",
            telemetry.id,
            telemetry.mode,
            telemetry.winner_name,
            "over",
            telemetry.loser_name,
        )

        return telemetry

    except Exception as error:
        print("MATCH TELEMETRY ERROR:", type(error).__name__, error)
        db.session.rollback()
        return None
