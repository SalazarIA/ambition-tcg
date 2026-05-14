import pytest
from copy import deepcopy

from services.battle_engine_v2 import (
    CARD_CATALOG_V2,
    CARD_REGISTRY_SCHEMA,
    KEYWORD_REGISTRY_V1,
    STARTING_HP,
    STARTING_HAND_SIZE,
    bot_choose_action,
    card_has_keyword,
    choose_intent,
    create_match,
    empty_lanes,
    play_card,
    resolve_round,
    start_round,
)
from services.arena_command_v1 import ARENA_COMMAND_SCHEMA, normalize_arena_command
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


def card(card_id):
    return deepcopy(CARD_CATALOG_V2[card_id])


def lane_for(payload, card_id):
    selected = next((c for c in payload["me"]["hand"] if c["id"] == card_id), {})
    if selected.get("type") == "Monster":
        return payload["legal_actions"]["legal_lanes"][0]
    return None


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
    match["player"]["ready"] = True
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
    be2_play_card(match, card_id=playable_id, lane=lane_for(after_intent, playable_id))
    after_play = build_be2_arena_payload(match)
    assert after_play["phase"] == "ready"
    assert after_play["turn"]["primary_action"] == "ready"
    assert after_play["legal_actions"]["can_play_cards"] is False
    assert after_play["legal_actions"]["can_ready"] is True

    with pytest.raises(ValueError, match="Only one card"):
        be2_play_card(match, card_id=after_play["me"]["hand"][0]["id"], lane="left")


def test_arena_command_v1_normalizes_play_card_payload():
    command = normalize_arena_command({
        "schema": ARENA_COMMAND_SCHEMA,
        "action": "play-card",
        "card_id": "spark_runner",
        "card_index": "0",
        "lane": "Left",
        "target": "",
    })

    assert command["schema"] == ARENA_COMMAND_SCHEMA
    assert command["action"] == "play_card"
    assert command["card_id"] == "spark_runner"
    assert command["card_index"] == 0
    assert command["lane"] == "Left"
    assert command["target"] is None


def test_match_engine_facade_runs_arena_command_v1_flow():
    emits = []
    active_matches = {}
    player_rooms = {}
    facade = MatchEngineFacade(
        active_matches,
        player_rooms,
        lambda event, payload, room=None: emits.append((event, payload, room)),
    )

    facade.run_command("sid-command", {"action": "start_training"})
    room_code, match = facade.match_for_sid("sid-command")

    assert room_code == "be2_training_sid-command"
    assert match["be2"] is True

    facade.run_command("sid-command", {"action": "set_intent", "intent": "Strike"})
    match["player"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    facade.run_command("sid-command", {
        "action": "play_card",
        "card_id": "spark_runner",
        "lane": "left",
    })

    assert match["player"]["board"]["left"]["card_id"] == "spark_runner"
    assert any(event == "az48_state" for event, _payload, _room in emits)


def test_be2_registry_and_keyword_metadata_are_explicit():
    assert CARD_CATALOG_V2["silent_guardian"]["registry"] == CARD_REGISTRY_SCHEMA
    assert card_has_keyword(CARD_CATALOG_V2["silent_guardian"], "guarded")
    assert KEYWORD_REGISTRY_V1["guarded"]["implemented"] is True

    match = create_be2_training_match(sid="registry-payload")
    be2_start(match)
    payload = build_be2_arena_payload(match)

    assert payload["card_registry"]["schema"] == CARD_REGISTRY_SCHEMA
    assert payload["keyword_registry"]["keywords"]["guarded"]["name"] == "Guarded"


def test_be2_payload_includes_structured_round_events():
    match = create_be2_training_match(sid="events-test")
    be2_start(match)
    be2_set_intent(match, "Guard")
    payload = build_be2_arena_payload(match)
    playable_id = payload["legal_actions"]["playable_card_ids"][0]
    be2_play_card(match, card_id=playable_id, lane=lane_for(payload, playable_id))
    be2_ready(match)

    resolved = build_be2_arena_payload(match)

    assert resolved["round"] >= 2 or resolved["phase"] == "finished"
    assert resolved["events"]
    assert resolved["round_summary"]["events"]
    assert any(event["type"] in {"hero_damage", "shield_gain", "ambition_gain", "lane_hero_damage"} for event in resolved["round_summary"]["events"])


def test_be2_payload_exposes_last_completed_combat_log_for_round_summary():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-round-summary-payload",
    )
    be2_start(match)
    match["player"]["hand"] = [card("spark_runner")]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    be2_set_intent(match, "Focus", side="player")
    be2_set_intent(match, "Focus", side="opponent")
    be2_play_card(match, card_id="spark_runner", side="player", lane="left")
    be2_play_card(match, card_id="spark_runner", side="opponent", lane="left")

    be2_ready(match, side="player")
    be2_ready(match, side="opponent")

    payload = build_be2_arena_payload(match)
    event_types = {event.get("type") for event in payload["combat_log"]}

    assert payload["combat_log"]
    assert payload["last_round_summary"] == payload["round_summary"]
    assert "round_end" in event_types
    assert {"lane_attack", "creature_damage"} & event_types
    assert {event.get("round") for event in payload["combat_log"]} == {1}


