# =========================================================
# Ambitionz Battle Engine V2 Adapter
# Converts BE2 card battler state into Arena Clean V50 payload.
# =========================================================

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from services.battle_engine_v2 import (
    CARD_REGISTRY_SCHEMA,
    ENGINE_VERSION,
    KEYWORD_REGISTRY_SCHEMA,
    KEYWORD_REGISTRY_V1,
    LANES,
    TRAINING_BOT_HP,
    UNLEASH_COST,
    choose_intent,
    create_match,
    empty_lanes,
    ensure_board,
    play_card,
    playable_cards,
    request_unleash,
    resolve_round,
    start_round,
    serialize_state,
)

ARENA_CLEAN_SCHEMA = "ambitionz_arena_clean_v50"
STATIC_IMG_DIR = Path(__file__).resolve().parents[1] / "static" / "img"


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


def _card_image(card: Dict[str, Any]) -> str:
    image = str((card or {}).get("image") or "").strip().lstrip("/")
    if image and (STATIC_IMG_DIR / image).exists():
        return image

    element = str((card or {}).get("element") or "Neutral").strip().lower()
    if element not in {"fire", "water", "earth", "plant", "global", "neutral"}:
        element = "neutral"
    return f"cards/elemental/{element}.svg"


def _card_effect_summary(card: Dict[str, Any]) -> str:
    kind = (card or {}).get("kind")

    if kind == "creature":
        return f"Summon {int(card.get('atk') or 0)} ATK / {int(card.get('hp') or 0)} HP."
    if kind == "support":
        bonus = int(card.get("atk_bonus") or 0)
        ambition = int(card.get("ambition_bonus") or 0)
        parts = []
        if bonus:
            parts.append(f"+{bonus} ATK while in play")
        if ambition:
            parts.append(f"+{ambition} Ambition each round")
        return "Support: " + (", ".join(parts) if parts else "stays on your spell slot.")
    if kind == "guard":
        parts = []
        if int(card.get("shield") or 0):
            parts.append(f"+{int(card.get('shield') or 0)} shield")
        if int(card.get("damage") or 0):
            parts.append(f"{int(card.get('damage') or 0)} counter damage")
        return "Guard: " + (", ".join(parts) if parts else "defensive response.")

    parts = []
    if int(card.get("damage") or 0):
        parts.append(f"{int(card.get('damage') or 0)} damage")
    if int(card.get("shield") or 0):
        parts.append(f"+{int(card.get('shield') or 0)} shield")
    if int(card.get("ambition") or 0):
        parts.append(f"+{int(card.get('ambition') or 0)} Ambition")
    if int(card.get("draw") or 0):
        parts.append(f"draw {int(card.get('draw') or 0)}")
    return "Spell: " + (", ".join(parts) if parts else "instant effect.")


def _card_preview(card: Dict[str, Any], intent: Optional[str] = None, owner: Optional[Dict[str, Any]] = None) -> str:
    intent = intent or "Focus"
    kind = (card or {}).get("kind")

    if kind == "creature":
        lanes = empty_lanes(owner or {}) if owner is not None else list(LANES)
        if not lanes:
            return "No empty lane available for this creature."
        return f"Enters an empty lane with {int(card.get('atk') or 0)} attack and {int(card.get('hp') or 0)} HP."

    damage = int(card.get("damage") or 0)
    shield = int(card.get("shield") or 0)
    ambition = int(card.get("ambition") or 0)

    if card.get("id") == "pressure_move" and intent == "Strike":
        damage += 1
    if intent == "Guard":
        shield += 2
    if intent == "Focus":
        ambition += 1

    parts = []
    if damage:
        parts.append(f"deal {damage} damage")
    if shield:
        parts.append(f"gain {shield} shield")
    if ambition:
        parts.append(f"gain {ambition} Ambition")
    if int(card.get("draw") or 0):
        parts.append(f"draw {int(card.get('draw') or 0)}")

    if not parts:
        return _card_effect_summary(card)

    return f"With {intent}: " + ", ".join(parts) + "."


