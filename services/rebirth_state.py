from copy import deepcopy
from enum import Enum
import hashlib
import uuid

from services.rebirth_contracts import PHASE_CHOOSE
from services.rebirth_cards import build_deck, catalog_payload
from services.rebirth_bot import choose_personality, personality_payload
from services.rebirth_events import append_event, append_snapshot, ensure_event_contract


STARTING_HP = 30
HAND_SIZE = 5
FIELD_SLOT_COUNT = 3


class TurnPhase(Enum):
    DRAW_PHASE = "DRAW_PHASE"
    MAIN_PHASE = "MAIN_PHASE"
    COMBAT_PHASE = "COMBAT_PHASE"
    END_PHASE = "END_PHASE"


class RebirthStateError(ValueError):
    pass


def _match_id(seed=None):
    if seed is None:
        return f"rebirth-{uuid.uuid4().hex[:12]}"
    digest = hashlib.sha256(str(seed).encode("utf-8")).hexdigest()[:12]
    return f"rebirth-{digest}"


def create_player(name, owner, card_ids=None):
    return {
        "name": name,
        "hp": STARTING_HP,
        "max_hp": STARTING_HP,
        "energy": 2,
        "max_energy": 2,
        "deck": build_deck(owner, card_ids=card_ids),
        "hand": [],
        "battlefield": [],
        "field": [None for _ in range(FIELD_SLOT_COUNT)],
        "discard": [],
        "played_card": None,
        "traps": [],
        "statuses": {},
        "wounded": False,
    }


def field_slots(side):
    raw_slots = side.get("field")
    raw_slots = raw_slots if isinstance(raw_slots, list) else []
    seen = set()
    compact = []
    for source in (side.get("battlefield", []), raw_slots):
        for card in source or []:
            if not card:
                continue
            key = card.get("instance_id") or card.get("id") or id(card)
            if key in seen:
                continue
            seen.add(key)
            compact.append(card)

    slots = [None for _ in range(FIELD_SLOT_COUNT)]
    # Respect each card's saved field_slot when valid and free; otherwise place
    # in the first empty slot. Falling back to "first empty" handles legacy state
    # that didn't carry field_slot and keeps survivors stable across redraws.
    for card in compact[:FIELD_SLOT_COUNT]:
        card["exhausted"] = bool(card.get("exhausted", False))
        card["has_attacked"] = bool(card.get("has_attacked", False))
        # Preserve the lock for legacy persisted attackers that predate
        # has_acted instead of reopening an already spent action.
        card["has_acted"] = bool(card.get("has_acted", card["has_attacked"]))
        raw = card.get("field_slot")
        index = int(raw) if isinstance(raw, int) or (isinstance(raw, str) and raw.isdigit()) else None
        if index is None or not (0 <= index < FIELD_SLOT_COUNT) or slots[index] is not None:
            index = next((i for i, slot in enumerate(slots) if slot is None), None)
        if index is None:
            break
        slots[index] = card
        card["field_slot"] = index
        card["slot"] = index + 1
    side["field"] = slots
    return slots


def compact_battlefield(side):
    side["battlefield"] = [card for card in field_slots(side) if card]
    return side["battlefield"]


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


def create_match(seed=None, player_card_ids=None, player_name="Você", bot_profile_id=None):
    match_id = _match_id(seed)
    deck_ids = None
    if player_card_ids:
        deck_ids = list(player_card_ids)
    player = create_player(player_name, "player", card_ids=deck_ids)
    bot = create_player("Bot", "bot")
    draw_to_hand_size(player)
    draw_to_hand_size(bot)
    bot_profile = personality_payload(bot_profile_id or choose_personality(seed=seed, match_id=match_id))

    match = {
        "match_id": match_id,
        "architecture": "Ambitionz Rebirth",
        "seed": str(seed or ""),
        "turn": 1,
        "phase": PHASE_CHOOSE,
        "turn_phase": TurnPhase.MAIN_PHASE.value,
        "player": player,
        "bot": bot,
        "bot_profile": bot_profile,
        "last_clash": None,
        "result": None,
        "winner": None,
        "is_finished": False,
        "log": [
            "Turno 01   Duelo Rebirth iniciado.",
            "Turno 01   Escolha uma carta.",
        ],
        "catalog": catalog_payload(),
    }
    ensure_event_contract(match)
    append_event(
        match,
        "MATCH_STARTED",
        payload={
            "seed": str(seed or ""),
            "player_name": player_name,
            "bot_profile_id": bot_profile["id"],
            "player_deck_count": len(player["deck"]) + len(player["hand"]),
            "bot_deck_count": len(bot["deck"]) + len(bot["hand"]),
        },
        message="Duelo Rebirth iniciado.",
    )
    append_snapshot(match, "match_started")
    return match


def set_turn_phase(match, phase):
    phase_value = phase.value if isinstance(phase, TurnPhase) else str(phase or "")
    if phase_value not in {item.value for item in TurnPhase}:
        raise RebirthStateError(f"Fase de turno inválida: {phase_value}")
    match["turn_phase"] = phase_value
    return match


def current_turn_phase(match):
    return str(match.get("turn_phase") or TurnPhase.MAIN_PHASE.value)


def is_main_phase(match):
    return current_turn_phase(match) == TurnPhase.MAIN_PHASE.value


def remove_from_hand(player, *, card_instance_id=None, card_id=None):
    for index, card in enumerate(player["hand"]):
        if card_instance_id and card["instance_id"] == card_instance_id:
            return player["hand"].pop(index)
        if not card_instance_id and card_id and card["id"] == card_id:
            return player["hand"].pop(index)
    raise RebirthStateError("A carta não está na mão.")


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
    match["player"]["played_card"] = None
    match["bot"]["played_card"] = None


def side_payload(side, *, reveal_hand=True):
    field = deepcopy(field_slots(side))
    battlefield = deepcopy(compact_battlefield(side))
    payload = {
        "name": side["name"],
        "hp": side["hp"],
        "max_hp": side.get("max_hp", STARTING_HP),
        "energy": int(side.get("energy", 0) or 0),
        "max_energy": int(side.get("max_energy", 0) or 0),
        "deck_count": len(side["deck"]),
        "discard_count": len(side["discard"]),
        "played_card": deepcopy(side.get("played_card")),
        "battlefield": battlefield,
        "field": field,
        "trap_count": len(side.get("traps", [])),
        "wounded": bool(side.get("wounded")),
        "statuses": deepcopy(side.get("statuses", {})),
    }
    if reveal_hand:
        payload["hand"] = deepcopy(side["hand"])
        payload["traps"] = deepcopy(side.get("traps", []))
    else:
        payload["hand_count"] = len(side["hand"])
        payload["traps"] = [
            {"face_down": True, "armed": bool(trap.get("armed", True)), "slot": trap.get("slot")}
            for trap in side.get("traps", [])
        ]
    return payload


def public_state(match):
    from services.rebirth_serializers import public_state as serialize_public_state

    return serialize_public_state(match)
