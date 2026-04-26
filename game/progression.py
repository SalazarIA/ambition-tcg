from datetime import datetime, timezone

from models import UserMission, db


MISSION_DEFINITIONS = [
    {
        "key": "play_1_match",
        "title": "Enter the Arena",
        "description": "Play 1 match.",
        "target": 1,
        "xp_reward": 40,
        "coin_reward": 80,
    },
    {
        "key": "play_3_matches",
        "title": "Arena Routine",
        "description": "Play 3 matches.",
        "target": 3,
        "xp_reward": 100,
        "coin_reward": 180,
    },
    {
        "key": "win_1_match",
        "title": "First Victory",
        "description": "Win 1 match.",
        "target": 1,
        "xp_reward": 120,
        "coin_reward": 220,
    },
    {
        "key": "open_1_booster",
        "title": "Open the Vault",
        "description": "Open 1 booster.",
        "target": 1,
        "xp_reward": 60,
        "coin_reward": 60,
    },
]


def today_key():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def xp_needed_for_level(level):
    return max(100, int(level) * 100)


def normalize_user_level(user):
    leveled = False

    while int(user.xp or 0) >= xp_needed_for_level(user.level):
        user.xp -= xp_needed_for_level(user.level)
        user.level += 1
        leveled = True

    return leveled


def award_xp(user, amount):
    if not user:
        return False

    user.xp += int(amount)
    return normalize_user_level(user)


def award_coins(user, amount):
    if not user:
        return

    user.coins += int(amount)


def ensure_daily_missions(user):
    if not user:
        return []

    mission_date = today_key()

    existing = {
        mission.mission_key: mission
        for mission in UserMission.query.filter_by(user_id=user.id, mission_date=mission_date).all()
    }

    for definition in MISSION_DEFINITIONS:
        if definition["key"] in existing:
            continue

        mission = UserMission(
            user_id=user.id,
            mission_key=definition["key"],
            title=definition["title"],
            description=definition["description"],
            target=definition["target"],
            xp_reward=definition["xp_reward"],
            coin_reward=definition["coin_reward"],
            mission_date=mission_date,
        )

        db.session.add(mission)

    db.session.commit()

    return (
        UserMission.query
        .filter_by(user_id=user.id, mission_date=mission_date)
        .order_by(UserMission.id.asc())
        .all()
    )


def increment_mission(user, mission_key, amount=1):
    if not user:
        return

    ensure_daily_missions(user)

    mission = (
        UserMission.query
        .filter_by(user_id=user.id, mission_key=mission_key, mission_date=today_key())
        .first()
    )

    if not mission or mission.is_claimed:
        return

    mission.progress = min(int(mission.target), int(mission.progress or 0) + int(amount))


def claim_mission(user, mission_id):
    if not user:
        return False, "Invalid user."

    mission = UserMission.query.filter_by(id=mission_id, user_id=user.id).first()

    if not mission:
        return False, "Mission not found."

    if not mission.is_complete:
        return False, "Mission is not complete yet."

    if mission.is_claimed:
        return False, "Mission already claimed."

    mission.is_claimed = True

    award_xp(user, mission.xp_reward)
    award_coins(user, mission.coin_reward)

    db.session.commit()

    return True, f"Mission claimed: +{mission.xp_reward} XP and +{mission.coin_reward} coins."
