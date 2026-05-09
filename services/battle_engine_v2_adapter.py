# =========================================================
# Ambitionz Battle Engine V2 Adapter
# Converts BE2 card battler state into Arena Clean V50 payload.
# =========================================================

from __future__ import annotations

from typing import Any, Dict, Optional

from services.battle_engine_v2 import (
    ENGINE_VERSION,
    UNLEASH_COST,
    choose_intent,
    create_match,
    play_card,
    playable_cards,
    request_unleash,
    resolve_round,
    start_round,
    serialize_state,
)

ARENA_CLEAN_SCHEMA = "ambitionz_arena_clean_v50"


def _card_stat(card: Dict[str, Any]) -> int:
    if not card:
        return 0

    return max(
        int(card.get("atk") or 0),
        int(card.get("damage") or 0),
        int(card.get("shield") or 0),
        int(card.get("current_hp") or 0),
        int(card.get("hp") or 0),
        int(card.get("ambition") or 0),
        1,
    )


def _card_label(card: Dict[str, Any]) -> str:
    kind = (card or {}).get("kind")

    if kind == "creature":
        return "ATK"
    if kind == "guard":
        return "SHD"
    if kind == "spell":
        return "DMG" if int((card or {}).get("damage") or 0) > 0 else "AMB"
    if kind == "support":
        return "SUP"

    return "VAL"


def _card_type(card: Dict[str, Any]) -> str:
    kind = (card or {}).get("kind")

    if kind == "creature":
        return "Monster"
    if kind == "guard":
        return "Trap"
    if kind == "support":
        return "Spell"
    if kind == "spell":
        return "Spell"

    return "Spell"


def _card_sigil(card: Dict[str, Any]) -> str:
    kind = (card or {}).get("kind")

    if kind == "creature":
        return "Creature"
    if kind == "guard":
        return "Guard"
    if kind == "support":
        return "Support"
    if int((card or {}).get("damage") or 0) > 0:
        return "Damage"

    return "Focus"


def _battle_card_to_arena_card(card: Optional[Dict[str, Any]], index: int = 0) -> Optional[Dict[str, Any]]:
    if not card:
        return None

    card_id = str(card.get("id") or f"be2-card-{index}")
    stat = _card_stat(card)

    hp = int(card.get("hp") or card.get("current_hp") or 0)
    current_hp = int(card.get("current_hp") or hp or 0)
    atk = int(card.get("atk") or card.get("damage") or 0)

    details = []

    if card.get("kind") == "creature":
        details.append(f"ATK {atk}")
        details.append(f"HP {current_hp}/{hp}")
    else:
        if card.get("damage"):
            details.append(f"Damage {card.get('damage')}")
        if card.get("shield"):
            details.append(f"Shield {card.get('shield')}")
        if card.get("ambition"):
            details.append(f"Ambition {card.get('ambition')}")

    text = card.get("text") or " / ".join(details)

    return {
        "id": card_id,
        "card_id": card_id,
        "name": str(card.get("name") or card_id),
        "type": _card_type(card),
        "element": "Neutral",
        "rarity": "Beta",
        "sigil": _card_sigil(card),
        "role": str(card.get("kind") or "card"),
        "cost": int(card.get("cost") or 0),
        "power": stat,
        "attack": atk,
        "value": stat,
        "combat_label": _card_label(card),
        "display_stat": stat,
        "effect": text,
        "description": text,
        "image": "cards/placeholders/card_placeholder.svg",
        "set_key": "battle_engine_v2",
        "set_name": "Battle Engine V2",
        "is_monster": card.get("kind") == "creature",
        "current_hp": current_hp,
        "max_hp": hp,
        "atk": atk,
        "kind": card.get("kind"),
    }


def _field_payload(player: Dict[str, Any]) -> Dict[str, Any]:
    field = player.get("field") or {}

    return {
        "monster": _battle_card_to_arena_card(field.get("active"), 0),
        "spell": _battle_card_to_arena_card(field.get("support"), 1),
        "trap": None,
    }


