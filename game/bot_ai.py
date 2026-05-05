import random

from game.rules import can_pay_cost, pay_card_cost
from game.engine import register_card_played_for_ambition, request_unleash
from game.state import set_player_intent


GAME_RNG = random.SystemRandom()


DIFFICULTY_PROFILES = {
    "easy": {
        "name": "Easy",
        "intent_weights": {
            "Strike": 35,
            "Guard": 35,
            "Focus": 25,
        },
        "overreach_hp_floor": 2600,
        "overreach_chance": 0.08,
        "play_spell_trap_chance": 0.45,
        "mistake_chance": 0.28,
        "prefer_best_card": False,
    },
    "normal": {
        "name": "Normal",
        "intent_weights": {
            "Strike": 45,
            "Guard": 25,
            "Focus": 22,
        },
        "overreach_hp_floor": 2200,
        "overreach_chance": 0.18,
        "play_spell_trap_chance": 0.72,
        "mistake_chance": 0.10,
        "prefer_best_card": True,
    },
    "hard": {
        "name": "Hard",
        "intent_weights": {
            "Strike": 48,
            "Guard": 18,
            "Focus": 20,
        },
        "overreach_hp_floor": 1800,
        "overreach_chance": 0.34,
        "play_spell_trap_chance": 0.88,
        "mistake_chance": 0.02,
        "prefer_best_card": True,
    },
}


def profile_for(difficulty):
    key = str(difficulty or "normal").lower().strip()
    return DIFFICULTY_PROFILES.get(key, DIFFICULTY_PROFILES["normal"])


def weighted_choice(weight_map):
    options = list(weight_map.keys())
    weights = list(weight_map.values())
    return GAME_RNG.choices(options, weights=weights, k=1)[0]


def card_score(card, bot, opponent, difficulty="normal"):
    profile = profile_for(difficulty)

    if not card or not can_pay_cost(bot, card):
        return -999999

    card_type = card.get("type")
    cost = int(card.get("cost", 1) or 1)
    power = int(card.get("power", 0) or 0)
    effect = card.get("effect", "None")
    role = card.get("role", "Balancer")
    sigil = card.get("sigil", "Global")
    intent = bot.get("intent", "Strike")
    bot_hp = int(bot.get("hp", 4000) or 4000)
    opponent_hp = int(opponent.get("hp", 4000) or 4000)

    score = 0

    if card_type == "Monster":
        score += 1000 + power
        score -= cost * 42

        if intent == "Strike":
            score += 90

        if sigil == "Fury" and intent == "Strike":
            score += 220

        if sigil == "Resolve" and intent == "Guard":
            score += 220

        if sigil == "Insight" and intent == "Focus":
            score += 220

        if sigil == "Harmony":
            score += 80

        if role == "Aggressor" and intent == "Strike":
            score += 170

        if role == "Defender" and bot_hp <= 2500:
            score += 180

        if role == "Controller" and intent == "Focus":
            score += 140

        if opponent_hp <= 1800 and power >= 1500:
            score += 220

    elif card_type == "Spell":
        score += 650
        score -= cost * 35

        if effect in ["Burn", "Drain", "Boost"]:
            score += 180

        if effect == "Draw" and len(bot.get("hand", [])) <= 3:
            score += 210

        if effect == "Heal" and bot_hp <= 2500:
            score += 260

        if effect == "Shield" and bot_hp <= 2200:
            score += 190

        if effect == "Weaken":
            score += 150

    elif card_type == "Trap":
        score += 560
        score -= cost * 30

        if effect in ["Counter", "Shield", "Weaken"]:
            score += 170

        if bot_hp <= 2400:
            score += 160

        if intent == "Guard":
            score += 100

    if profile["prefer_best_card"]:
        score += 50

    return score


