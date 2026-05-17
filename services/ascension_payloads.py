"""Public JSON payloads for Ascension Duel."""

from __future__ import annotations

import copy

from services.ascension_bot import bot_profile_payload
from services.ascension_engine import legal_actions


def public_card(card):
    if not card:
        return None
    return {
        "id": card.get("id"),
        "name": card.get("name"),
        "type": card.get("type"),
        "rarity": card.get("rarity"),
        "faction": card.get("faction"),
        "text": card.get("text"),
        "modes": list(card.get("modes", [])),
        "ambition_cost": card.get("ambition_cost", 0),
        "resolve": copy.deepcopy(card.get("resolve", {})),
        "current_hp": card.get("current_hp"),
        "max_hp": card.get("max_hp"),
        "ascended": bool(card.get("ascended")),
    }


def _scheme_payload(scheme, hide_hidden=True):
    card = scheme.get("card") if isinstance(scheme, dict) else None
    revealed = bool(scheme.get("revealed")) if isinstance(scheme, dict) else False
    if hide_hidden and not revealed:
        return {"revealed": False, "name": "Prepared Scheme", "type": "scheme"}
    payload = public_card(card)
    payload["revealed"] = revealed
    return payload


def public_side_state(side_state, hide_hidden=True):
    schemes = side_state.get("schemes", [])
    return {
        "name": side_state.get("name"),
        "hp": side_state.get("hp", 0),
        "ambition": side_state.get("ambition", 0),
        "active_champion": public_card(side_state.get("active_champion")),
        "bound_souls": [public_card(card) for card in side_state.get("bound_souls", [])],
        "relic": public_card(side_state.get("relic")),
        "schemes_count": len(schemes),
        "schemes": [_scheme_payload(scheme, hide_hidden=hide_hidden) for scheme in schemes],
        "intent": side_state.get("intent"),
        "previous_intent": side_state.get("previous_intent"),
        "status": copy.deepcopy(side_state.get("status", {})),
        "hand": [public_card(card) for card in side_state.get("hand", [])],
        "hand_count": len(side_state.get("hand", [])),
        "deck_count": len(side_state.get("deck", [])),
        "echo_count": len(side_state.get("echo", [])),
        "domination_marks": side_state.get("domination_marks", 0),
        "ascended": bool(side_state.get("ascended")),
    }


def chronicle_payload(match):
    return list(match.get("chronicle", []))[-40:]


def public_match_state(match, perspective="player"):
    perspective = "opponent" if perspective == "opponent" else "player"
    enemy_side = "player" if perspective == "opponent" else "opponent"

    viewer = public_side_state(match[perspective], hide_hidden=False)
    enemy = public_side_state(match[enemy_side], hide_hidden=True)
    enemy["hand"] = []

    return {
        "id": match.get("id"),
        "version": match.get("version"),
        "round": match.get("round"),
        "phase": match.get("phase"),
        "winner": match.get("winner"),
        "bot_profile": bot_profile_payload(match.get("bot_profile")),
        "seed": match.get("seed"),
        "created_at": match.get("created_at"),
        "perspective": perspective,
        "player": viewer,
        "opponent": enemy,
        "chronicle": chronicle_payload(match),
    }


def action_response(match, ok=True, error=None):
    payload = {
        "ok": bool(ok),
        "error": error,
        "match": public_match_state(match, perspective="player") if match else None,
    }
    if ok and match:
        payload["actions"] = legal_actions(match, "player")
    return payload
