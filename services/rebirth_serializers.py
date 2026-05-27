from copy import deepcopy

from services.rebirth_contracts import validate_phase
from services.rebirth_domain import CARD_SET_VERSION, ENGINE_VERSION, canonical_state_hash
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

RESOLUTION_PRIORITY_LABELS = {
    1: "Replacement",
    2: "Interrupt / Trap",
    3: "Resposta",
    4: "Efeito ativo",
    5: "Trigger",
    6: "Limpeza",
}
FEEDBACK_EVENT_TYPES = {
    "DAMAGE_RESOLVED",
    "SHIELD_APPLIED",
    "SHIELD_GRANTED",
    "SHIELD_BROKEN",
    "TRAP_TRIGGERED",
    "UNIT_DESTROYED",
    "UNIT_EXHAUSTED",
    "MONSTERS_FUSED",
    "STATUS_APPLIED",
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


def resolution_context(match):
    """Expose authoritative resolution signals for a presentation-only HUD."""
    events = match.get("events") or []
    latest = events[-1] if events else {}
    chain_id = latest.get("effect_chain_id")
    chain_events = [event for event in events if chain_id and event.get("effect_chain_id") == chain_id]
    feedback = [
        {
            "event_type": event.get("event_type") or event.get("type"),
            "target_id": event.get("target_id"),
            "message": event.get("message"),
        }
        for event in chain_events
        if (event.get("event_type") or event.get("type")) in FEEDBACK_EVENT_TYPES
    ][-4:]
    priority = latest.get("priority_level")
    awaiting_player = match.get("phase") == "choose" and not match.get("is_finished")
    has_interrupt = any(int(event.get("priority_level", 0) or 0) == 2 for event in chain_events)
    payload = {
        "current_phase": match.get("turn_phase"),
        "priority_label": "Jogador" if awaiting_player else RESOLUTION_PRIORITY_LABELS.get(priority, "Resolvida"),
        "chain_id": chain_id,
        "chain_event_count": len(chain_events),
        "chain_state": "aguardando acao" if awaiting_player and not chain_id else "resolvida",
        "interrupt_label": "Trap resolvida" if has_interrupt else "Janela fechada",
        "feedback": feedback,
    }
    return payload


def public_state(match):
    validate_phase(match["phase"])
    player = side_payload(match["player"], reveal_hand=True)
    bot = side_payload(match["bot"], reveal_hand=False)
    payload = {
        "match_id": match["match_id"],
        "architecture": match["architecture"],
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "version": int(match.get("version", 0) or 0),
        "state_hash": state_hash(match),
        "canonical_state_hash": canonical_state_hash(match),
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
        "first_duel": bool(match.get("first_duel", False)),
        "replay_audio_muted_mode": bool(match.get("replay_audio_muted_mode", False)),
        "resolution_context": resolution_context(match),
        "checkpoint": deepcopy((match.get("checkpoints") or [None])[-1]),
        "events": deepcopy(match.get("events", [])[-12:]),
        "log": list(match.get("log", [])[-8:]),
    }
    if match.get("campaign_node"):
        payload["campaign"] = {
            "version": match.get("campaign_version"),
            "node_id": match.get("campaign_node"),
            "attempt": int(match.get("campaign_attempt", 1) or 1),
            "modifiers": deepcopy(match.get("campaign_modifiers") or []),
            "presentation": deepcopy(match.get("campaign_presentation") or {}),
        }
        if match.get("is_finished") and match.get("winner") == "bot":
            payload["campaign"]["defeat_advice"] = deepcopy(match.get("campaign_advice") or {})
    return payload
