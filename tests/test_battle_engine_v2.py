import pytest

from services.battle_engine_v2 import (
    STARTING_HAND_SIZE,
    choose_intent,
    create_match,
    play_card,
    resolve_round,
    start_round,
)
from services.battle_engine_v2_adapter import (
    be2_ready,
    be2_set_intent,
    build_be2_arena_payload,
    create_be2_match_from_players,
)
from services.match_engine_facade import MatchEngineFacade


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


def test_be2_pvp_waits_for_both_players_before_resolving():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-a-b",
    )
    start_round(match)

    be2_set_intent(match, "Strike", side="player")
    be2_ready(match, side="player")

    assert match["round"] == 1
    assert match["phase"] == "choose_action"
    assert match["player"]["ready"] is True
    assert match["opponent"]["ready"] is False

    be2_set_intent(match, "Guard", side="opponent")
    be2_ready(match, side="opponent")

    assert match["round"] == 2
    assert match["phase"] == "choose_action"
    assert match["player"]["ready"] is False
    assert match["opponent"]["ready"] is False


def test_be2_arena_payload_flips_perspective_for_second_player():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-a-b",
    )
    start_round(match)

    p1_payload = build_be2_arena_payload(match, viewer_side="player")
    p2_payload = build_be2_arena_payload(match, viewer_side="opponent")

    assert p1_payload["me"]["name"] == "Alice"
    assert p1_payload["enemy"]["name"] == "Bob"
    assert p2_payload["me"]["name"] == "Bob"
    assert p2_payload["enemy"]["name"] == "Alice"
    assert len(p2_payload["me"]["hand"]) == STARTING_HAND_SIZE
    assert p2_payload["enemy"]["hand"] == []


def test_be2_rejects_explicit_invalid_card_id():
    match = create_match(seed=42)
    start_round(match)

    with pytest.raises(ValueError, match="Card not found"):
        play_card(match, "player", card_id="not-in-hand")


def test_match_engine_facade_finalizes_finished_match_once():
    finalized = []
    emits = []
    active_matches = {}
    player_rooms = {}

    facade = MatchEngineFacade(
        active_matches,
        player_rooms,
        lambda event, payload, room=None: emits.append((event, payload, room)),
        finish_match=lambda room_code, match: finalized.append((room_code, match.get("winner"))),
    )

    facade.start_training("sid-a")
    room_code, match = facade.match_for_sid("sid-a")
    match["winner"] = "player"
    match["phase"] = "finished"

    facade.emit_state("sid-a")
    facade.emit_state("sid-a")

    assert finalized == [(room_code, "player")]
    assert match["be2_finalized"] is True
