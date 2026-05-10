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


def attach_legacy_match_aliases(match: Dict[str, Any]) -> Dict[str, Any]:
    """Expose p1/p2/logs aliases while BE2 remains the canonical state."""
    match["p1"] = match["player"]
    match["p2"] = match["opponent"]
    match["logs"] = match["log"]
    match.setdefault("resolving", False)
    return match


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
        "element": str(card.get("element") or "Neutral"),
        "rarity": str(card.get("rarity") or "Beta"),
        "sigil": str(card.get("sigil") or _card_sigil(card)),
        "role": str(card.get("role") or card.get("kind") or "card"),
        "cost": int(card.get("cost") or 0),
        "power": stat,
        "attack": atk,
        "value": stat,
        "combat_label": _card_label(card),
        "display_stat": stat,
        "effect": text,
        "description": text,
        "image": str(card.get("image") or "cards/placeholders/card_placeholder.svg"),
        "set_key": str(card.get("source") or "battle_engine_v2"),
        "set_name": "Official Catalog" if card.get("source") == "official_catalog" else "Battle Engine V2",
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
        "intent": str(player.get("intent") or "") if viewer else "Hidden",
        "ready": bool(player.get("ready") or player.get("intent")),
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


def _opposite_side(side: str) -> str:
    return "opponent" if side == "player" else "player"


def _winner_for_viewer(winner: Optional[str], viewer_side: str) -> Optional[str]:
    if not winner:
        return None
    if winner == "draw":
        return "draw"
    return "player" if winner == viewer_side else "opponent"


def _summary_for_viewer(summary: Dict[str, Any], viewer_side: str) -> Dict[str, Any]:
    if viewer_side == "player" or not summary:
        return summary

    player_lost = max(0, int(summary.get("player_hp_before") or 0) - int(summary.get("player_hp_after") or 0))
    enemy_lost = max(0, int(summary.get("enemy_hp_before") or 0) - int(summary.get("enemy_hp_after") or 0))

    return {
        **summary,
        "player_intent": summary.get("enemy_intent"),
        "enemy_intent": summary.get("player_intent"),
        "player_card": summary.get("enemy_card"),
        "enemy_card": summary.get("player_card"),
        "player_attack": summary.get("enemy_attack"),
        "enemy_attack": summary.get("player_attack"),
        "short_result": f"You dealt {player_lost} HP damage. Enemy dealt {enemy_lost} HP damage.",
        "lines": [
            f"You chose {summary.get('enemy_intent') or 'Focus'} and played {summary.get('enemy_card') or 'No card'}.",
            f"Enemy chose {summary.get('player_intent') or 'Focus'} and played {summary.get('player_card') or 'No card'}.",
            f"You dealt {player_lost} HP damage. Enemy dealt {enemy_lost} HP damage.",
        ],
    }


def side_for_sid(match: Dict[str, Any], sid: Optional[str]) -> str:
    if sid and str((match.get("opponent") or {}).get("sid")) == str(sid):
        return "opponent"
    return "player"


