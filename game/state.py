AMBITION_MAX = 10
AMBITION_UNLEASH_COST = 5
AMBITION_UNLEASH_POWER_BONUS = 300
OVERREACH_PENALTY_DAMAGE = 300
OVERREACH_RESET_VALUE = 7

INTENT_STRIKE = "Strike"
INTENT_GUARD = "Guard"
INTENT_FOCUS = "Focus"

DEFAULT_INTENT = INTENT_STRIKE

VALID_INTENTS = {
    INTENT_STRIKE,
    INTENT_GUARD,
    INTENT_FOCUS,
}

INTENT_RULES = {
    INTENT_STRIKE: {
        "label": "Strike",
        "description": "+200 power if you win combat. If you lose, take +100 extra damage.",
        "win_power_bonus": 200,
        "loss_extra_damage": 100,
        "damage_reduction": 0,
        "survive_ambition_gain": 0,
    },
    INTENT_GUARD: {
        "label": "Guard",
        "description": "Reduce incoming damage by 300 this round.",
        "win_power_bonus": 0,
        "loss_extra_damage": 0,
        "damage_reduction": 300,
        "survive_ambition_gain": 0,
    },
    INTENT_FOCUS: {
        "label": "Focus",
        "description": "If you survive this round, gain +2 Ambition.",
        "win_power_bonus": 0,
        "loss_extra_damage": 0,
        "damage_reduction": 0,
        "survive_ambition_gain": 2,
    },
}


def normalize_intent(intent):
    if intent in VALID_INTENTS:
        return intent

    return DEFAULT_INTENT


def create_player_state(user, sid, deck, hand):
    return {
        "sid": sid,
        "user_id": user.id,
        "name": user.username,
        "hp": 4000,
        "deck": deck,
        "hand": hand,
        "graveyard": [],
        "field_m": None,
        "field_st": None,
        "ready": False,
        "shield": 0,
        "energy": 0,
        "max_energy": 0,
        "ambition": 0,
        "ambition_unleashed": False,
        "wants_unleash": False,
        "overreach_count": 0,
        "intent": DEFAULT_INTENT,
    }


def create_match_state(player_one, player_two):
    return {
        "p1": player_one,
        "p2": player_two,
        "round": 1,
        "phase": "Set Phase",
        "resolving": False,
        "logs": [],
    }


def reset_round_flags(player):
    player["ambition_unleashed"] = False
    player["wants_unleash"] = False
    player["intent"] = DEFAULT_INTENT
