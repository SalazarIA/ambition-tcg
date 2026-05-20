from copy import deepcopy

from services.rebirth_contracts import validate_phase
from services.rebirth_events import state_hash
from services.rebirth_state import STARTING_HP, available_evolutions


REQUIRED_CARD_FIELDS = {
    "id",
    "name",
    "family",
    "tier",
    "attack",
    "guard",
    "element",
    "ability_key",
    "ability_name",
    "ability_text",
    "art",
    "art_key",
    "art_status",
    "art_version",
    "palette",
    "silhouette",
}


def validate_card_contract(card):
    missing = [field for field in REQUIRED_CARD_FIELDS if field not in card]
    if missing:
        raise ValueError(f"Rebirth card missing required fields: {', '.join(missing)}")
    return card


def side_payload(side, *, reveal_hand=True):
    for card in side.get("hand", []):
        validate_card_contract(card)
    for card in side.get("deck", []):
        validate_card_contract(card)
    for card in side.get("discard", []):
        validate_card_contract(card)
    if side.get("played_card"):
        validate_card_contract(side["played_card"])

    payload = {
        "name": side["name"],
        "hp": side["hp"],
        "max_hp": side.get("max_hp", STARTING_HP),
        "deck_count": len(side.get("deck", [])),
        "discard_count": len(side.get("discard", [])),
        "played_card": deepcopy(side.get("played_card")),
        "wounded": bool(side.get("wounded")),
        "statuses": deepcopy(side.get("statuses", {})),
    }
    if reveal_hand:
        payload["hand"] = deepcopy(side.get("hand", []))
    else:
        payload["hand_count"] = len(side.get("hand", []))
    return payload


def public_state(match):
    validate_phase(match["phase"])
    return {
        "match_id": match["match_id"],
        "architecture": match["architecture"],
        "version": int(match.get("version", 0) or 0),
        "state_hash": state_hash(match),
        "turn": match["turn"],
        "phase": match["phase"],
        "turn_phase": match.get("turn_phase"),
        "player": side_payload(match["player"], reveal_hand=True),
        "bot": side_payload(match["bot"], reveal_hand=False),
        "bot_profile": deepcopy(match.get("bot_profile")),
        "available_evolutions": available_evolutions(match["player"]),
        "last_clash": deepcopy(match.get("last_clash")),
        "result": deepcopy(match.get("result")),
        "winner": match.get("winner"),
        "is_finished": bool(match.get("is_finished")),
        "events": deepcopy(match.get("events", [])[-12:]),
        "log": list(match.get("log", [])[-8:]),
    }
