PROGRESSION_LOOP_VERSION = "Ambitionz V1.06 Progression Loop Pack"

CORE_LOOP = [
    {
        "step": "Play Match",
        "purpose": "Start the engagement loop with a quick duel.",
        "player_feeling": "I can play one more match quickly.",
    },
    {
        "step": "Earn XP and Coins",
        "purpose": "Reward time spent even after losses.",
        "player_feeling": "My time was not wasted.",
    },
    {
        "step": "Complete Missions",
        "purpose": "Give short-term goals beyond simply winning.",
        "player_feeling": "I have a reason to return today.",
    },
    {
        "step": "Open Booster",
        "purpose": "Create anticipation and collection growth.",
        "player_feeling": "Maybe I unlock something useful or rare.",
    },
    {
        "step": "Improve Deck",
        "purpose": "Turn rewards into strategic expression.",
        "player_feeling": "My deck is becoming mine.",
    },
    {
        "step": "Climb Ranking",
        "purpose": "Create competitive progression.",
        "player_feeling": "I am getting better and proving it.",
    },
    {
        "step": "Unlock Cosmetic or Card Identity",
        "purpose": "Create long-term attachment and personalization.",
        "player_feeling": "My account has history and identity.",
    },
]

PROGRESSION_SYSTEMS = {
    "xp": {
        "role": "Measures account growth and unlock pacing.",
        "design_rule": "XP should reward both wins and participation.",
        "future_use": "Unlock levels, cosmetics, missions and beta milestones.",
    },
    "coins": {
        "role": "Soft currency for boosters and future cosmetic purchases.",
        "design_rule": "Coins should feel useful but not inflate too fast.",
        "future_use": "Booster purchases, event entries, cosmetics.",
    },
    "missions": {
        "role": "Daily and onboarding goals.",
        "design_rule": "Missions must teach good gameplay behavior.",
        "future_use": "Daily retention, tutorial progression, beta tasks.",
    },
    "boosters": {
        "role": "Collection expansion and excitement.",
        "design_rule": "Boosters should support deck improvement without overwhelming new players.",
        "future_use": "Element packs, Sigil packs, event packs.",
    },
    "ranking": {
        "role": "Competitive identity.",
        "design_rule": "Ranking should reward consistency, not only grind.",
        "future_use": "Seasons, tiers, leaderboard rewards.",
    },
    "cosmetics": {
        "role": "Long-term personalization.",
        "design_rule": "Cosmetics should not affect gameplay power.",
        "future_use": "Card backs, frames, titles, avatars, arena skins.",
    },
}

REWARD_PHILOSOPHY = {
    "win": "Winning should feel clearly better, especially in PvP.",
    "loss": "Losing should still advance the player slightly to reduce early churn.",
    "draw": "Draws should reward time but less than clean wins.",
    "training": "Training rewards should teach and encourage experimentation.",
    "pvp": "PvP rewards should be the main competitive progression source.",
}

MISSION_DESIGN_RULES = [
    "A mission should teach or reinforce a useful behavior.",
    "Avoid missions that force bad gameplay decisions.",
    "Use simple verbs: play, win, use, complete, open, claim.",
    "Early missions should be easy and fast.",
    "Daily missions should create variety without forcing frustration.",
    "Beta missions should generate testing data.",
]

BOOSTER_DESIGN_RULES = [
    "Starter boosters should be readable and low complexity.",
    "Element boosters should help players pursue identity.",
    "Sigil boosters should help players pursue playstyle.",
    "Rare cards should feel exciting but not mandatory.",
    "Beta booster economy should be generous enough for testing.",
]

RETENTION_TARGETS = [
    "The first match should happen quickly.",
    "The first reward should be immediate.",
    "The first booster should be reachable early.",
    "The first deck edit should feel meaningful.",
    "The first ranking improvement should feel achievable.",
]
