from copy import deepcopy
import hashlib
import uuid

from services.rebirth_cards import build_deck, catalog_payload


STARTING_HP = 30
HAND_SIZE = 5


class RebirthStateError(ValueError):
    pass


def _match_id(seed=None):
    if seed is None:
        return f"rebirth-{uuid.uuid4().hex[:12]}"
    digest = hashlib.sha256(str(seed).encode("utf-8")).hexdigest()[:12]
    return f"rebirth-{digest}"


def create_player(name, owner):
    return {
        "name": name,
        "hp": STARTING_HP,
        "max_hp": STARTING_HP,
        "deck": build_deck(owner),
        "hand": [],
        "discard": [],
        "played_card": None,
        "wounded": False,
    }


def draw_card(player):
    if not player["deck"]:
        return None
    card = player["deck"].pop(0)
    player["hand"].append(card)
    return card


def draw_to_hand_size(player, hand_size=HAND_SIZE):
    drawn = []
    while len(player["hand"]) < hand_size:
        card = draw_card(player)
        if not card:
            break
        drawn.append(card)
    return drawn


def create_match(seed=None):
    player = create_player("You", "player")
    bot = create_player("Bot", "bot")
    draw_to_hand_size(player)
    draw_to_hand_size(bot)

    return {
        "match_id": _match_id(seed),
        "architecture": "Ambitionz Rebirth",
        "turn": 1,
        "phase": "choose",
        "player": player,
        "bot": bot,
        "last_clash": None,
        "result": None,
        "winner": None,
        "is_finished": False,
        "log": [
            "Turn 01   Rebirth clash initialized.",
            "Turn 01   Choose one monster.",
        ],
        "catalog": catalog_payload(),
    }


def remove_from_hand(player, *, card_instance_id=None, card_id=None):
    for index, card in enumerate(player["hand"]):
        if card_instance_id and card["instance_id"] == card_instance_id:
            return player["hand"].pop(index)
        if not card_instance_id and card_id and card["id"] == card_id:
            return player["hand"].pop(index)
    raise RebirthStateError("Card is not in hand.")


def add_to_discard(player, card):
    if card:
        player["discard"].append(deepcopy(card))


def available_evolutions(player):
    grouped = {}
    for card in player["hand"]:
        if not card.get("evolution_id"):
            continue
        grouped.setdefault(card["id"], []).append(card)

    evolutions = []
    for card_id, cards in grouped.items():
        if len(cards) >= 2:
            first = cards[0]
            evolutions.append(
                {
                    "card_id": card_id,
                    "name": first["name"],
                    "count": len(cards),
                    "evolution_id": first["evolution_id"],
                }
            )
    return evolutions


def clear_played_cards(match):
    add_to_discard(match["player"], match["player"].get("played_card"))
    add_to_discard(match["bot"], match["bot"].get("played_card"))
    match["player"]["played_card"] = None
    match["bot"]["played_card"] = None


def side_payload(side, *, reveal_hand=True):
    payload = {
        "name": side["name"],
        "hp": side["hp"],
        "max_hp": side.get("max_hp", STARTING_HP),
        "deck_count": len(side["deck"]),
        "discard_count": len(side["discard"]),
        "played_card": deepcopy(side.get("played_card")),
        "wounded": bool(side.get("wounded")),
    }
    if reveal_hand:
        payload["hand"] = deepcopy(side["hand"])
    else:
        payload["hand_count"] = len(side["hand"])
    return payload


def public_state(match):
    return {
        "match_id": match["match_id"],
        "architecture": match["architecture"],
        "turn": match["turn"],
        "phase": match["phase"],
        "player": side_payload(match["player"], reveal_hand=True),
        "bot": side_payload(match["bot"], reveal_hand=False),
        "available_evolutions": available_evolutions(match["player"]),
        "last_clash": deepcopy(match.get("last_clash")),
        "result": deepcopy(match.get("result")),
        "winner": match.get("winner"),
        "is_finished": match["is_finished"],
        "log": list(match["log"][-8:]),
    }
