AMBITION_MAX = 10
AMBITION_UNLEASH_COST = 5
AMBITION_UNLEASH_POWER_BONUS = 200
OVERREACH_PENALTY_DAMAGE = 300
OVERREACH_RESET_VALUE = 7


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
        "overreach_count": 0,
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
