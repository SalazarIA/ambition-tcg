import random

from game.deck import build_playable_deck, draw_starting_hand
from game.rules import can_pay_cost, pay_card_cost, reset_player_energy
from game.engine import register_card_played_for_ambition, request_unleash
from game.state import create_player_state, set_player_intent


BOT_NAMES = [
    "Astra",
    "Nyx",
    "Kael",
    "Orion",
    "Vega",
]


def create_bot_user_stub():
    class BotUser:
        id = -999
        username = random.choice(BOT_NAMES)

    return BotUser()


def create_bot_player(deck_json):
    user = create_bot_user_stub()
    deck = build_playable_deck(deck_json)
    hand = draw_starting_hand(deck, 5)

    player = create_player_state(user, "BOT_SID", deck, hand)
    player["is_bot"] = True
    player["name"] = f"Bot {user.username}"

    reset_player_energy(player, 1)

    return player


def choose_bot_intent(bot):
    hp = int(bot.get("hp", 4000))
    ambition = int(bot.get("ambition", 0))

    if hp <= 1800:
        return "Guard"

    if ambition >= 4:
        return "Strike"

    return random.choice(["Strike", "Guard", "Focus"])


def bot_choose_card_indexes(bot):
    hand = bot.get("hand", [])

    monster_indexes = []
    spell_trap_indexes = []

    for index, card in enumerate(hand):
        if not can_pay_cost(bot, card):
            continue

        if card.get("type") == "Monster" and bot.get("field_m") is None:
            monster_indexes.append(index)

        if card.get("type") in ["Spell", "Trap"] and bot.get("field_st") is None:
            spell_trap_indexes.append(index)

    selected = []

    if monster_indexes:
        selected.append(random.choice(monster_indexes))

    if spell_trap_indexes:
        selected.append(random.choice(spell_trap_indexes))

    return sorted(selected, reverse=True)


def bot_play_turn(bot, match_logs):
    intent = choose_bot_intent(bot)
    set_player_intent(bot, intent)

    match_logs.append(f"{bot['name']} selected {intent} intent.")

    indexes = bot_choose_card_indexes(bot)

    for index in indexes:
        if index < 0 or index >= len(bot["hand"]):
            continue

        card = bot["hand"][index]

        if not can_pay_cost(bot, card):
            continue

        if card.get("type") == "Monster" and bot.get("field_m") is None:
            pay_card_cost(bot, card)
            bot["field_m"] = bot["hand"].pop(index)
            register_card_played_for_ambition(bot, card, match_logs)
            match_logs.append(f"{bot['name']} set a monster: {card['name']}.")

        elif card.get("type") in ["Spell", "Trap"] and bot.get("field_st") is None:
            pay_card_cost(bot, card)
            bot["field_st"] = bot["hand"].pop(index)
            register_card_played_for_ambition(bot, card, match_logs)
            match_logs.append(f"{bot['name']} set a spell/trap: {card['name']}.")

    if int(bot.get("ambition", 0)) >= 5 and bot.get("field_m"):
        if random.random() < 0.65:
            request_unleash(bot)
            match_logs.append(f"{bot['name']} prepared Ambition Unleash.")

    bot["ready"] = True