def build_be2_arena_payload(
    match: Dict[str, Any],
    message: Optional[str] = None,
    viewer_side: str = "player",
) -> Dict[str, Any]:
    state = serialize_state(match, public_only=False)
    viewer_side = viewer_side if viewer_side in {"player", "opponent"} else "player"
    enemy_side = _opposite_side(viewer_side)
    player = state[viewer_side]
    enemy = state[enemy_side]

    raw_phase = state.get("phase") or "start"
    phase = "finished" if state.get("winner") else ("main" if raw_phase in {"created", "round_start", "choose_action"} else raw_phase)
    is_finished = phase == "finished" or bool(state.get("winner"))

    playable_ids = [] if is_finished or player.get("ready") else [str(card.get("id")) for card in playable_cards(player)]

    can_act = raw_phase in {"created", "round_start", "choose_action"} and not is_finished and not player.get("ready")
    can_play_cards = bool(playable_ids) and can_act
    can_unleash = int(player.get("ambition") or 0) >= UNLEASH_COST and not is_finished

    enemy_preview = state.get("enemy_preview") or {}
    if not enemy.get("is_bot"):
        enemy_preview = {
            "intent": "Hidden" if enemy.get("intent") else "",
            "message": "Opponent is choosing their line.",
        }

    final_message = message

    if not final_message:
        summary = state.get("round_summary") or {}

        if state.get("winner"):
            final_message = summary.get("short_result") or f"Match finished. Winner: {_winner_for_viewer(state.get('winner'), viewer_side)}."
        elif summary.get("short_result"):
            final_message = summary["short_result"]
        elif enemy_preview.get("message"):
            final_message = enemy_preview["message"]
        else:
            final_message = "Choose a tactic: Strike attacks harder, Guard blocks damage, Focus charges Unleash."

    return {
        "schema": ARENA_CLEAN_SCHEMA,
        "engine": ENGINE_VERSION,
        "mode": "training",
        "phase": phase,
        "round": int(state.get("round") or 0),
        "message": final_message,
        "winner": _winner_for_viewer(state.get("winner"), viewer_side),
        "reason": state.get("reason"),
        "enemy_preview": enemy_preview,
        "round_summary": _summary_for_viewer(state.get("round_summary") or {}, viewer_side),
        "help": {
            "turn_order": [
                "1. Choose Strike, Guard or Focus.",
                "2. Play one card if you can.",
                "3. Press Ready to resolve combat.",
            ],
            "actions": {
                "Strike": "+2 attack this round.",
                "Guard": "+4 shield this round.",
                "Focus": "+3 Ambition. Ambition charges Unleash.",
                "Ready": "Resolves your action and the enemy action.",
            },
            "goal": "Destroy enemy creatures, damage enemy HP, and use Unleash to finish the duel.",
        },
        "unleash_cost": UNLEASH_COST,
        "me": _player_payload(player, viewer=True),
        "enemy": _player_payload(enemy, viewer=False),
        "legal_actions": {
            "show_start": phase == "created",
            "can_start": phase == "created",
            "show_intents": can_act,
            "can_choose_intent": can_act,
            "can_play_cards": can_play_cards,
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
    match["training"] = True
    match["is_bot_match"] = True
    match["bot_difficulty"] = "normal"
    match["room_code"] = f"be2_training_{sid}" if sid else "be2_training"
    return attach_legacy_match_aliases(match)


def create_be2_bot_match(user=None, sid: Optional[str] = None, room_code: Optional[str] = None, matchmaking_fallback: bool = False) -> Dict[str, Any]:
    match = create_be2_training_match(user=user, sid=sid)
    match["training"] = bool(matchmaking_fallback)
    match["matchmaking_fallback"] = bool(matchmaking_fallback)
    match["room_code"] = room_code or (f"be2_bot_{sid}" if sid else "be2_bot")
    return match


def create_be2_match_from_players(waiting_player: Dict[str, Any], player_object: Dict[str, Any], room_code: str) -> Dict[str, Any]:
    match = create_match(
        player_name=str(waiting_player.get("name") or "Player 1"),
        opponent_name=str(player_object.get("name") or "Player 2"),
        player_sid=waiting_player.get("sid"),
        user_id=waiting_player.get("user_id"),
        opponent_sid=player_object.get("sid"),
        opponent_user_id=player_object.get("user_id"),
        opponent_is_bot=False,
    )
    match["be2"] = True
    match["is_bot_match"] = False
    match["room_code"] = room_code
    return attach_legacy_match_aliases(match)


def be2_start(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)
    return match


def be2_set_intent(match: Dict[str, Any], intent: str, side: str = "player") -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    choose_intent(match, side if side in {"player", "opponent"} else "player", intent)
    return match


def be2_play_card(match: Dict[str, Any], card_id: Optional[str] = None, card_index: Optional[int] = None, side: str = "player") -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    play_card(match, side if side in {"player", "opponent"} else "player", card_id=card_id, card_index=card_index)
    return match


def be2_unleash(match: Dict[str, Any], side: str = "player") -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    request_unleash(match, side if side in {"player", "opponent"} else "player")
    return match


def be2_ready(match: Dict[str, Any], side: str = "player") -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    side = side if side in {"player", "opponent"} else "player"
    other_side = _opposite_side(side)

    if not match[side].get("intent"):
        choose_intent(match, side, "Focus")

    match[side]["ready"] = True

    if match[other_side].get("is_bot"):
        resolve_round(match)
        return match

    if match[other_side].get("ready"):
        if not match[other_side].get("intent"):
            choose_intent(match, other_side, "Focus")
        resolve_round(match)

    return match
