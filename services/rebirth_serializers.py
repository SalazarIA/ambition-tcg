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
    "UNIT_DAMAGE_RESOLVED",
    "FATIGUE_DAMAGE",
    "BURST_DAMAGE",
    "REGEN_TICK",
    "HAND_MULLIGANED",
    "SHIELD_APPLIED",
    "SHIELD_GRANTED",
    "SHIELD_BROKEN",
    "SHIELD_KEYWORD_BROKEN",
    "TRAP_TRIGGERED",
    "UNIT_DESTROYED",
    "UNIT_EXHAUSTED",
    "MONSTERS_FUSED",
    "STATUS_APPLIED",
}

GAMEPLAY_COMMAND_TYPES = {"PLAY_CARD", "DECLARE_ATTACK", "NEXT_TURN", "EVOLVE_DUPLICATE", "FUSE_FIELD_PAIR"}


def mulligan_available(match):
    if not match or match.get("is_finished") or match.get("mulligan_used"):
        return False
    if int(match.get("turn", 1) or 1) != 1 or match.get("phase") != "choose":
        return False
    for command in match.get("commands") or []:
        if str(command.get("type") or command.get("command_type") or "") in GAMEPLAY_COMMAND_TYPES:
            return False
    return True


def validate_card_contract(card):
    missing = [field for field in REQUIRED_CARD_FIELDS if field not in card]
    if missing:
        raise ValueError(f"Carta Rebirth sem campos obrigatórios: {', '.join(missing)}")
    return card


# audit #4: campos só usados pela engine/bot que não precisam ir no fio. O
# heuristic_vector é input do bot AI; o cliente nunca o lê. Stripá-lo encolhe
# o payload de estado (≈6 chaves por carta × ~16 cartas por resposta) sem
# afetar o canonical_state_hash (calculado à parte em rebirth_domain).
_RUNTIME_STRIP_FIELDS = ("heuristic_vector",)


def _strip_runtime_fields(card):
    if isinstance(card, dict):
        for key in _RUNTIME_STRIP_FIELDS:
            card.pop(key, None)
    return card


def _strip_runtime_cards(cards):
    for card in cards or []:
        _strip_runtime_fields(card)
    return cards


_GRAVEYARD_CARD_FIELDS = (
    "id",
    "instance_id",
    "name",
    "type",
    "card_type",
    "element",
    "tier",
    "attack",
    "guard",
    "cost",
    "art_key",
    "rarity",
)


def _graveyard_card(card):
    return {key: card.get(key) for key in _GRAVEYARD_CARD_FIELDS if card.get(key) is not None}


def side_payload(side, *, reveal_hand=True):
    field = _strip_runtime_cards(deepcopy(field_slots(side)))
    battlefield = _strip_runtime_cards(deepcopy(compact_battlefield(side)))
    # Perf v103: valida o contrato apenas do que ENTRA no payload (mão,
    # campo, traps, played). Deck e descarte inteiros eram ~35 validações
    # extras por request para dados que viram só counts — a engine já os
    # valida ao criar/mutar as cartas.
    for card in side.get("hand", []):
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
        # YGO v104: o cemitério é informação pública dos dois lados — versão
        # compacta (9 campos) para o overlay consultável, não a carta inteira.
        "graveyard": [_graveyard_card(card) for card in side.get("discard", [])],
        "played_card": _strip_runtime_fields(deepcopy(side.get("played_card"))),
        "battlefield": battlefield,
        "field": field,
        "trap_count": len(side.get("traps", [])),
        "wounded": bool(side.get("wounded")),
        "statuses": deepcopy(side.get("statuses", {})),
    }
    if reveal_hand:
        payload["hand"] = _strip_runtime_cards(deepcopy(side.get("hand", [])))
        payload["traps"] = _strip_runtime_cards(deepcopy(side.get("traps", [])))
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
        "chain_state": "aguardando ação" if awaiting_player and not chain_id else "resolvida",
        "interrupt_label": "Trap resolvida" if has_interrupt else "Janela fechada",
        "feedback": feedback,
    }
    return payload


_PUBLIC_EVENT_HEAVY_KEYS = ("card", "cards")


def _slim_public_event(event):
    """Evento para o PAYLOAD público: sem cartas embutidas.

    O front lê type/instance_id/message/resulting_*; cartas completas dentro
    de payload (MONSTER_SUMMONED.card ~1.2KB, CARDS_DRAWN.cards ~1.7KB) só
    importam para o replay — que lê das tabelas match_events, não daqui.
    """
    slim = dict(event)
    payload = slim.get("payload")
    if isinstance(payload, dict) and any(key in payload for key in _PUBLIC_EVENT_HEAVY_KEYS):
        slim["payload"] = {
            key: value for key, value in payload.items() if key not in _PUBLIC_EVENT_HEAVY_KEYS
        }
    return slim


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
        # Perf v103: o front consome os slots no topo (player_field/bot_field);
        # a cópia "field" dentro de cada lado era a MESMA lista 2x por lado
        # (~6KB duplicados por resposta). pop = uma única cópia viaja.
        "player_field": player.pop("field"),
        "bot_field": bot.pop("field"),
        "bot_profile": deepcopy(match.get("bot_profile")),
        "bot_difficulty": deepcopy(match.get("bot_difficulty")),
        "available_evolutions": available_evolutions(match["player"]),
        "last_clash": deepcopy(match.get("last_clash")),
        "result": deepcopy(match.get("result")),
        "winner": match.get("winner"),
        "is_finished": bool(match.get("is_finished")),
        "first_duel": bool(match.get("first_duel", False)),
        "mulligan_available": mulligan_available(match),
        "mulligan_used": bool(match.get("mulligan_used", False)),
        "replay_audio_muted_mode": bool(match.get("replay_audio_muted_mode", False)),
        "resolution_context": resolution_context(match),
        "checkpoint": deepcopy((match.get("checkpoints") or [None])[-1]),
        "events": [_slim_public_event(event) for event in match.get("events", [])[-12:]],
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