def test_training_bot_uses_training_balance_profile():
    match = create_be2_training_match(sid="balance-test")

    assert match["bot_difficulty"] == "training"
    assert match["opponent"]["max_hp"] == 24


def test_be2_rejects_explicit_invalid_card_id():
    match = create_match(seed=42)
    start_round(match)
    choose_intent(match, "player", "Strike")

    with pytest.raises(ValueError, match="Card not found"):
        play_card(match, "player", card_id="not-in-hand")


def test_creature_played_occupies_lane_without_active_replacement():
    match = create_match(seed=1)
    start_round(match)
    choose_intent(match, "player", "Strike")
    match["player"]["hand"] = [card("spark_runner"), card("street_challenger")]
    match["player"]["energy"] = 10

    play_card(match, "player", card_id="spark_runner", lane="left")

    lane_card = match["player"]["board"]["left"]
    assert lane_card["instance_id"]
    assert lane_card["card_id"] == "spark_runner"
    assert lane_card["owner"] == "player"
    assert lane_card["lane"] == "left"
    assert lane_card["current_hp"] == lane_card["max_hp"]
    assert match["player"]["field"]["active"] is None
    assert [c["id"] for c in match["player"]["hand"]] == ["street_challenger"]


def test_occupied_lane_rejects_second_creature():
    match = create_match(seed=2)
    start_round(match)
    choose_intent(match, "player", "Strike")
    match["player"]["hand"] = [card("spark_runner"), card("street_challenger")]
    match["player"]["energy"] = 10

    play_card(match, "player", card_id="spark_runner", lane="center")

    match["player"]["played_card"] = None
    match["player"]["played_this_round"] = False
    with pytest.raises(ValueError, match="Lane is occupied"):
        play_card(match, "player", card_id="street_challenger", lane="center")


def test_invalid_lane_rejects_creature_play():
    match = create_match(seed=3)
    start_round(match)
    choose_intent(match, "player", "Strike")
    match["player"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10

    with pytest.raises(ValueError, match="Invalid lane"):
        play_card(match, "player", card_id="spark_runner", lane="diagonal")


def test_one_card_per_round_is_enforced():
    match = create_match(seed=4)
    start_round(match)
    choose_intent(match, "player", "Strike")
    match["player"]["hand"] = [card("spark_runner"), card("street_challenger")]
    match["player"]["energy"] = 10

    play_card(match, "player", card_id="spark_runner", lane="left")

    with pytest.raises(ValueError, match="Only one card"):
        play_card(match, "player", card_id="street_challenger", lane="right")


def test_empty_hand_can_ready_after_intent():
    match = create_be2_training_match(sid="empty-hand")
    be2_start(match)
    be2_set_intent(match, "Focus")
    match["player"]["hand"] = []

    be2_ready(match)

    assert match["round"] >= 2 or match["phase"] == "finished"


def test_lane_to_lane_combat_damages_creatures():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-combat",
    )
    be2_start(match)
    match["player"]["hand"] = [card("spark_runner")]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    be2_set_intent(match, "Focus", side="player")
    be2_set_intent(match, "Focus", side="opponent")
    be2_play_card(match, card_id="spark_runner", side="player", lane="left")
    be2_play_card(match, card_id="spark_runner", side="opponent", lane="left")

    be2_ready(match, side="player")
    be2_ready(match, side="opponent")

    assert match["player"]["board"]["left"]["current_hp"] == 1
    assert match["opponent"]["board"]["left"]["current_hp"] == 1


