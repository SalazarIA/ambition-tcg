from copy import deepcopy


def choose_response(bot_hand, player_card):
    if not bot_hand:
        return None

    player_power = int(player_card.get("power", 0))
    stronger = [card for card in bot_hand if int(card.get("power", 0)) > player_power]

    if stronger:
        return deepcopy(sorted(stronger, key=lambda card: (card["power"], card["name"]))[0])

    return deepcopy(sorted(bot_hand, key=lambda card: (card["power"], card["name"]))[0])
