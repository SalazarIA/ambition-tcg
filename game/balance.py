"""
Ambitionz V1.01A — Central Balance File

All relevant gameplay numbers should live here.
"""

GAME_VERSION = "V1.01A-core-identity"

STARTING_HP = 4000

MAX_ENERGY = 6
STARTING_ENERGY = 2

ELEMENT_ADVANTAGE_POWER_BONUS = 300

AMBITION_MAX = 10
AMBITION_UNLEASH_COST = 5
AMBITION_UNLEASH_POWER_BONUS = 300

OVERREACH_PENALTY_DAMAGE = 350
OVERREACH_RESET_VALUE = 6

INTENT_RULES = {
    "Strike": {
        "label": "Strike",
        "description": "+150 power if you win the clash. If you lose, receive +100 extra damage.",
        "win_power_bonus": 150,
        "lose_extra_damage": 100,
        "damage_reduction": 0,
        "survive_ambition": 0,
    },
    "Guard": {
        "label": "Guard",
        "description": "Reduce received damage by 350 this round.",
        "win_power_bonus": 0,
        "lose_extra_damage": 0,
        "damage_reduction": 350,
        "survive_ambition": 0,
    },
    "Focus": {
        "label": "Focus",
        "description": "If you survive the round, gain +2 Ambition.",
        "win_power_bonus": 0,
        "lose_extra_damage": 0,
        "damage_reduction": 0,
        "survive_ambition": 2,
    },
}

SIGIL_RULES = {
    "Fury": {
        "description": "+100 power if the player chose Strike.",
        "power_bonus": 100,
        "requires_intent": "Strike",
        "ambition_bonus": 0,
        "damage_bonus": 0,
        "damage_reduction": 0,
        "requires_element_advantage": False,
        "requires_element_disadvantage": False,
    },
    "Resolve": {
        "description": "+100 power if the player chose Guard.",
        "power_bonus": 100,
        "requires_intent": "Guard",
        "ambition_bonus": 0,
        "damage_bonus": 0,
        "damage_reduction": 0,
        "requires_element_advantage": False,
        "requires_element_disadvantage": False,
    },
    "Insight": {
        "description": "+1 Ambition if the player chose Focus.",
        "power_bonus": 0,
        "requires_intent": "Focus",
        "ambition_bonus": 1,
        "damage_bonus": 0,
        "damage_reduction": 0,
        "requires_element_advantage": False,
        "requires_element_disadvantage": False,
    },
    "Ruin": {
        "description": "+100 damage if winning with elemental advantage.",
        "power_bonus": 0,
        "requires_intent": None,
        "ambition_bonus": 0,
        "damage_bonus": 100,
        "damage_reduction": 0,
        "requires_element_advantage": True,
        "requires_element_disadvantage": False,
    },
    "Harmony": {
        "description": "Reduce 100 damage if in elemental disadvantage.",
        "power_bonus": 0,
        "requires_intent": None,
        "ambition_bonus": 0,
        "damage_bonus": 0,
        "damage_reduction": 100,
        "requires_element_advantage": False,
        "requires_element_disadvantage": True,
    },
}

DEFAULT_SIGIL = "Fury"

CARD_ROLES = [
    "Aggressor",
    "Defender",
    "Controller",
    "Balancer",
    "Finisher",
]

PVE_WIN_COINS = 60
PVE_WIN_XP = 30
PVE_LOSS_XP = 15

PVP_WIN_COINS = 150
PVP_WIN_XP = 80
PVP_LOSS_XP = 35
