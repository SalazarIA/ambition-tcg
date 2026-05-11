# =========================================================
# QA BE2 Adapter
# Validates BE2 -> Arena Clean V50 contract.
# =========================================================

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.battle_engine_v2_adapter import (
    build_be2_arena_payload,
    create_be2_training_match,
    be2_play_card,
    be2_ready,
    be2_set_intent,
    be2_start,
)


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    print("=== QA BE2 ADAPTER ===")

    match = create_be2_training_match(sid="adapter-smoke")
    payload = build_be2_arena_payload(match)

    assert_true(payload["schema"] == "arena_state_v50", "invalid schema")
    assert_true(payload["legacy_schema"] == "ambitionz_arena_clean_v50", "missing legacy schema marker")
    assert_true(payload["engine"] == "battle_engine_v2", "invalid engine")
    assert_true(payload["phase"] == "start", "expected start phase")
    assert_true(payload["legal_actions"]["primary_action"] == "start", "expected start primary action")

    be2_start(match)
    payload = build_be2_arena_payload(match)

    assert_true(payload["phase"] == "intent", "expected intent after start")
    assert_true(payload["me"]["hand_count"] >= 5, "expected hand after start")
    assert_true(payload["enemy"]["hand_count"] >= 5, "expected enemy hand count")
    assert_true(payload["legal_actions"]["can_choose_intent"], "expected intent action")
    assert_true(payload["legal_actions"]["can_ready"], "ready should be legal even before intent")

    hand_before = payload["me"]["hand_count"]

    be2_set_intent(match, "Strike")
    payload = build_be2_arena_payload(match)

    assert_true(payload["me"]["hand_count"] == hand_before, "intent should not play card")
    assert_true(payload["me"]["intent"] == "Strike", "intent should be Strike")

    playable = payload["legal_actions"]["playable_card_ids"]
    assert_true(len(playable) > 0, "expected playable cards")

    selected_card_id = playable[0]
    be2_play_card(match, card_id=selected_card_id)
    payload = build_be2_arena_payload(match)

    played = match["player"].get("played_card") or {}
    assert_true(played.get("id") == selected_card_id, "selected card should be registered as played_card")

    # Some cards draw immediately, so hand_count is not guaranteed to be hand_before - 1.
    assert_true(payload["me"]["hand_count"] <= hand_before, "hand should not grow beyond previous count after a single play")

    be2_ready(match)
    payload = build_be2_arena_payload(match)

    assert_true(payload["schema"] == "arena_state_v50", "schema after ready")
    assert_true(payload["round"] >= 1, "round should exist")
    assert_true(payload["me"]["hp"] >= 0, "player hp should be non-negative")
    assert_true(payload["enemy"]["hp"] >= 0, "enemy hp should be non-negative")

    print("PASS BE2 adapter smoke")
    print("round:", payload["round"])
    print("phase:", payload["phase"])
    print("player hp:", payload["me"]["hp"])
    print("enemy hp:", payload["enemy"]["hp"])
    print("")
    print("ALL BE2 ADAPTER QA PASSED")


if __name__ == "__main__":
    main()
