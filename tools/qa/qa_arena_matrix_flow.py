
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _summary(payload):
    me = payload.get("me") or {}
    enemy = payload.get("enemy") or {}
    legal = payload.get("legal_actions") or {}

    return {
        "schema": payload.get("schema"),
        "phase": payload.get("phase"),
        "round": payload.get("round"),
        "message": payload.get("message"),
        "me_hp": me.get("hp"),
        "enemy_hp": enemy.get("hp"),
        "me_energy": me.get("energy"),
        "me_max_energy": me.get("max_energy"),
        "me_intent": me.get("intent"),
        "me_ready": me.get("ready"),
        "me_hand": len(me.get("hand") or []),
        "enemy_hand_count": enemy.get("hand_count"),
        "field": me.get("field"),
        "can_ready": legal.get("can_ready"),
        "can_play_cards": legal.get("can_play_cards"),
        "playable_card_ids": legal.get("playable_card_ids"),
    }


def _assert_clean_payload(payload, label, failures):
    if not payload:
        failures.append(f"{label}: empty payload")
        return

    if payload.get("schema") not in {"arena_state_v50", "ambitionz_arena_clean_v50"}:
        failures.append(f"{label}: wrong schema {payload.get('schema')}")

    me = payload.get("me") or {}
    enemy = payload.get("enemy") or {}
    legal = payload.get("legal_actions") or {}

    if not me:
        failures.append(f"{label}: missing me payload")

    if not enemy:
        failures.append(f"{label}: missing enemy payload")

    if not isinstance(me.get("hand") or [], list):
        failures.append(f"{label}: me.hand is not a list")

    if "can_ready" not in legal:
        failures.append(f"{label}: legal_actions missing can_ready")

    if "can_play_cards" not in legal:
        failures.append(f"{label}: legal_actions missing can_play_cards")

    if int(me.get("hp") or 0) <= 0 and payload.get("phase") != "finished":
        failures.append(f"{label}: player hp invalid before finish")

    if int(enemy.get("hp") or 0) <= 0 and payload.get("phase") != "finished":
        failures.append(f"{label}: enemy hp invalid before finish")


