import random


VALID_INTENTS = ["Strike", "Guard", "Focus", "Overreach"]


def card_type(card):
    return str(card.get("type", "")).strip()


def card_power(card):
    try:
        return int(card.get("power", 0) or 0)
    except Exception:
        return 0


def card_cost(card):
    try:
        return int(card.get("cost", 0) or 0)
    except Exception:
        return 0


def card_sigil(card):
    return str(card.get("sigil", "Global") or "Global")


def card_role(card):
    return str(card.get("role", "Balancer") or "Balancer")


def is_monster(card):
    return card_type(card) == "Monster"


def is_spell_or_trap(card):
    return card_type(card) in {"Spell", "Trap"}


def score_monster(card, difficulty="normal"):
    score = card_power(card)

    sigil = card_sigil(card)
    role = card_role(card)
    cost = card_cost(card)

    if sigil == "Fury":
        score += 250
    elif sigil == "Resolve":
        score += 180
    elif sigil == "Insight":
        score += 140
    elif sigil == "Ruin":
        score += 220
    elif sigil == "Harmony":
        score += 120

    if role in {"Aggressor", "Finisher"}:
        score += 180
    elif role in {"Defender", "Tank"}:
        score += 130
    elif role in {"Controller", "Support"}:
        score += 110

    if difficulty == "easy":
        score -= cost * 10
    elif difficulty == "hard":
        score += cost * 35

    return score


def score_spell_or_trap(card, difficulty="normal"):
    score = 100

    sigil = card_sigil(card)
    role = card_role(card)
    effect = str(card.get("effect", "")).lower()

    if sigil == "Insight":
        score += 180
    elif sigil == "Resolve":
        score += 140
    elif sigil == "Ruin":
        score += 170
    elif sigil == "Harmony":
        score += 120
    elif sigil == "Fury":
        score += 110

    keywords = {
        "draw": 160,
        "damage": 140,
        "destroy": 180,
        "heal": 110,
        "shield": 130,
        "reduce": 120,
        "boost": 120,
        "graveyard": 90,
    }

    for keyword, value in keywords.items():
        if keyword in effect:
            score += value

    if role in {"Controller", "Support"}:
        score += 120

    if difficulty == "easy":
        score += random.randint(-50, 50)
    elif difficulty == "hard":
        score += 80

    return score


def choose_best_monster(hand, difficulty="normal"):
    monsters = [
        (index, card)
        for index, card in enumerate(hand)
        if is_monster(card)
    ]

    if not monsters:
        return None

    if difficulty == "easy":
        return monsters[0]

    return max(monsters, key=lambda item: score_monster(item[1], difficulty))


def choose_best_spell_or_trap(hand, difficulty="normal"):
    spells = [
        (index, card)
        for index, card in enumerate(hand)
        if is_spell_or_trap(card)
    ]

    if not spells:
        return None

    if difficulty == "easy":
        return spells[0]

    return max(spells, key=lambda item: score_spell_or_trap(item[1], difficulty))


def choose_intent(bot, opponent=None, difficulty="normal"):
    bot_hp = int(bot.get("hp", 4000) or 4000)
    opponent_hp = int((opponent or {}).get("hp", 4000) or 4000)

    bot_monster = bot.get("field_m")
    opponent_monster = (opponent or {}).get("field_m")

    bot_power = card_power(bot_monster or {})
    opponent_power = card_power(opponent_monster or {})

    if difficulty == "easy":
        return random.choice(["Strike", "Guard", "Focus"])

    if bot_hp <= 1200:
        return "Guard"

    if opponent_hp <= 1200 and bot_power >= opponent_power:
        return "Strike"

    if bot_power >= opponent_power + 500:
        return "Strike"

    if opponent_power >= bot_power + 600:
        return "Guard"

    if difficulty == "hard":
        if bot_power >= 1800 and opponent_hp <= 2000:
            return "Overreach"

        if not bot_monster:
            return "Focus"

    return "Focus"


def bot_choose_play(bot, opponent=None, difficulty="normal"):
    hand = bot.get("hand", [])

    chosen_monster = None
    chosen_spell = None

    if not bot.get("field_m"):
        chosen_monster = choose_best_monster(hand, difficulty)

        if chosen_monster:
            index, card = chosen_monster
            bot["field_m"] = hand.pop(index)

    if not bot.get("field_st"):
        chosen_spell = choose_best_spell_or_trap(hand, difficulty)

        if chosen_spell:
            index, card = chosen_spell
            bot["field_st"] = hand.pop(index)

    bot["intent"] = choose_intent(bot, opponent, difficulty)
    bot["ready"] = True

    return {
        "monster": bot.get("field_m"),
        "spell_or_trap": bot.get("field_st"),
        "intent": bot.get("intent"),
        "difficulty": difficulty,
    }
