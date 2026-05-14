import json
from datetime import datetime, timezone

from models import RewardLedger, UserMission, db


BETA_MISSION_DATE = "beta"


BETA_MISSION_DEFINITIONS = [
    {
        "key": "play_training_match",
        "title": "Training Duel",
        "description": "Finish 1 Training match.",
        "target": 1,
        "xp_reward": 45,
        "coin_reward": 0,
        "reward_preview": "45 XP",
        "cta_endpoint": "training",
        "cta_label": "Play Training",
    },
    {
        "key": "complete_tutorial",
        "title": "Learn the Loop",
        "description": "Complete the tutorial/onboarding step.",
        "target": 1,
        "xp_reward": 25,
        "coin_reward": 0,
        "reward_preview": "25 XP",
        "cta_endpoint": "tutorial",
        "cta_label": "Open Tutorial",
    },
    {
        "key": "view_collection",
        "title": "Open the Vault",
        "description": "Open your Collection and inspect owned cards.",
        "target": 1,
        "xp_reward": 20,
        "coin_reward": 0,
        "reward_preview": "20 XP",
        "cta_endpoint": "collection",
        "cta_label": "Open Collection",
    },
    {
        "key": "save_or_validate_deck",
        "title": "Deck Check",
        "description": "Save or validate the fixed 30-card beta deck.",
        "target": 1,
        "xp_reward": 30,
        "coin_reward": 0,
        "reward_preview": "30 XP",
        "cta_endpoint": "deck_builder",
        "cta_label": "Check Deck",
    },
    {
        "key": "play_campaign_chapter",
        "title": "Campaign Step",
        "description": "Finish 1 contextual Campaign chapter duel.",
        "target": 1,
        "xp_reward": 60,
        "coin_reward": 0,
        "reward_preview": "60 XP",
        "cta_endpoint": "campaign",
        "cta_label": "Start Campaign",
    },
    {
        "key": "return_daily",
        "title": "Daily Return",
        "description": "Claim today's Daily Check-In.",
        "target": 1,
        "xp_reward": 35,
        "coin_reward": 0,
        "reward_preview": "35 XP",
        "cta_endpoint": "daily",
        "cta_label": "Claim Daily",
    },
]


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
    {
        "key": "play_1_training",
        "title": "Training Grounds",
        "description": "Play 1 training match.",
        "target": 1,
        "xp_reward": 35,
        "coin_reward": 60,
    },
    {
        "key": "win_1_training",
        "title": "Beat the Bot",
        "description": "Win 1 training match.",
        "target": 1,
        "xp_reward": 80,
        "coin_reward": 120,
    },
    {
        "key": "use_overreach_1",
        "title": "Calculated Risk",
        "description": "Select Overreach 1 time.",
        "target": 1,
        "xp_reward": 60,
        "coin_reward": 90,
    },
    {
        "key": "declare_ready_1",
        "title": "Commit the Turn",
        "description": "Declare Ready 1 time.",
        "target": 1,
        "xp_reward": 30,
        "coin_reward": 50,
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


def award_xp(user, amount, source="system", metadata=None, reward_key=None):
    if not user:
        return {"awarded": False, "xp": 0, "level": 1, "level_progress_percent": 0}

    amount = max(0, int(amount or 0))

    if amount <= 0:
        return {
            "awarded": False,
            "xp": 0,
            "level": int(user.level or 1),
            "level_progress_percent": user.level_progress_percent,
            "total_xp": int(getattr(user, "total_xp", 0) or 0),
        }

    if reward_key and RewardLedger.query.filter_by(reward_key=reward_key).first():
        return {
            "awarded": False,
            "duplicate": True,
            "xp": 0,
            "level": int(user.level or 1),
            "level_progress_percent": user.level_progress_percent,
            "total_xp": int(getattr(user, "total_xp", 0) or 0),
        }

    before_level = int(user.level or 1)
    user.xp = int(user.xp or 0) + amount
    user.total_xp = int(getattr(user, "total_xp", 0) or 0) + amount
    leveled = normalize_user_level(user)

    if reward_key:
        db.session.add(
            RewardLedger(
                reward_key=reward_key,
                user_id=user.id,
                source=str(source or "system")[:80],
                xp=amount,
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False)[:4000],
            )
        )

    return {
        "awarded": True,
        "xp": amount,
        "level": int(user.level or 1),
        "level_before": before_level,
        "leveled": bool(leveled),
        "level_progress_percent": user.level_progress_percent,
        "next_level_xp": user.next_level_xp,
        "total_xp": int(getattr(user, "total_xp", 0) or 0),
    }


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


def ensure_beta_missions(user):
    if not user:
        return []

    existing = {
        mission.mission_key: mission
        for mission in UserMission.query.filter_by(user_id=user.id, mission_date=BETA_MISSION_DATE).all()
    }

    now = datetime.now(timezone.utc)

    for definition in BETA_MISSION_DEFINITIONS:
        mission = existing.get(definition["key"])

        if mission:
            mission.title = definition["title"]
            mission.description = definition["description"]
            mission.target = definition["target"]
            mission.xp_reward = definition["xp_reward"]
            mission.coin_reward = definition["coin_reward"]
            continue

        db.session.add(
            UserMission(
                user_id=user.id,
                mission_key=definition["key"],
                title=definition["title"],
                description=definition["description"],
                target=definition["target"],
                xp_reward=definition["xp_reward"],
                coin_reward=definition["coin_reward"],
                mission_date=BETA_MISSION_DATE,
                updated_at=now,
            )
        )

    db.session.flush()

    return (
        UserMission.query
        .filter_by(user_id=user.id, mission_date=BETA_MISSION_DATE)
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
    mission.updated_at = datetime.now(timezone.utc)


def increment_beta_mission(user, mission_key, amount=1):
    if not user:
        return None

    ensure_beta_missions(user)

    mission = (
        UserMission.query
        .filter_by(user_id=user.id, mission_key=mission_key, mission_date=BETA_MISSION_DATE)
        .first()
    )

    if not mission or mission.is_claimed:
        return None

    before_complete = mission.is_complete
    before_progress = int(mission.progress or 0)
    mission.progress = min(int(mission.target), before_progress + int(amount or 1))
    mission.updated_at = datetime.now(timezone.utc)

    return {
        "mission_key": mission.mission_key,
        "title": mission.title,
        "progress": int(mission.progress or 0),
        "target": int(mission.target or 1),
        "percent": mission.progress_percent,
        "completed": mission.is_complete,
        "just_completed": mission.is_complete and not before_complete,
        "changed": int(mission.progress or 0) != before_progress,
        "reward_preview": f"{mission.xp_reward} XP" if int(mission.xp_reward or 0) else "Progress",
    }


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
    mission.updated_at = datetime.now(timezone.utc)

    award_xp(
        user,
        mission.xp_reward,
        source="mission_claim",
        metadata={"mission_key": mission.mission_key, "mission_id": mission.id},
        reward_key=f"mission:{user.id}:{mission.id}",
    )
    award_coins(user, mission.coin_reward)

    db.session.commit()

    return True, f"Mission claimed: +{mission.xp_reward} XP and +{mission.coin_reward} coins."
