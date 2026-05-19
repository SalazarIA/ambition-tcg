from copy import deepcopy
import hashlib
import uuid

from services.rebirth.rebirth_decks import build_rebirth_deck, get_default_rebirth_deck_id


VALID_SIDES = {"player", "opponent"}
VALID_DIFFICULTIES = {"easy", "normal", "hard"}
DIFFICULTY_LABELS = {
    "easy": "Easy",
    "normal": "Normal",
    "hard": "Hard",
}


def _match_id(seed=None):
    token = str(seed) if seed is not None else uuid.uuid4().hex
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:14]
    return f"rebirth-{digest}"


def normalize_rebirth_difficulty(difficulty=None):
    key = str(difficulty or "normal").lower()
    if key not in VALID_DIFFICULTIES:
        raise ValueError("Invalid Rebirth difficulty.")
    return key


def create_rebirth_player(name, seed=None, deck_id=None):
    deck = build_rebirth_deck(deck_id or get_default_rebirth_deck_id(), seed=seed)
    return {
        "name": name,
        "hp": 32,
        "ambition": 0,
        "deck": deepcopy(deck["cards"]),
        "deck_id": deck["id"],
        "deck_name": deck["name"],
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


def _opponent_deck_id(player_deck_id):
    if player_deck_id == "deepguard":
        return "null_circuit"
    if player_deck_id == "null_circuit":
        return "ember_oath"
    return "deepguard"


def create_rebirth_match(seed=None, deck_id=None, difficulty="normal"):
    selected_deck = build_rebirth_deck(deck_id or get_default_rebirth_deck_id(), seed=f"{seed}:preview")
    difficulty_key = normalize_rebirth_difficulty(difficulty)
    player = create_rebirth_player("Player", seed=f"{seed}:player", deck_id=selected_deck["id"])
    opponent = create_rebirth_player("Rival", seed=f"{seed}:opponent", deck_id=_opponent_deck_id(selected_deck["id"]))
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
        "selected_deck_id": selected_deck["id"],
        "selected_deck_name": selected_deck["name"],
        "difficulty": difficulty_key,
        "difficulty_label": DIFFICULTY_LABELS[difficulty_key],
        "opponent_profile": None,
        "metrics": {
            "player_damage_dealt": 0,
            "opponent_damage_dealt": 0,
            "cards_activated": 0,
            "player_intents": {},
            "ambition_gained": 0,
        },
        "match_summary": None,
        "reward_preview": None,
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
