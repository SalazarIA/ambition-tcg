"""BE2 training actions used by audits and maintenance scripts."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from services.battle_engine_v2_adapter import (
    be2_play_card,
    be2_ready,
    be2_set_intent,
    be2_start,
    build_be2_arena_payload,
    create_be2_training_match,
)

Match = Dict[str, Any]
Payload = Dict[str, Any]
Result = Tuple[bool, str]


def _side(side: str) -> str:
    return "opponent" if side in {"p2", "opponent"} else "player"


def create_training_match(user: Any = None, sid: Optional[str] = None, room_code: Optional[str] = None) -> Match:
    match = create_be2_training_match(user=user, sid=sid)

    if room_code:
        match["room_code"] = room_code

    return be2_start(match)


def build_training_payload(match: Match, viewer_key: str = "p1", message: Optional[str] = None) -> Payload:
    return build_be2_arena_payload(match, viewer_side=_side(viewer_key), message=message)


def set_intent(match: Match, side: str, intent: str) -> Result:
    try:
        be2_set_intent(match, intent, side=_side(side))
        return True, f"{intent} selected."
    except Exception as error:
        return False, str(error)


def play_card(match: Match, side: str, card_id: Optional[str] = None, card_index: Optional[int] = None) -> Result:
    try:
        be2_play_card(match, card_id=card_id, card_index=card_index, side=_side(side))
        return True, "Card played."
    except Exception as error:
        return False, str(error)


def declare_ready(match: Match, side: str) -> Result:
    try:
        be2_ready(match, side=_side(side))
        return True, "Round resolved."
    except Exception as error:
        return False, str(error)
