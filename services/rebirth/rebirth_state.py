from copy import deepcopy
import hashlib
import uuid

from services.rebirth.rebirth_cards import build_rebirth_deck


VALID_SIDES = {"player", "opponent"}


def _match_id(seed=None):
    token = str(seed) if seed is not None else uuid.uuid4().hex
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:14]
    return f"rebirth-{digest}"


def create_rebirth_player(name, seed=None):
    return {
        "name": name,
        "hp": 32,
        "ambition": 0,
        "deck": build_rebirth_deck(seed=seed),
        "hand": [],
        "discard": [],
        "active_card": None,
        "selected_intent": None,
    }


def draw_card(player):
    if not player.get("deck"):
        return None
    card = player["deck"].pop(0)
    player.setdefault("hand", []).append(card)
    return card


def draw_starting_hand(player, hand_size=4):
    drawn = []
    for _ in range(hand_size):
        card = draw_card(player)
        if card:
            drawn.append(card)
    return drawn


def create_rebirth_match(seed=None):
    player = create_rebirth_player("Player", seed=f"{seed}:player")
    opponent = create_rebirth_player("Rival", seed=f"{seed}:opponent")
    draw_starting_hand(player)
    draw_starting_hand(opponent)
    return {
        "match_id": _match_id(seed),
        "round": 1,
        "phase": "START",
        "player": player,
        "opponent": opponent,
        "combat_log": [],
        "cinematic_event": None,
        "winner": None,
        "is_finished": False,
        "seed": seed,
    }


def get_side(match, side):
    side_key = str(side or "").lower()
    if side_key not in VALID_SIDES:
        raise ValueError(f"Invalid side: {side}")
    return match[side_key]


def get_opponent_side(side):
    side_key = str(side or "").lower()
    if side_key == "player":
        return "opponent"
    if side_key == "opponent":
        return "player"
    raise ValueError(f"Invalid side: {side}")


def activate_card_from_hand(match, side, card_id):
    player = get_side(match, side)
    hand = player.setdefault("hand", [])
    selected = None
    for index, card in enumerate(hand):
        if card.get("id") == card_id:
            selected = hand.pop(index)
            break
    if not selected:
        raise ValueError("Card is not in hand.")

    previous = player.get("active_card")
    if previous:
        player.setdefault("discard", []).append(deepcopy(previous))
    player["active_card"] = selected
    return selected