def run_arena_matrix_flow():
    logs = []
    failures = []

    try:
        from app import app
        from models import User
        from services.arena_training_actions import (
            create_training_match,
            build_training_payload,
            set_intent,
            play_card,
            declare_ready,
        )

        with app.app_context():
            user = User.query.first()

            if not user:
                return {
                    "name": "arena_matrix_flow",
                    "status": "FAIL",
                    "error": "No local user found.",
                    "logs": logs,
                }

            logs.append(f"user: id={user.id} username={user.username}")

            # Scenario 1: all intents should work through a round.
            for intent in ["Strike", "Guard", "Focus"]:
                room = f"qa_matrix_{intent.lower()}"
                sid = f"QA_MATRIX_{intent.upper()}"

                match = create_training_match(user, sid, room)

                initial = build_training_payload(match, "p1")
                _assert_clean_payload(initial, f"{intent}/initial", failures)
                logs.append(f"{intent}/initial: {_summary(initial)}")

                ok, message = set_intent(match, "p1", intent)
                logs.append(f"{intent}/set_intent: ok={ok} message={message}")

                if not ok:
                    failures.append(f"{intent}: set_intent failed: {message}")
                    continue

                after_intent = build_training_payload(match, "p1", message=message)
                _assert_clean_payload(after_intent, f"{intent}/after_intent", failures)
                logs.append(f"{intent}/after_intent: {_summary(after_intent)}")

                hand = ((after_intent.get("me") or {}).get("hand") or [])
                if not hand:
                    failures.append(f"{intent}: no hand after intent")
                    continue

                playable_ids = ((after_intent.get("legal_actions") or {}).get("playable_card_ids") or [])
                card_id = next(
                    (
                        card.get("id")
                        for card in hand
                        if card.get("type") == "Monster" and card.get("id") in playable_ids
                    ),
                    playable_ids[0] if playable_ids else hand[0].get("id"),
                )
                selected_card = next((card for card in hand if card.get("id") == card_id), {})
                ok, message = play_card(match, "p1", card_id)
                logs.append(f"{intent}/play_card: card_id={card_id} ok={ok} message={message}")

                if not ok:
                    failures.append(f"{intent}: play_card failed: {message}")
                    continue

                after_play = build_training_payload(match, "p1", message=message)
                _assert_clean_payload(after_play, f"{intent}/after_play", failures)
                logs.append(f"{intent}/after_play: {_summary(after_play)}")

                after_play_hand = len(((after_play.get("me") or {}).get("hand") or []))
                field = ((after_play.get("me") or {}).get("field") or {})

                if after_play_hand != len(hand) - 1:
                    failures.append(f"{intent}: hand did not decrease after play. before={len(hand)} after={after_play_hand}")

                if selected_card.get("type") == "Monster" and not field.get("monster"):
                    failures.append(f"{intent}: no card appeared in field after play")

                ok, message = declare_ready(match, "p1")
                logs.append(f"{intent}/declare_ready: ok={ok} message={message}")

                if not ok:
                    failures.append(f"{intent}: declare_ready failed: {message}")
                    continue

                after_ready = build_training_payload(match, "p1", message=message)
                _assert_clean_payload(after_ready, f"{intent}/after_ready", failures)
                logs.append(f"{intent}/after_ready: {_summary(after_ready)}")

                if int(after_ready.get("round") or 0) < 2 and after_ready.get("phase") != "finished":
                    failures.append(f"{intent}: round did not advance after ready")

            # Scenario 2: ready without playing should still resolve safely.
            match = create_training_match(user, "QA_MATRIX_READY_ONLY", "qa_matrix_ready_only")

            ok, message = set_intent(match, "p1", "Strike")
            logs.append(f"ready_only/set_intent: ok={ok} message={message}")

            ok, message = declare_ready(match, "p1")
            logs.append(f"ready_only/declare_ready: ok={ok} message={message}")

            after_ready_only = build_training_payload(match, "p1", message=message)
            _assert_clean_payload(after_ready_only, "ready_only/after_ready", failures)
            logs.append(f"ready_only/after_ready: {_summary(after_ready_only)}")

            if not ok:
                failures.append(f"ready_only: declare_ready failed: {message}")

            # Scenario 3: invalid card id should fail, not mutate hand.
            match = create_training_match(user, "QA_MATRIX_INVALID", "qa_matrix_invalid")
            before_invalid = build_training_payload(match, "p1")
            hand_before = len(((before_invalid.get("me") or {}).get("hand") or []))

            ok, message = play_card(match, "p1", "__invalid_card_id__")
            logs.append(f"invalid_card/play_card: ok={ok} message={message}")

            after_invalid = build_training_payload(match, "p1", message=message)
            hand_after = len(((after_invalid.get("me") or {}).get("hand") or []))

            if ok:
                failures.append("invalid_card: play_card unexpectedly succeeded")

            if hand_after != hand_before:
                failures.append(f"invalid_card: hand mutated after invalid card. before={hand_before} after={hand_after}")

            # Scenario 4: second monster in occupied monster slot should not break state.
            match = create_training_match(user, "QA_MATRIX_SLOT", "qa_matrix_slot")
            set_intent(match, "p1", "Strike")

            state = build_training_payload(match, "p1")
            hand = ((state.get("me") or {}).get("hand") or [])

            playable_ids = ((state.get("legal_actions") or {}).get("playable_card_ids") or [])
            first_card = playable_ids[0] if playable_ids else (hand[0].get("id") if hand else None)
            ok1, msg1 = play_card(match, "p1", first_card)
            logs.append(f"slot_guard/first_play: card_id={first_card} ok={ok1} message={msg1}")

            state_after_first = build_training_payload(match, "p1", message=msg1)
            hand2 = ((state_after_first.get("me") or {}).get("hand") or [])

            playable_ids2 = ((state_after_first.get("legal_actions") or {}).get("playable_card_ids") or [])
            second_card = playable_ids2[0] if playable_ids2 else (hand2[0].get("id") if hand2 else None)
            ok2, msg2 = play_card(match, "p1", second_card)
            logs.append(f"slot_guard/second_play: card_id={second_card} ok={ok2} message={msg2}")

            state_after_second = build_training_payload(match, "p1", message=msg2)
            _assert_clean_payload(state_after_second, "slot_guard/after_second", failures)
            logs.append(f"slot_guard/after_second: {_summary(state_after_second)}")

            if ok2:
                logs.append("slot_guard: second play succeeded; probably different zone or card type.")
            else:
                logs.append("slot_guard: second play rejected safely.")

        status = "FAIL" if failures else "PASS"

        return {
            "name": "arena_matrix_flow",
            "status": status,
            "error": "; ".join(failures) if failures else None,
            "logs": logs,
        }

    except Exception as exc:
        return {
            "name": "arena_matrix_flow",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "logs": logs,
        }
