from copy import deepcopy

import pytest

from services.battle_engine_v2 import (
    CARD_CATALOG_V2,
    STARTING_HAND_SIZE,
    bot_take_turn,
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


def _v2_card(card_id):
    return deepcopy(CARD_CATALOG_V2[card_id])


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
    match["player"]["hand"] = [_v2_card("spark_runner"), _v2_card("hold_position")]
    match["player"]["energy"] = 2

    initial = build_be2_arena_payload(match)
    assert initial["phase"] == "intent"
    assert initial["turn"]["primary_action"] == "choose_intent"
    assert initial["legal_actions"]["can_choose_intent"] is True
    assert initial["legal_actions"]["can_play_cards"] is True
    assert initial["legal_actions"]["can_ready"] is True

    playable_id = initial["legal_actions"]["playable_card_ids"][0]
    be2_play_card(match, card_id=playable_id)
    after_play_without_intent = build_be2_arena_payload(match)
    assert match["player"]["played_card"]["id"] == playable_id
    assert match["player"]["intent"] == "Focus"
    assert after_play_without_intent["legal_actions"]["can_play_cards"] is False
    assert after_play_without_intent["legal_actions"]["can_ready"] is True
    assert after_play_without_intent["legal_actions"]["can_choose_intent"] is False
    assert after_play_without_intent["turn"]["primary_action"] == "ready"

    with pytest.raises(ValueError, match="Only one card"):
        be2_play_card(match, card_index=0)

    with pytest.raises(ValueError, match="Intent is locked"):
        be2_set_intent(match, "Strike")


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


def test_bot_take_turn_chooses_intent_plays_card_and_marks_ready():
    match = create_be2_training_match(sid="bot-turn-test")
    be2_start(match)
    match["opponent"]["hand"] = [_v2_card("spark_runner")]
    match["opponent"]["deck"] = []
    match["opponent"]["energy"] = 2

    bot_take_turn(match)

    assert match["opponent"]["intent"] in {"Strike", "Guard", "Focus"}
    assert match["opponent"]["played_card"]["id"] == "spark_runner"
    assert match["opponent"]["field"]["active"]["id"] == "spark_runner"
    assert match["opponent"]["ready"] is True


def test_bot_ready_path_resolves_attack_damage():
    match = create_be2_training_match(sid="bot-damage-test")
    be2_start(match)
    match["opponent"]["hand"] = [_v2_card("spark_runner")]
    match["opponent"]["deck"] = []
    match["opponent"]["energy"] = 2
    match["player"]["field"]["active"] = None
    player_hp_before = match["player"]["hp"]

    be2_ready(match, side="player")

    summary = match["round_summary"]
    assert match["round"] == 2
    assert summary["enemy_attack"] > 0
    assert summary["player_hp_after"] < player_hp_before
    assert match["player"]["hp"] == summary["player_hp_after"]


def test_player_with_empty_hand_can_ready():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-empty-hand",
    )
    start_round(match)
    match["player"]["hand"] = []
    match["player"]["deck"] = []

    be2_ready(match, side="player")

    assert match["round"] == 1
    assert match["player"]["ready"] is True
    assert match["player"]["intent"] == "Focus"
    assert match["opponent"]["ready"] is False


def test_both_ready_resolves_and_resets_round_state():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-reset",
    )
    start_round(match)

    for side in ("player", "opponent"):
        match[side]["hand"] = [_v2_card("spark_runner")]
        match[side]["deck"] = [_v2_card("hold_position")]
        match[side]["energy"] = 2
        match[side]["max_energy"] = 2

    be2_play_card(match, card_id="spark_runner", side="player")
    be2_play_card(match, card_id="spark_runner", side="opponent")
    be2_ready(match, side="player")

    assert match["round"] == 1
    assert match["player"]["ready"] is True
    assert match["opponent"]["ready"] is False

    be2_ready(match, side="opponent")

    assert match["round"] == 2
    assert match["phase"] == "choose_action"
    for side in ("player", "opponent"):
        assert match[side]["intent"] is None
        assert match[side]["played_card"] is None
        assert match[side]["ready"] is False
        assert match[side]["energy"] == match[side]["max_energy"] == 3
        assert [card["id"] for card in match[side]["hand"]] == ["hold_position"]


def test_pvp_ready_does_not_depend_on_bot():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-no-bot",
    )
    start_round(match)
    match["opponent"]["hand"] = [_v2_card("spark_runner")]
    match["opponent"]["deck"] = []

    be2_ready(match, side="player")

    assert match["round"] == 1
    assert match["opponent"]["intent"] is None
    assert match["opponent"]["played_card"] is None
    assert match["opponent"]["ready"] is False

    be2_ready(match, side="opponent")

    assert match["round"] == 2


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
