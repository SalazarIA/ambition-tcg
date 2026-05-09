# =========================================================
# Ambitionz Battle Engine V1 Adapter
# Converts isolated battle_engine_v1 state into Arena Clean V50 payload.
# =========================================================

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from services.battle_engine_v1 import (
    choose_action,
    create_match,
    playable_cards,
    resolve_round,
    start_round,
    bot_choose_action,
    serialize_state,
)

ARENA_CLEAN_SCHEMA = "ambitionz_arena_clean_v50"


def _battle_card_to_arena_card(card: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    card = card or {}
    card_id = str(card.get("id") or f"be1-card-{index}")

    damage = int(card.get("damage") or 0)
    guard = int(card.get("guard") or 0)
    ambition = int(card.get("ambition") or 0)

    stat = max(1, damage, guard, ambition)

    card_type = "Monster" if damage > 0 else "Spell"
    sigil = "Strike" if damage > 0 else ("Guard" if guard > 0 else "Focus")

    return {
        "id": card_id,
        "card_id": card_id,
        "name": str(card.get("name") or card_id),
        "type": card_type,
        "element": "Neutral",
        "rarity": "Beta",
        "sigil": sigil,
        "role": str(card.get("type") or "battle"),
        "cost": int(card.get("cost") or 0),
        "power": stat,
        "attack": damage,
        "value": stat,
        "combat_label": "DMG" if damage > 0 else ("GRD" if guard > 0 else "AMB"),
        "display_stat": stat,
        "effect": f"Damage {damage} / Guard {guard} / Ambition {ambition}",
        "description": f"Damage {damage} / Guard {guard} / Ambition {ambition}",
        "image": "cards/placeholders/card_placeholder.svg",
        "set_key": "battle_engine_v1",
        "set_name": "Battle Engine V1",
        "is_monster": damage > 0,
    }


def _field_from_played_card(player: Dict[str, Any]) -> Dict[str, Any]:
    played = player.get("played_card")
    if not played:
        return {"monster": None, "spell": None, "trap": None}

    arena_card = _battle_card_to_arena_card(played)

    if int(played.get("damage") or 0) > 0:
        return {"monster": arena_card, "spell": None, "trap": None}

    if int(played.get("guard") or 0) > 0:
        return {"monster": None, "spell": None, "trap": arena_card}

    return {"monster": None, "spell": arena_card, "trap": None}


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
        "intent": str(player.get("intent") or ""),
        "ready": bool(player.get("intent")),
        "hand": [
            _battle_card_to_arena_card(card, index=index)
            for index, card in enumerate(hand)
        ] if viewer else [],
        "hand_count": len(hand),
        "field": _field_from_played_card(player),
        "deck_count": len(player.get("deck") or []),
        "graveyard_count": len(player.get("discard") or []),
    }


def build_be1_arena_payload(match: Dict[str, Any], message: Optional[str] = None) -> Dict[str, Any]:
    public_state = serialize_state(match, public_only=False)
    player = public_state["player"]
    enemy = public_state["opponent"]

    playable = playable_cards(player)
    playable_ids = [str(card.get("id")) for card in playable]

    phase = public_state.get("phase") or "start"

    can_choose = phase in {"round_start", "choose_action"} and not public_state.get("winner")
    can_ready = phase in {"round_start", "choose_action"} and not public_state.get("winner")
    show_start = phase == "created"

    if public_state.get("winner"):
        show_start = False
        can_choose = False
        can_ready = False

    final_message = message
    if not final_message:
        if public_state.get("winner"):
            final_message = f"Match finished. Winner: {public_state.get('winner')}."
        elif phase in {"round_start", "choose_action"}:
            final_message = "Choose an intent, play one card, then press Ready."
        else:
            final_message = "Battle Engine V1 active."

    return {
        "schema": ARENA_CLEAN_SCHEMA,
        "engine": "battle_engine_v1",
        "mode": "training",
        "phase": "finished" if public_state.get("winner") else phase,
        "round": int(public_state.get("round") or 0),
        "message": final_message,
        "winner": public_state.get("winner"),
        "reason": public_state.get("reason"),
        "me": _player_payload(player, viewer=True),
        "enemy": _player_payload(enemy, viewer=False),
        "legal_actions": {
            "show_start": show_start,
            "can_start": show_start,
            "show_intents": can_choose,
            "can_choose_intent": can_choose,
            "show_ready": can_ready,
            "can_ready": can_ready,
            "playable_card_ids": playable_ids,
        },
        "log": list(public_state.get("log") or [])[-8:],
    }


def create_be1_training_match(user=None, sid: Optional[str] = None) -> Dict[str, Any]:
    player_name = getattr(user, "username", None) or getattr(user, "email", None) or "Player"
    match = create_match(player_name=player_name, opponent_name="Ambitionz Bot")
    match["be1"] = True
    match["sid"] = sid
    match["room_code"] = f"be1_training_{sid}" if sid else "be1_training"
    match["player"]["sid"] = sid
    match["player"]["user_id"] = getattr(user, "id", None)
    match["phase"] = "created"
    return match


def be1_start(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)
    return match


def be1_set_intent(match: Dict[str, Any], intent: str) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    if intent not in {"Strike", "Guard", "Focus"}:
        raise ValueError(f"Invalid intent: {intent}")

    # UI behavior: selecting intent must NOT auto-play a card.
    match["player"]["intent"] = intent
    match["log"].append(f"{match['player']['name']} selected {intent}.")
    return match


def be1_play_card(match: Dict[str, Any], card_id: Optional[str] = None, card_index: Optional[int] = None) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    player = match["player"]

    if not player.get("intent"):
        player["intent"] = "Strike"

    hand = player.get("hand") or []

    selected_index = None

    if card_index is not None:
        try:
            selected_index = int(card_index)
        except Exception:
            selected_index = None

    if selected_index is None and card_id:
        for idx, card in enumerate(hand):
            if str(card.get("id")) == str(card_id):
                selected_index = idx
                break

    if selected_index is None:
        cards = playable_cards(player)
        if not cards:
            return match
        selected = cards[0]
        selected_index = hand.index(selected)

    # If choose_action already selected intent but no card, this second call is safe for card selection.
    choose_action(match, "player", player.get("intent") or "Strike", selected_index)
    return match


def be1_ready(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    # Pressing Ready without a selected intent defaults to Focus,
    # but it must not auto-play a card.
    if not match["player"].get("intent"):
        match["player"]["intent"] = "Focus"
        match["log"].append(f"{match['player']['name']} selected Focus.")

    if not match["opponent"].get("intent"):
        bot_choose_action(match)

    resolve_round(match)

    if not match.get("winner"):
        start_round(match)

    return match
