import random

from game.deck import build_playable_deck, draw_starting_hand
from game.engine import register_card_played_for_ambition, request_unleash
from game.rules import can_pay_cost, pay_card_cost, reset_player_energy
from game.state import create_player_state, set_player_intent


BOT_NAMES = [
    "Astra",
    "Nyx",
    "Kael",
    "Orion",
    "Vega",
    "Selene",
    "Mira",
]
GAME_RNG = random.SystemRandom()


class BotUser:
    id = -999
    username = "Bot"


def create_bot_player(deck_json):
    user = BotUser()
    user.username = GAME_RNG.choice(BOT_NAMES)

    deck = build_playable_deck(deck_json)
    hand = draw_starting_hand(deck, 5)

    bot = create_player_state(user, "BOT_SID", deck, hand)

    bot["is_bot"] = True
    bot["name"] = f"Bot {user.username}"
    bot["difficulty"] = "training"

    reset_player_energy(bot, 1)

    return bot


def choose_bot_intent(bot):
    hp = int(bot.get("hp", 4000))
    ambition = int(bot.get("ambition", 0))
    hand = bot.get("hand", [])

    has_monster = any(card.get("type") == "Monster" for card in hand)
    has_fury = any(card.get("sigil") == "Fury" for card in hand)
    has_resolve = any(card.get("sigil") == "Resolve" for card in hand)
    has_insight = any(card.get("sigil") == "Insight" for card in hand)

    if hp <= 1600:
        if has_resolve:
            return "Guard"
        return GAME_RNG.choices(["Guard", "Focus"], weights=[75, 25], k=1)[0]

    if ambition >= 5 and has_monster:
        if has_fury:
            return "Strike"
        return GAME_RNG.choices(["Strike", "Focus"], weights=[75, 25], k=1)[0]

    if len(hand) <= 2:
        if has_insight:
            return "Focus"
        return GAME_RNG.choices(["Focus", "Guard"], weights=[70, 30], k=1)[0]

    return GAME_RNG.choices(
        ["Strike", "Guard", "Focus"],
        weights=[45, 30, 25],
        k=1,
    )[0]


def card_score_for_bot(card, bot):
    score = 0

    card_type = card.get("type")
    cost = int(card.get("cost", 1))
    power = int(card.get("power", 0))
    effect = card.get("effect", "None")
    role = card.get("role", "Balancer")
    sigil = card.get("sigil", "Fury")
    intent = bot.get("intent", "Strike")

    if not can_pay_cost(bot, card):
        return -9999

    if card_type == "Monster":
        score += 1000
        score += power
        score -= cost * 40

        if effect != "None":
            score += 120

        if role == "Finisher":
            score += 120

        if role == "Aggressor" and intent == "Strike":
            score += 140

        if role == "Defender" and intent == "Guard":
            score += 140

        if role == "Controller" and intent == "Focus":
            score += 120

        if sigil == "Fury" and intent == "Strike":
            score += 180

        if sigil == "Resolve" and intent == "Guard":
            score += 180

        if sigil == "Insight" and intent == "Focus":
            score += 180

        if cost >= 3:
            score += 80

    elif card_type == "Spell":
        score += 650
        score -= cost * 35

        if effect in ["Burn", "Drain", "Boost", "Draw"]:
            score += 160

        if effect == "Heal" and bot.get("hp", 4000) <= 2500:
            score += 220

        if role == "Controller" and intent == "Focus":
            score += 80

    elif card_type == "Trap":
        score += 560
        score -= cost * 30

        if effect in ["Counter", "Shield", "Weaken"]:
            score += 140

        if role == "Defender" and intent == "Guard":
            score += 120

    return score


def choose_best_card_index(bot, allowed_types):
    best_index = None
    best_score = -99999

    for index, card in enumerate(bot.get("hand", [])):
        if card.get("type") not in allowed_types:
            continue

        score = card_score_for_bot(card, bot)

        if score > best_score:
            best_score = score
            best_index = index

    return best_index


def play_card_from_hand(bot, index, match_logs):
    if index is None:
        return False

    if index < 0 or index >= len(bot.get("hand", [])):
        return False

    card = bot["hand"][index]
    card_type = card.get("type")

    if not can_pay_cost(bot, card):
        return False

    if card_type == "Monster":
        if bot.get("field_m") is not None:
            return False

        pay_card_cost(bot, card)
        bot["field_m"] = bot["hand"].pop(index)
        register_card_played_for_ambition(bot, card, match_logs)

        match_logs.append(
            f"{bot['name']} set a monster: {card['name']} [{card.get('sigil', 'Fury')} / {card.get('role', 'Balancer')}]."
        )
        return True

    if card_type in ["Spell", "Trap"]:
        if bot.get("field_st") is not None:
            return False

        pay_card_cost(bot, card)
        bot["field_st"] = bot["hand"].pop(index)
        register_card_played_for_ambition(bot, card, match_logs)

        match_logs.append(f"{bot['name']} set a spell/trap: {card['name']}.")
        return True

    return False


def bot_play_turn(bot, match_logs):
    if bot.get("ready"):
        return

    intent = choose_bot_intent(bot)
    set_player_intent(bot, intent)

    match_logs.append(f"{bot['name']} selected {intent} intent.")

    monster_index = choose_best_card_index(bot, ["Monster"])
    play_card_from_hand(bot, monster_index, match_logs)

    spell_trap_index = choose_best_card_index(bot, ["Spell", "Trap"])
    play_card_from_hand(bot, spell_trap_index, match_logs)

    if int(bot.get("ambition", 0)) >= 5 and bot.get("field_m"):
        if GAME_RNG.random() <= 0.72:
            request_unleash(bot)
            match_logs.append(f"{bot['name']} prepared Ambition Unleash.")

    bot["ready"] = True