def test_guarded_keyword_reduces_combat_damage_on_guard_intent():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-keyword-guarded",
    )
    be2_start(match)
    match["player"]["hand"] = [card("silent_guardian")]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    be2_set_intent(match, "Guard", side="player")
    be2_set_intent(match, "Focus", side="opponent")
    be2_play_card(match, card_id="silent_guardian", side="player", lane="center")
    be2_play_card(match, card_id="spark_runner", side="opponent", lane="center")

    be2_ready(match, side="player")
    be2_ready(match, side="opponent")

    guardian = match["player"]["board"]["center"]
    assert guardian["current_hp"] == 6
    assert card_has_keyword(guardian, "guarded")


def test_focused_keyword_adds_ambition_to_instant_effect():
    match = create_match(seed=5)
    start_round(match)
    choose_intent(match, "player", "Strike")
    match["player"]["hand"] = [card("focus_surge")]
    match["player"]["energy"] = 10

    play_card(match, "player", card_id="focus_surge")

    assert match["player"]["ambition"] == 5
    assert any(discard.get("id") == "focus_surge" for discard in match["player"]["discard"])


def test_combat_log_records_lane_to_lane_events():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-combat-log-lane",
    )
    be2_start(match)
    match["player"]["hand"] = [card("spark_runner")]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    be2_set_intent(match, "Focus", side="player")
    be2_set_intent(match, "Focus", side="opponent")
    be2_play_card(match, card_id="spark_runner", side="player", lane="left")
    be2_play_card(match, card_id="spark_runner", side="opponent", lane="left")

    be2_ready(match, side="player")
    be2_ready(match, side="opponent")

    combat_log = match.get("combat_log") or []
    event_types = {event.get("type") for event in combat_log}
    assert combat_log
    assert all(isinstance(event, dict) for event in combat_log)
    assert {"lane_attack", "creature_damage"} & event_types
    assert "round_end" in event_types


def test_empty_lane_damage_hits_enemy_hero():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-hero-hit",
    )
    be2_start(match)
    match["player"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    be2_set_intent(match, "Focus", side="player")
    be2_set_intent(match, "Focus", side="opponent")
    be2_play_card(match, card_id="spark_runner", side="player", lane="right")

    be2_ready(match, side="player")
    be2_ready(match, side="opponent")

    assert match["opponent"]["hp"] == STARTING_HP - 2


def test_combat_log_records_direct_attack_events():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-combat-log-direct",
    )
    be2_start(match)
    match["player"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    be2_set_intent(match, "Focus", side="player")
    be2_set_intent(match, "Focus", side="opponent")
    be2_play_card(match, card_id="spark_runner", side="player", lane="right")

    be2_ready(match, side="player")
    be2_ready(match, side="opponent")

    combat_log = match.get("combat_log") or []
    event_types = {event.get("type") for event in combat_log}
    assert combat_log
    assert all(isinstance(event, dict) for event in combat_log)
    assert {"direct_attack", "hero_damage"} & event_types
    assert "round_end" in event_types


def test_dead_creature_moves_to_discard_and_lane_clears():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-death",
    )
    be2_start(match)
    match["player"]["hand"] = [card("arena_brute")]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    be2_set_intent(match, "Focus", side="player")
    be2_set_intent(match, "Focus", side="opponent")
    be2_play_card(match, card_id="arena_brute", side="player", lane="center")
    be2_play_card(match, card_id="spark_runner", side="opponent", lane="center")

    be2_ready(match, side="player")
    be2_ready(match, side="opponent")

    assert match["opponent"]["board"]["center"] is None
    assert any(dead.get("card_id") == "spark_runner" for dead in match["opponent"]["discard"])


def test_bot_chooses_intent_plays_creature_and_readies():
    match = create_be2_training_match(sid="bot-core")
    be2_start(match)
    match["opponent"]["hand"] = [card("spark_runner")]
    match["opponent"]["energy"] = 10

    bot_choose_action(match)

    assert match["opponent"]["intent"] in {"Strike", "Focus", "Guard"}
    assert match["opponent"]["ready"] is True
    assert match["opponent"]["board"]["left"]["card_id"] == "spark_runner"


def test_pvp_ready_does_not_invoke_bot_or_resolve_early():
    match = create_be2_match_from_players(
        {"name": "Alice", "sid": "sid-a", "user_id": 1},
        {"name": "Bob", "sid": "sid-b", "user_id": 2},
        "room-no-bot",
    )
    be2_start(match)
    be2_set_intent(match, "Strike", side="player")

    be2_ready(match, side="player")

    assert match["round"] == 1
    assert match["player"]["ready"] is True
    assert match["opponent"]["ready"] is False
    assert match["opponent"]["is_bot"] is False


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
