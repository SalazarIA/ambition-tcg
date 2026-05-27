"""Telemetry analyzer covers per-profile balancing signals.

`record_match_telemetry` now writes `bot_profile_id`, `max_chain_length`
and `first_duel` so the offline analyzer can group real matches by
profile/campaign node. This locks the analyzer + query contract so the
balancing pass that consumes it does not silently break.
"""

from services.rebirth_persistence import RebirthRepository
from tools.rebirth_telemetry_analyzer import analyze


def _make_repo(flask_app):
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.ensure_schema()
    return repo


def _emit_match(repo, *, bot_profile_id, winner, turn, max_chain_length=2, first_duel=False, abandoned=False, campaign_node=None):
    payload = {
        "bot_profile_id": bot_profile_id,
        "winner": winner,
        "turn": turn,
        "is_finished": not abandoned,
        "max_chain_length": max_chain_length,
        "first_duel": first_duel,
        "campaign_node": campaign_node,
    }
    event_type = "match_abandoned" if abandoned else "match_finished"
    repo.record_telemetry_event(event_type, payload)


def test_query_telemetry_events_filters_by_type(flask_app):
    repo = _make_repo(flask_app)
    _emit_match(repo, bot_profile_id="aggressive", winner="bot", turn=10)
    _emit_match(repo, bot_profile_id="defensive", winner="player", turn=14)
    _emit_match(repo, bot_profile_id="aggressive", winner="player", turn=8, abandoned=True)

    finished = repo.query_telemetry_events(event_types=("match_finished",))
    abandoned = repo.query_telemetry_events(event_types=("match_abandoned",))
    combined = repo.query_telemetry_events(event_types=("match_finished", "match_abandoned"))

    assert len(finished) == 2
    assert len(abandoned) == 1
    assert len(combined) == 3
    assert {event["event_type"] for event in combined} == {"match_finished", "match_abandoned"}
    assert combined[0]["id"] > combined[-1]["id"]


def test_analyzer_separates_profiles_and_flags_difficulty_spread(flask_app):
    repo = _make_repo(flask_app)
    for _ in range(10):
        _emit_match(repo, bot_profile_id="defensive", winner="player", turn=15)
    for _ in range(10):
        _emit_match(repo, bot_profile_id="aggressive", winner="bot", turn=12)
    _emit_match(repo, bot_profile_id="aggressive", winner="player", turn=11)
    for _ in range(2):
        _emit_match(repo, bot_profile_id="defensive", winner="bot", turn=22, abandoned=True)

    events = repo.query_telemetry_events(event_types=("match_finished", "match_abandoned"))
    report = analyze(events)

    profiles = {profile["label"]: profile for profile in report["by_profile"]}
    assert set(profiles) == {"aggressive", "defensive"}
    assert profiles["defensive"]["player_win_rate"] == 1.0
    assert profiles["aggressive"]["player_win_rate"] < 0.2
    assert "profile_difficulty_spread_high" in report["overall"]["flags"]
    assert profiles["defensive"]["matches_abandoned"] == 2
    assert profiles["defensive"]["abandon_rate"] is not None


def test_analyzer_excludes_first_duel_by_default(flask_app):
    repo = _make_repo(flask_app)
    for _ in range(5):
        _emit_match(repo, bot_profile_id="novice", winner="player", turn=6, first_duel=True)
    for _ in range(5):
        _emit_match(repo, bot_profile_id="aggressive", winner="bot", turn=20)

    events = repo.query_telemetry_events(event_types=("match_finished",))
    excluded = analyze(events)
    included = analyze(events, exclude_first_duel=False)

    assert {profile["label"] for profile in excluded["by_profile"]} == {"aggressive"}
    assert {profile["label"] for profile in included["by_profile"]} == {"aggressive", "novice"}
    assert excluded["sample_size"] == 5
    assert included["sample_size"] == 10


def test_analyzer_groups_campaign_nodes(flask_app):
    repo = _make_repo(flask_app)
    _emit_match(repo, bot_profile_id="aggressive", winner="player", turn=11, campaign_node="node_03_pyrelord")
    _emit_match(repo, bot_profile_id="aggressive", winner="bot", turn=18, campaign_node="node_03_pyrelord")
    _emit_match(repo, bot_profile_id="defensive", winner="player", turn=20, campaign_node="node_02_guardian")

    events = repo.query_telemetry_events(event_types=("match_finished",))
    report = analyze(events)

    node_labels = {node["label"]: node for node in report["by_campaign_node"]}
    assert set(node_labels) == {"node_02_guardian", "node_03_pyrelord"}
    assert node_labels["node_03_pyrelord"]["matches_finished"] == 2
    assert node_labels["node_03_pyrelord"]["player_win_rate"] == 0.5


def test_record_match_telemetry_includes_bot_profile_id(client):
    from app import record_match_telemetry, app as ambition_app
    repo = RebirthRepository(ambition_app.config["REBIRTH_DB_PATH"])
    match = {
        "match_id": "telemetry-profile",
        "turn": 12,
        "phase": "main",
        "is_finished": True,
        "winner": "player",
        "result": {"outcome": "player_victory"},
        "player": {"hp": 22},
        "bot": {"hp": 0},
        "bot_profile": {"id": "aggressive"},
        "first_duel": False,
        "events": [
            {"effect_chain_id": "chain-a"},
            {"effect_chain_id": "chain-a"},
            {"effect_chain_id": "chain-b"},
        ],
    }
    record_match_telemetry(repo, None, match, "match_finished")

    finished = repo.query_telemetry_events(event_types=("match_finished",), limit=1)
    assert finished, "expected match_finished event to be persisted"
    payload = finished[0]["payload"]
    assert payload["bot_profile_id"] == "aggressive"
    assert payload["max_chain_length"] == 2
    assert payload["winner"] == "player"
    assert payload["first_duel"] is False
