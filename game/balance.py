"""
Central balance configuration for Ambition TCG.

This file should become the main place for tuning gameplay numbers.
"""

STARTING_HP = 4000

MAX_ENERGY = 6
STARTING_ENERGY = 2

AMBITION_MAX = 10
AMBITION_UNLEASH_COST = 5
AMBITION_UNLEASH_POWER_BONUS = 300

OVERREACH_PENALTY_DAMAGE = 350
OVERREACH_RESET_VALUE = 6

ELEMENT_ADVANTAGE_POWER_BONUS = 300

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

PVE_WIN_COINS = 60
PVE_WIN_XP = 30
PVE_LOSS_XP = 15

PVP_WIN_COINS = 150
PVP_WIN_XP = 80
PVP_LOSS_XP = 35
