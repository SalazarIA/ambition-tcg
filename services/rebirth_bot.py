from copy import deepcopy


def choose_response(bot_hand, player_card):
    if not bot_hand:
        return None

    player_attack = int(player_card.get("attack", player_card.get("power", 0)) or 0)
    stronger = [card for card in bot_hand if int(card.get("attack", 0) or 0) > player_attack]

    if stronger:
        return deepcopy(sorted(stronger, key=lambda card: (card["attack"], card["guard"], card["name"]))[0])

    return deepcopy(sorted(bot_hand, key=lambda card: (card["guard"], card["attack"], card["name"]))[-1])
