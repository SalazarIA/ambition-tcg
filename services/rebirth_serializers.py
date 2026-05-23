from copy import deepcopy

from services.rebirth_contracts import validate_phase
from services.rebirth_events import state_hash
from services.rebirth_state import STARTING_HP, available_evolutions, compact_battlefield, field_slots


REQUIRED_CARD_FIELDS = {
    "id",
    "name",
    "type",
    "card_type",
    "family",
    "tier",
    "cost",
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
        raise ValueError(f"Carta Rebirth sem campos obrigatórios: {', '.join(missing)}")
    return card


def side_payload(side, *, reveal_hand=True):
    field = deepcopy(field_slots(side))
    battlefield = deepcopy(compact_battlefield(side))
    for card in side.get("hand", []):
        validate_card_contract(card)
    for card in side.get("deck", []):
        validate_card_contract(card)
    for card in side.get("discard", []):
        validate_card_contract(card)
    for card in battlefield:
        validate_card_contract(card)
    for card in side.get("traps", []):
        validate_card_contract(card)
    if side.get("played_card"):
        validate_card_contract(side["played_card"])

    payload = {
        "name": side["name"],
        "hp": side["hp"],
        "max_hp": side.get("max_hp", STARTING_HP),
        "energy": int(side.get("energy", 0) or 0),
        "max_energy": int(side.get("max_energy", 0) or 0),
        "deck_count": len(side.get("deck", [])),
        "discard_count": len(side.get("discard", [])),
        "played_card": deepcopy(side.get("played_card")),
        "battlefield": battlefield,
        "field": field,
        "trap_count": len(side.get("traps", [])),
        "wounded": bool(side.get("wounded")),
        "statuses": deepcopy(side.get("statuses", {})),
    }
    if reveal_hand:
        payload["hand"] = deepcopy(side.get("hand", []))
        payload["traps"] = deepcopy(side.get("traps", []))
    else:
        payload["hand_count"] = len(side.get("hand", []))
        payload["traps"] = [
            {"face_down": True, "armed": bool(trap.get("armed", True)), "slot": trap.get("slot")}
            for trap in side.get("traps", [])
        ]
    return payload


def public_state(match):
    validate_phase(match["phase"])
    player = side_payload(match["player"], reveal_hand=True)
    bot = side_payload(match["bot"], reveal_hand=False)
    return {
        "match_id": match["match_id"],
        "architecture": match["architecture"],
        "version": int(match.get("version", 0) or 0),
        "state_hash": state_hash(match),
        "turn": match["turn"],
        "phase": match["phase"],
        "turn_phase": match.get("turn_phase"),
        "player": player,
        "bot": bot,
        "player_field": deepcopy(player["field"]),
        "bot_field": deepcopy(bot["field"]),
        "bot_profile": deepcopy(match.get("bot_profile")),
        "available_evolutions": available_evolutions(match["player"]),
        "last_clash": deepcopy(match.get("last_clash")),
        "result": deepcopy(match.get("result")),
        "winner": match.get("winner"),
        "is_finished": bool(match.get("is_finished")),
        "events": deepcopy(match.get("events", [])[-12:]),
        "log": list(match.get("log", [])[-8:]),
    }
