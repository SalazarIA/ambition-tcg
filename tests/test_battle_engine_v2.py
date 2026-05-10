from services.battle_engine_v2 import (
    STARTING_HAND_SIZE,
    choose_intent,
    create_match,
    resolve_round,
    start_round,
)


def test_be2_start_round_preserves_initial_hand_size():
    match = create_match(seed=42)

    assert len(match["player"]["hand"]) == STARTING_HAND_SIZE

    start_round(match)

    assert match["round"] == 1
    assert len(match["player"]["hand"]) == STARTING_HAND_SIZE
    assert len(match["opponent"]["hand"]) == STARTING_HAND_SIZE


def test_be2_resolved_round_draws_for_next_round():
    match = create_match(seed=42)
    start_round(match)

    choose_intent(match, "player", "Focus")
    resolve_round(match)

    assert match["round"] == 2
    assert len(match["player"]["hand"]) == STARTING_HAND_SIZE + 1
