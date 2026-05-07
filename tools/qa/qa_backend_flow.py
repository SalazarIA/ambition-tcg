from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from models import User
from services.match_actions_v1 import (
    create_training_match_v1,
    set_intent,
    play_card,
    declare_ready,
)
from services.arena_clean_state import build_arena_clean_state


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _state_summary(payload):
    me = payload.get("me") or {}
    enemy = payload.get("enemy") or {}
    legal = payload.get("legal_actions") or {}

    return {
        "schema": payload.get("schema"),
        "phase": payload.get("phase"),
        "message": payload.get("message"),
        "round": payload.get("round"),
        "me_hp": me.get("hp"),
        "me_energy": me.get("energy"),
        "me_max_energy": me.get("max_energy"),
        "me_intent": me.get("intent"),
        "me_ready": me.get("ready"),
        "me_hand_count": len(me.get("hand") or []),
        "enemy_hand_count": enemy.get("hand_count"),
        "can_ready": legal.get("can_ready"),
        "can_play_cards": legal.get("can_play_cards"),
        "playable_card_ids": legal.get("playable_card_ids") or [],
    }


def _validate_hand_cards(payload, stage, logs):
    hand = ((payload.get("me") or {}).get("hand") or [])

    _assert(hand, f"{stage}: expected non-empty hand")

    for index, card in enumerate(hand, start=1):
        card_id = card.get("id")
        name = card.get("name")
        card_type = card.get("type")
        cost = card.get("cost")
        power = card.get("power")
        display_stat = card.get("display_stat")

        logs.append(
            f"{stage} HAND {index}: id={card_id} name={name} type={card_type} cost={cost} power={power} display={display_stat}"
        )

        _assert(card_id, f"{stage}: card {index} missing id")
        _assert(name, f"{stage}: card {index} missing name")
        _assert(card_type in ("Monster", "Spell", "Trap"), f"{stage}: card {index} invalid type {card_type}")
        _assert(int(cost or 0) > 0, f"{stage}: card {index} invalid cost {cost}")

        if card_type == "Monster":
            _assert(int(power or 0) > 0, f"{stage}: monster card has zero power: {card}")


def run_backend_flow():
    logs = []
    result = {
        "name": "backend_training_flow",
        "status": "PASS",
        "logs": logs,
        "error": None,
    }

    try:
        with app.app_context():
            user = User.query.first()

            _assert(user is not None, "No local user found. Create at least one user before running QA.")

            logs.append(f"user: id={user.id} username={user.username}")

            match = create_training_match_v1(user, "QA_BACKEND_SID", "qa_backend_room")

            initial = build_arena_clean_state(match, "p1")
            logs.append(f"initial_state: {_state_summary(initial)}")
            _assert(initial.get("schema") == "ambitionz_arena_clean_v50", "Initial state schema mismatch")
            _assert(initial.get("phase") in ("intent", "main", "start"), f"Unexpected initial phase {initial.get('phase')}")
            _validate_hand_cards(initial, "initial", logs)

            ok, message = set_intent(match, "p1", "Strike")
            logs.append(f"set_intent: ok={ok} message={message}")
            _assert(ok, f"set_intent failed: {message}")

            after_intent = build_arena_clean_state(match, "p1", message=message)
            logs.append(f"after_intent_state: {_state_summary(after_intent)}")
            _assert(after_intent["me"]["intent"] == "Strike", "Intent was not set to Strike")
            _validate_hand_cards(after_intent, "after_intent", logs)

            first_card_id = after_intent["me"]["hand"][0]["id"]

            ok, message = play_card(match, "p1", first_card_id)
            logs.append(f"play_card: card_id={first_card_id} ok={ok} message={message}")
            _assert(ok, f"play_card failed: {message}")

            after_play = build_arena_clean_state(match, "p1", message=message)
            logs.append(f"after_play_state: {_state_summary(after_play)}")
            _assert(len(after_play["me"]["hand"]) == 4, f"Expected 4 cards after play, got {len(after_play['me']['hand'])}")
            _assert(after_play["me"]["field"]["monster"], "Expected monster in field after play")
            _assert(after_play["legal_actions"]["can_ready"], "Expected can_ready True after play")
            _validate_hand_cards(after_play, "after_play", logs)

            monster = after_play["me"]["field"]["monster"]
            logs.append(f"field_monster: {monster}")
            _assert(int(monster.get("power") or 0) > 0, "Field monster has zero power")

            ok, message = declare_ready(match, "p1")
            logs.append(f"declare_ready: ok={ok} message={message}")
            _assert(ok, f"declare_ready failed: {message}")

            after_ready = build_arena_clean_state(match, "p1", message=message)
            logs.append(f"after_ready_state: {_state_summary(after_ready)}")
            _assert(after_ready["me"]["hand"], "Expected hand after ready/new round")

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result