def _player_payload(player: Dict[str, Any], viewer: bool) -> Dict[str, Any]:
    hand = player.get("hand") or []

    return {
        "sid": player.get("sid"),
        "user_id": player.get("user_id"),
        "name": str(player.get("name") or ("You" if viewer else "Opponent")),
        "hp": int(player.get("hp") or 0),
        "energy": int(player.get("energy") or 0),
        "max_energy": int(player.get("max_energy") or player.get("energy") or 0),
        "ambition": int(player.get("ambition") or 0),
        "shield": int(player.get("shield") or 0),
        "intent": str(player.get("intent") or ""),
        "ready": bool(player.get("intent")),
        "hand": [
            _battle_card_to_arena_card(card, index=index)
            for index, card in enumerate(hand)
        ] if viewer else [],
        "hand_count": len(hand),
        "field": _field_payload(player),
        "deck_count": len(player.get("deck") or []),
        "graveyard_count": len(player.get("discard") or []),
        "can_unleash": int(player.get("ambition") or 0) >= UNLEASH_COST,
    }


def build_be2_arena_payload(match: Dict[str, Any], message: Optional[str] = None) -> Dict[str, Any]:
    state = serialize_state(match, public_only=False)
    player = state["player"]
    enemy = state["opponent"]

    playable_ids = [str(card.get("id")) for card in playable_cards(player)]
    phase = "finished" if state.get("winner") else (state.get("phase") or "start")

    can_act = phase in {"created", "round_start", "choose_action"} and not state.get("winner")
    can_unleash = int(player.get("ambition") or 0) >= UNLEASH_COST and not state.get("winner")

    enemy_preview = state.get("enemy_preview") or {}

    final_message = message

    if not final_message:
        if state.get("winner"):
            final_message = f"Match finished. Winner: {state.get('winner')}."
        elif enemy_preview.get("message"):
            final_message = enemy_preview["message"]
        else:
            final_message = "Summon creatures, cast spells and press Ready."

    return {
        "schema": ARENA_CLEAN_SCHEMA,
        "engine": ENGINE_VERSION,
        "mode": "training",
        "phase": phase,
        "round": int(state.get("round") or 0),
        "message": final_message,
        "winner": state.get("winner"),
        "reason": state.get("reason"),
        "enemy_preview": enemy_preview,
        "unleash_cost": UNLEASH_COST,
        "me": _player_payload(player, viewer=True),
        "enemy": _player_payload(enemy, viewer=False),
        "legal_actions": {
            "show_start": phase == "created",
            "can_start": phase == "created",
            "show_intents": can_act,
            "can_choose_intent": can_act,
            "show_ready": can_act,
            "can_ready": can_act,
            "can_unleash": can_unleash,
            "playable_card_ids": playable_ids,
        },
        "log": list(state.get("log") or [])[-10:],
    }


def create_be2_training_match(user=None, sid: Optional[str] = None) -> Dict[str, Any]:
    player_name = getattr(user, "username", None) or getattr(user, "email", None) or "Player"
    user_id = getattr(user, "id", None)
    match = create_match(player_name=player_name, opponent_name="Ambitionz Bot", player_sid=sid, user_id=user_id)
    match["be2"] = True
    match["room_code"] = f"be2_training_{sid}" if sid else "be2_training"
    return match


def be2_start(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)
    return match


def be2_set_intent(match: Dict[str, Any], intent: str) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    choose_intent(match, "player", intent)
    return match


def be2_play_card(match: Dict[str, Any], card_id: Optional[str] = None, card_index: Optional[int] = None) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    play_card(match, "player", card_id=card_id, card_index=card_index)
    return match


def be2_unleash(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    request_unleash(match, "player")
    return match


def be2_ready(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    if not match["player"].get("intent"):
        choose_intent(match, "player", "Focus")

    resolve_round(match)
    return match
