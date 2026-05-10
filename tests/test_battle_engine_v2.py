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
    be2_play_card,
    be2_ready,
    be2_set_intent,
    be2_start,
    build_be2_arena_payload,
    create_be2_match_from_players,
    create_be2_training_match,
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


def test_be2_payload_exposes_clear_turn_contract():
    match = create_be2_training_match(sid="contract-test")

    created = build_be2_arena_payload(match)
    assert created["phase"] == "start"
    assert created["turn"]["primary_action"] == "start"
    assert created["legal_actions"]["can_start"] is True

    be2_start(match)
    initial = build_be2_arena_payload(match)
    assert initial["phase"] == "intent"
    assert initial["turn"]["primary_action"] == "choose_intent"
    assert initial["legal_actions"]["can_choose_intent"] is True
    assert initial["legal_actions"]["can_play_cards"] is False

    be2_set_intent(match, "Strike")
    after_intent = build_be2_arena_payload(match)
    assert after_intent["phase"] == "card"
    assert after_intent["turn"]["primary_action"] in {"play_card", "ready"}
    assert after_intent["legal_actions"]["can_ready"] is True
    assert after_intent["legal_actions"]["card_states"]
    assert after_intent["me"]["hand"][0]["preview"]

    playable_id = after_intent["legal_actions"]["playable_card_ids"][0]
    be2_play_card(match, card_id=playable_id)
    after_play = build_be2_arena_payload(match)
    assert after_play["phase"] == "ready"
    assert after_play["turn"]["primary_action"] == "ready"
    assert after_play["legal_actions"]["can_play_cards"] is False
    assert after_play["legal_actions"]["can_ready"] is True

    with pytest.raises(ValueError, match="Only one card"):
        be2_play_card(match, card_id=after_play["me"]["hand"][0]["id"])


def test_be2_payload_includes_structured_round_events():
    match = create_be2_training_match(sid="events-test")
    be2_start(match)
    be2_set_intent(match, "Guard")
    payload = build_be2_arena_payload(match)
    playable_id = payload["legal_actions"]["playable_card_ids"][0]
    be2_play_card(match, card_id=playable_id)
    be2_ready(match)

    resolved = build_be2_arena_payload(match)

    assert resolved["round"] >= 2 or resolved["phase"] == "finished"
    assert resolved["events"]
    assert resolved["round_summary"]["events"]
    assert any(event["type"] in {"attack", "hero_damage", "shield"} for event in resolved["round_summary"]["events"])


def test_training_bot_uses_training_balance_profile():
    match = create_be2_training_match(sid="balance-test")

    assert match["bot_difficulty"] == "training"
    assert match["opponent"]["max_hp"] == 24


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