def choose_intent(bot, opponent, difficulty="normal"):
    profile = profile_for(difficulty)
    bot_hp = int(bot.get("hp", 4000) or 4000)
    opponent_hp = int(opponent.get("hp", 4000) or 4000)
    hand = bot.get("hand", [])

    has_monster = any(card.get("type") == "Monster" and can_pay_cost(bot, card) for card in hand)
    has_fury = any(card.get("sigil") == "Fury" and can_pay_cost(bot, card) for card in hand)
    has_resolve = any(card.get("sigil") == "Resolve" and can_pay_cost(bot, card) for card in hand)
    has_insight = any(card.get("sigil") == "Insight" and can_pay_cost(bot, card) for card in hand)

    if bot_hp <= 1600:
        return "Guard" if has_resolve else weighted_choice({"Guard": 75, "Focus": 25})

    if len(hand) <= 2:
        return "Focus" if has_insight else weighted_choice({"Focus": 65, "Guard": 35})

    if has_monster and has_fury and bot_hp >= profile["overreach_hp_floor"] and opponent_hp <= 2600:
        return "Strike"

    return weighted_choice(profile["intent_weights"])


def choose_card_index(bot, opponent, allowed_types, difficulty="normal"):
    profile = profile_for(difficulty)
    candidates = []

    for index, card in enumerate(bot.get("hand", [])):
        if card.get("type") not in allowed_types:
            continue

        if not can_pay_cost(bot, card):
            continue

        candidates.append((index, card_score(card, bot, opponent, difficulty)))

    if not candidates:
        return None

    if GAME_RNG.random() < profile["mistake_chance"]:
        return GAME_RNG.choice(candidates)[0]

    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def play_index(bot, index, match_logs):
    if index is None:
        return None

    hand = bot.get("hand", [])

    if index < 0 or index >= len(hand):
        return None

    card = hand[index]

    if not can_pay_cost(bot, card):
        return None

    card_type = card.get("type")

    if card_type == "Monster":
        if bot.get("field_m"):
            return None

        pay_card_cost(bot, card)
        played = bot["hand"].pop(index)
        bot["field_m"] = played
        register_card_played_for_ambition(bot, played, match_logs)
        return played

    if card_type in ["Spell", "Trap"]:
        if bot.get("field_st"):
            return None

        pay_card_cost(bot, card)
        played = bot["hand"].pop(index)
        bot["field_st"] = played
        register_card_played_for_ambition(bot, played, match_logs)
        return played

    return None


def bot_choose_play(bot, opponent, difficulty="normal"):
    profile = profile_for(difficulty)
    logs = []

    if bot.get("ready"):
        return {
            "intent": bot.get("intent", "Strike"),
            "monster": bot.get("field_m"),
            "spell_or_trap": bot.get("field_st"),
            "difficulty": difficulty,
            "profile": profile["name"],
            "logs": logs,
        }

    intent = choose_intent(bot, opponent, difficulty)
    set_player_intent(bot, intent)

    monster = None
    spell_or_trap = None

    monster_index = choose_card_index(bot, opponent, ["Monster"], difficulty)
    monster = play_index(bot, monster_index, logs)

    if GAME_RNG.random() <= profile["play_spell_trap_chance"]:
        spell_trap_index = choose_card_index(bot, opponent, ["Spell", "Trap"], difficulty)
        spell_or_trap = play_index(bot, spell_trap_index, logs)

    if (
        bot.get("field_m")
        and int(bot.get("ambition", 0) or 0) >= 5
        and int(bot.get("hp", 0) or 0) >= profile["overreach_hp_floor"]
        and GAME_RNG.random() <= profile["overreach_chance"]
    ):
        if request_unleash(bot):
            logs.append(f"{bot['name']} prepared Ambition Unleash.")

    bot["ready"] = True

    return {
        "intent": intent,
        "monster": monster,
        "spell_or_trap": spell_or_trap,
        "difficulty": difficulty,
        "profile": profile["name"],
        "logs": logs,
    }