def _battle_card_to_arena_card(
    card: Optional[Dict[str, Any]],
    index: int = 0,
    intent: Optional[str] = None,
    owner: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if not card:
        return None

    catalog_id = str(card.get("card_id") or card.get("id") or f"be2-card-{index}")
    runtime_id = str(card.get("instance_id") or card.get("id") or catalog_id)
    stat = _card_stat(card)

    hp = int(card.get("max_hp") or card.get("hp") or card.get("current_hp") or 0)
    current_hp = int(card.get("current_hp") if card.get("current_hp") is not None else (hp or 0))
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

    effect_summary = _card_effect_summary(card)
    text = effect_summary or card.get("text") or " / ".join(details)
    keywords = list(card.get("keywords") or [])
    keyword_text = [
        str((KEYWORD_REGISTRY_V1.get(keyword) or {}).get("name") or keyword)
        for keyword in keywords
    ]

    return {
        "id": runtime_id,
        "card_id": catalog_id,
        "instance_id": str(card.get("instance_id") or ""),
        "name": str(card.get("name") or catalog_id),
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
        "description": str(card.get("text") or text),
        "effect_summary": effect_summary,
        "preview": _card_preview(card, intent=intent, owner=owner),
        "image": _card_image(card),
        "set_key": str(card.get("source") or "battle_engine_v2"),
        "set_name": "Official Catalog" if card.get("source") == "official_catalog" else "Battle Engine V2",
        "is_monster": card.get("kind") == "creature",
        "current_hp": current_hp,
        "max_hp": hp,
        "atk": atk,
        "kind": card.get("kind"),
        "owner": card.get("owner"),
        "lane": card.get("lane"),
        "keywords": keywords,
        "keyword_text": keyword_text,
        "exhausted": bool(card.get("exhausted")),
        "played_round": int(card.get("played_round") or 0),
        "registry": str(card.get("registry") or CARD_REGISTRY_SCHEMA),
        "registry_version": str(card.get("registry_version") or "v1"),
    }


def _field_payload(player: Dict[str, Any]) -> Dict[str, Any]:
    field = player.get("field") or {}
    board = _board_payload(player)
    first_creature = next((board[lane] for lane in LANES if board.get(lane)), None)

    return {
        "monster": board.get("center") or first_creature,
        "spell": _battle_card_to_arena_card(field.get("support"), 1, owner=player),
        "trap": None,
        "lanes": board,
        "board": board,
    }


def _board_payload(player: Dict[str, Any]) -> Dict[str, Optional[Dict[str, Any]]]:
    board = ensure_board(player)
    return {
        lane: _battle_card_to_arena_card(board.get(lane), index=index, owner=player)
        for index, lane in enumerate(LANES)
    }


def _player_payload(player: Dict[str, Any], viewer: bool) -> Dict[str, Any]:
    hand = player.get("hand") or []
    board = _board_payload(player)

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
        "ready": bool(player.get("ready")),
        "hand": [
            _battle_card_to_arena_card(card, index=index, intent=player.get("intent"), owner=player)
            for index, card in enumerate(hand)
        ] if viewer else [],
        "hand_count": len(hand),
        "field": _field_payload(player),
        "board": board,
        "deck_count": len(player.get("deck") or []),
        "graveyard_count": len(player.get("discard") or []),
        "can_unleash": int(player.get("ambition") or 0) >= UNLEASH_COST,
        "played_this_round": bool(player.get("played_this_round")),
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
    if not summary:
        return summary

    if viewer_side == "player":
        return {
            **summary,
            "events": _events_for_viewer(summary.get("events") or [], viewer_side),
        }

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
        "events": _events_for_viewer(summary.get("events") or [], viewer_side),
    }


def _event_actor_label(actor: Optional[str], viewer_side: str) -> str:
    if actor == viewer_side:
        return "You"
    if actor in {"player", "opponent"}:
        return "Enemy"
    return ""


def _events_for_viewer(events: List[Dict[str, Any]], viewer_side: str) -> List[Dict[str, Any]]:
    mapped = []
    for event in events:
        actor = event.get("actor")
        target = event.get("target")
        mapped.append({
            **event,
            "actor_label": _event_actor_label(actor, viewer_side),
            "target_label": _event_actor_label(target, viewer_side),
        })
    return mapped


