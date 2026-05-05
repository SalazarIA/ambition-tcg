from game.deck import deck_analysis_v115, full_deck_analysis
from services.card_stats import played_cards_for_stats
from services.match_payloads import (
    build_game_state_payloads,
    build_post_match_payload,
    find_player_key,
    history_result_for_ending,
    perspective_battle_events,
)


def make_player(name, sid, *, is_bot=False):
    return {
        "name": name,
        "sid": sid,
        "hp": 3200,
        "deck": [{"id": "d1"}],
        "graveyard": [],
        "hand": [{"id": "h1"}],
        "field_m": None,
        "field_st": None,
        "ready": False,
        "energy": 1,
        "max_energy": 1,
        "ambition": 0,
        "is_bot": is_bot,
        "intent": "Strike",
    }


def test_match_payload_helpers_keep_player_perspective():
    match = {
        "p1": make_player("Alice", "sid-a"),
        "p2": make_player("Bob", "sid-b"),
        "round": 2,
        "phase": "Set Phase",
        "resolving": False,
    }

    assert find_player_key(match, "sid-a") == "p1"
    assert find_player_key(match, "sid-b") == "p2"
    assert find_player_key(match, "missing") is None

    payloads = build_game_state_payloads("room-1", match)

    assert [sid for sid, _state in payloads] == ["sid-a", "sid-b"]
    assert payloads[0][1]["me"]["name"] == "Alice"
    assert payloads[0][1]["enemy"]["name"] == "Bob"


def test_battle_events_are_mirrored_for_second_player():
    events = [
        {"side": "player", "to": "enemy", "from": "player", "amount": 100},
        {"side": "enemy", "to": "player", "from": "enemy", "amount": 50},
    ]

    assert perspective_battle_events(events, "p1") == events
    assert perspective_battle_events(events, "p2") == [
        {"side": "enemy", "to": "player", "from": "enemy", "amount": 100},
        {"side": "player", "to": "enemy", "from": "player", "amount": 50},
    ]


def test_post_match_payload_and_history_result_helpers():
    match = {
        "p1": make_player("Winner", "sid-w"),
        "p2": make_player("Loser", "sid-l"),
        "round": 3,
        "is_bot_match": True,
    }

    payload = build_post_match_payload(match, "p1", "WIN", {"coins": 10, "xp": 5})

    assert payload["mode"] == "bot"
    assert payload["summary"]["title"] == "Victory"
    assert payload["viewer"]["name"] == "Winner"
    assert payload["opponent"]["name"] == "Loser"
    assert history_result_for_ending("p1", "completed") == "FINISHED"
    assert history_result_for_ending("p1", "disconnect") == "DISCONNECT"
    assert history_result_for_ending("DRAW", "completed") == "DRAW"


def test_card_stats_collects_graveyard_and_field_cards():
    player = {
        "graveyard": [{"id": "g1"}, None],
        "field_m": {"id": "m1"},
        "field_st": {"id": "s1"},
    }

    assert played_cards_for_stats(player) == [
        {"id": "g1"},
        {"id": "m1"},
        {"id": "s1"},
    ]


def test_deck_analysis_exports_stay_compatible():
    assert full_deck_analysis([])["stats"]["total"] == 0
    assert "warnings" in deck_analysis_v115([])