def _combat_log_for_payload(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    combat_log = [
        event for event in (state.get("combat_log") or [])
        if isinstance(event, dict)
    ]

    if not combat_log:
        return []

    completed_rounds = [
        int(event.get("round") or 0)
        for event in combat_log
        if event.get("type") == "round_end"
    ]

    if not completed_rounds:
        return []

    last_completed_round = completed_rounds[-1]
    return [
        dict(event)
        for event in combat_log
        if int(event.get("round") or 0) == last_completed_round
    ][-40:]


def _turn_step(raw_phase: str, player: Dict[str, Any], is_finished: bool) -> str:
    if is_finished:
        return "finished"
    if raw_phase == "created":
        return "start"
    if player.get("ready"):
        return "waiting"
    if not player.get("intent"):
        return "intent"
    if player.get("played_card"):
        return "ready"
    return "card"


def _card_state(card: Dict[str, Any], player: Dict[str, Any], step: str, is_finished: bool) -> Dict[str, Any]:
    cost = int(card.get("cost") or 0)
    energy = int(player.get("energy") or 0)
    card_id = str(card.get("id") or "")
    legal_lanes = empty_lanes(player) if card.get("kind") == "creature" else []

    disabled_reason = ""
    if is_finished:
        disabled_reason = "Match finished."
    elif player.get("ready"):
        disabled_reason = "You are ready for this round."
    elif not player.get("intent"):
        disabled_reason = "Choose Strike, Guard or Focus first."
    elif player.get("played_this_round") or player.get("played_card"):
        disabled_reason = "Only one card can be played each round."
    elif cost > energy:
        disabled_reason = f"Needs {cost} energy. You have {energy}."
    elif card.get("kind") == "creature" and not legal_lanes:
        disabled_reason = "No empty lane available."
    elif step != "card":
        disabled_reason = "Not the card step."

    return {
        "id": card_id,
        "playable": disabled_reason == "",
        "disabled_reason": disabled_reason,
        "preview": _card_preview(card, intent=player.get("intent"), owner=player),
        "legal_lanes": legal_lanes,
    }


def _legal_actions_for(player: Dict[str, Any], raw_phase: str, step: str, is_finished: bool) -> Dict[str, Any]:
    card_states = [_card_state(card, player, step, is_finished) for card in (player.get("hand") or [])]
    playable_ids = [state["id"] for state in card_states if state["playable"]]
    has_intent = bool(player.get("intent"))
    can_ready = step in {"card", "ready"} and has_intent and not player.get("ready") and not is_finished
    can_play_cards = step == "card" and bool(playable_ids) and not player.get("ready") and not is_finished
    legal_lanes = empty_lanes(player) if step == "card" and has_intent and not player.get("ready") and not is_finished else []

    if step == "start":
        primary_action = "start"
        prompt = "Press Start to begin the training duel."
    elif step == "intent":
        primary_action = "choose_intent"
        prompt = "Choose one tactic for this round."
    elif step == "card" and can_play_cards:
        primary_action = "play_card"
        prompt = "Play one highlighted card, or press Ready to skip the card."
    elif step in {"card", "ready"}:
        primary_action = "ready"
        prompt = "Press Ready to resolve combat."
    elif step == "waiting":
        primary_action = "wait"
        prompt = "Waiting for the opponent."
    else:
        primary_action = "finished"
        prompt = "Match finished."

    return {
        "show_start": raw_phase == "created",
        "can_start": raw_phase == "created" and not is_finished,
        "show_intents": step == "intent",
        "can_choose_intent": step == "intent",
        "can_play_cards": can_play_cards,
        "show_ready": can_ready,
        "can_ready": can_ready,
        "can_unleash": int(player.get("ambition") or 0) >= UNLEASH_COST and step in {"card", "ready"} and not is_finished,
        "legal_lanes": legal_lanes,
        "legal_targets": ["enemy_hero", "self"],
        "playable_card_ids": playable_ids,
        "card_states": card_states,
        "disabled_reasons_by_card": {
            state["id"]: state["disabled_reason"]
            for state in card_states
            if state["disabled_reason"]
        },
        "primary_action": primary_action,
        "next_required_action": primary_action,
        "prompt": prompt,
    }


def _mode_for_state(state: Dict[str, Any]) -> str:
    if state.get("training"):
        return "training"
    if state.get("is_bot_match"):
        return "bot"
    return "pvp"


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
    is_finished = raw_phase == "finished" or bool(state.get("winner"))
    phase = _turn_step(str(raw_phase), player, is_finished)
    legal_actions = _legal_actions_for(player, str(raw_phase), phase, is_finished)
    card_state_by_id = {
        str(card_state.get("id")): card_state
        for card_state in legal_actions.get("card_states", [])
    }

    enemy_preview = state.get("enemy_preview") or {}
    if not enemy.get("is_bot"):
        enemy_preview = {
            "intent": "Hidden" if enemy.get("intent") else "",
            "message": "Opponent is choosing their line.",
        }

    me_payload = _player_payload(player, viewer=True)
    for card in me_payload.get("hand") or []:
        card_state = card_state_by_id.get(str(card.get("id"))) or {}
        card["playable"] = bool(card_state.get("playable"))
        card["disabled_reason"] = str(card_state.get("disabled_reason") or "")
        card["preview"] = str(card_state.get("preview") or card.get("preview") or "")

    final_message = message

    if not final_message:
        summary = state.get("round_summary") or {}

        if state.get("winner"):
            final_message = summary.get("short_result") or f"Match finished. Winner: {_winner_for_viewer(state.get('winner'), viewer_side)}."
        elif legal_actions.get("prompt"):
            final_message = str(legal_actions["prompt"])
        elif summary.get("short_result"):
            final_message = summary["short_result"]
        elif enemy_preview.get("message"):
            final_message = enemy_preview["message"]
        else:
            final_message = "Choose a tactic: Strike attacks harder, Guard blocks damage, Focus charges Unleash."

    round_summary = _summary_for_viewer(state.get("round_summary") or {}, viewer_side)

    return {
        "schema": ARENA_CLEAN_SCHEMA,
        "engine": ENGINE_VERSION,
        "mode": _mode_for_state(state),
        "phase": phase,
        "raw_phase": raw_phase,
        "round": int(state.get("round") or 0),
        "message": final_message,
        "winner": _winner_for_viewer(state.get("winner"), viewer_side),
        "reason": state.get("reason"),
        "enemy_preview": enemy_preview,
        "round_summary": round_summary,
        "last_round_summary": round_summary,
        "combat_log": _combat_log_for_payload(state),
        "events": _events_for_viewer(list(state.get("events") or [])[-24:], viewer_side),
        "round_events": _events_for_viewer(list(state.get("round_events") or [])[-12:], viewer_side),
        "card_registry": {
            "schema": CARD_REGISTRY_SCHEMA,
            "version": "v1",
        },
        "keyword_registry": {
            "schema": KEYWORD_REGISTRY_SCHEMA,
            "version": "v1",
            "keywords": KEYWORD_REGISTRY_V1,
        },
        "turn": {
            "step": phase,
            "raw_phase": raw_phase,
            "primary_action": legal_actions.get("primary_action"),
            "prompt": legal_actions.get("prompt"),
            "selected_intent": player.get("intent"),
            "played_card_id": str((player.get("played_card") or {}).get("id") or ""),
            "played_card_name": str((player.get("played_card") or {}).get("name") or ""),
        },
        "help": {
            "turn_order": [
                "1. Choose Strike, Guard or Focus.",
                "2. Play one card if you can.",
                "3. Press Ready to resolve combat.",
            ],
            "actions": {
                "Strike": "+2 attack this round.",
                "Guard": "+5 shield this round.",
                "Focus": "+3 Ambition. Ambition charges Unleash.",
                "Ready": "Resolves your action and the enemy action.",
            },
            "goal": "Destroy enemy creatures, damage enemy HP, and use Unleash to finish the duel.",
        },
        "unleash_cost": UNLEASH_COST,
        "me": me_payload,
        "enemy": _player_payload(enemy, viewer=False),
        "legal_actions": legal_actions,
        "log": list(state.get("log") or [])[-10:],
    }


def create_be2_training_match(user=None, sid: Optional[str] = None, difficulty: str = "training") -> Dict[str, Any]:
    player_name = getattr(user, "username", None) or getattr(user, "email", None) or "Player"
    user_id = getattr(user, "id", None)
    match = create_match(player_name=player_name, opponent_name="Ambitionz Bot", player_sid=sid, user_id=user_id)
    match["opponent"]["hp"] = TRAINING_BOT_HP
    match["opponent"]["max_hp"] = TRAINING_BOT_HP
    match["be2"] = True
    match["training"] = True
    match["is_bot_match"] = True
    match["bot_difficulty"] = difficulty or "training"
    match["room_code"] = f"be2_training_{sid}" if sid else "be2_training"
    return attach_legacy_match_aliases(match)


def create_be2_bot_match(
    user=None,
    sid: Optional[str] = None,
    room_code: Optional[str] = None,
    matchmaking_fallback: bool = False,
    training: bool = False,
    difficulty: str = "normal",
) -> Dict[str, Any]:
    match = create_be2_training_match(user=user, sid=sid, difficulty="training" if training else difficulty)
    match["training"] = bool(training)
    match["matchmaking_fallback"] = bool(matchmaking_fallback)
    match["bot_difficulty"] = "training" if training else difficulty
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


def be2_play_card(
    match: Dict[str, Any],
    card_id: Optional[str] = None,
    card_index: Optional[int] = None,
    side: str = "player",
    lane: Optional[str] = None,
    target: Optional[str] = None,
) -> Dict[str, Any]:
    if match.get("phase") == "created":
        start_round(match)

    side = side if side in {"player", "opponent"} else "player"

    play_card(match, side, card_id=card_id, card_index=card_index, lane=lane, target=target)
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
        raise ValueError("Choose Strike, Guard or Focus before ready.")

    match[side]["ready"] = True

    if match[other_side].get("is_bot"):
        if not match[other_side].get("ready"):
            from services.battle_engine_v2 import bot_choose_action
            bot_choose_action(match)
        resolve_round(match)
        return match

    if match[other_side].get("ready"):
        resolve_round(match)

    return match
