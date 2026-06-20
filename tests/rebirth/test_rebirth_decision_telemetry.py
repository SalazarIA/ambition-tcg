from services.rebirth_live_balance import live_balance_report
from services.rebirth_telemetry import (
    REBIRTH_DECISION_TELEMETRY_EVENT,
    build_decision_made_payload,
    build_decision_telemetry_payload,
)


def _decision_event(event_id, **payload):
    return {
        "id": event_id,
        "event_type": REBIRTH_DECISION_TELEMETRY_EVENT,
        "payload": payload,
    }


def test_decision_payload_is_allowlisted_clean_and_derives_regret():
    payload = build_decision_telemetry_payload(
        {
            "actor": " player ",
            "action_type": "  attack\n",
            "legal_action_count": "4",
            "chosen_action_id": " action:chosen ",
            "chosen_action_fingerprint": " fp-123 ",
            "best_action_id": "action:best",
            "chosen_score": "7.25",
            "best_score": 9,
            "elapsed_ms": "31",
            "turn": "6",
            "profile_id": " aggressive ",
            "difficulty": " hard ",
            "email": "private@example.com",
            "user_id": 991,
            "metadata": {"authorization": "secret"},
        }
    )

    assert payload == {
        "actor": "human",
        "action_type": "attack",
        "legal_action_count": 4,
        "chosen_action_id": "action:chosen",
        "chosen_action_fingerprint": "fp-123",
        "best_action_id": "action:best",
        "chosen_score": 7.25,
        "best_score": 9.0,
        "regret": 1.75,
        "decision_elapsed_ms": 31,
        "turn": 6,
        "profile": "aggressive",
        "difficulty": "hard",
    }
    assert build_decision_made_payload(actor="automated", action_type="pass", legal_action_count=1) == {
        "actor": "bot",
        "action_type": "pass",
        "legal_action_count": 1,
    }


def test_live_balance_aggregates_decisions_and_legacy_field_aliases():
    events = [
        _decision_event(
            1,
            action_type="attack",
            actor="human",
            regret=0,
            chosen_score=10,
            best_score=10,
            decision_elapsed_ms=10,
            profile="aggressive",
            difficulty="hard",
        ),
        _decision_event(
            2,
            action_type="attack",
            actor="human",
            regret=2,
            chosen_score=8,
            best_score=10,
            decision_elapsed_ms=30,
            profile_id="aggressive",
            difficulty="hard",
        ),
        _decision_event(
            3,
            action_type="summon",
            actor="bot",
            chosen_score=5,
            best_score=9,
            decision_elapsed_ms=50,
            bot_profile_id="defensive",
            difficulty="normal",
        ),
        {"id": 4, "event_type": "card_played", "payload": {"card_id": "card_001"}},
    ]

    report = live_balance_report(events)
    decisions = report["decisions"]

    assert decisions["decision_count"] == 3
    assert decisions["scored_decision_count"] == 3
    assert decisions["average_regret"] == 2.0
    assert decisions["regret_p95"] == 4.0
    assert decisions["max_regret"] == 4.0
    assert decisions["suboptimal_decision_count"] == 2
    assert decisions["suboptimal_decision_rate"] == 0.667
    assert decisions["average_decision_elapsed_ms"] == 30.0
    by_actor = {item["actor"]: item for item in decisions["by_actor"]}
    assert by_actor["human"]["decision_count"] == 2
    assert by_actor["bot"]["decision_count"] == 1

    by_action = {item["action_type"]: item for item in decisions["by_action_type"]}
    assert by_action["attack"]["decision_count"] == 2
    assert by_action["attack"]["average_regret"] == 1.0
    assert by_action["summon"]["suboptimal_decision_rate"] == 1.0

    by_profile = {item["profile"]: item for item in decisions["by_profile"]}
    assert by_profile["aggressive"]["decision_count"] == 2
    assert by_profile["defensive"]["decision_count"] == 1

    by_difficulty = {item["difficulty"]: item for item in decisions["by_difficulty"]}
    assert by_difficulty["hard"]["decision_count"] == 2
    assert by_difficulty["normal"]["decision_count"] == 1


def test_live_balance_keeps_empty_decision_metrics_additive():
    report = live_balance_report([])

    assert report["version"] == "live-balance-v1"
    assert report["decisions"]["decision_count"] == 0
    assert report["decisions"]["average_regret"] is None
    assert report["decisions"]["by_actor"] == []
    assert report["decisions"]["by_action_type"] == []


def test_live_balance_loads_all_terminal_matches_beyond_general_event_window():
    terminal = [
        {
            "id": 10_000 + index,
            "event_type": "match_finished",
            "payload": {
                "match_id": f"match-{index}",
                "is_finished": True,
                "winner": "player",
            },
        }
        for index in range(500)
    ]

    class Repo:
        def __init__(self):
            self.calls = []

        def query_telemetry_events(self, event_types=None, *, limit=None, since=None):
            self.calls.append({"event_types": event_types, "limit": limit, "since": since})
            return terminal if event_types else []

    from services.rebirth_live_balance import live_balance_payload

    repo = Repo()
    report = live_balance_payload(repo, limit=50)

    assert report["human_match_gate"]["state"] == "ready"
    assert report["human_match_gate"]["observed_finished_matches"] == 500
    assert repo.calls[-1]["event_types"] == ("match_finished", "match_abandoned")
    assert repo.calls[-1]["limit"] is None


def test_human_decision_snapshot_validates_legal_actions(monkeypatch):
    import app as ambition_app

    seen = {}

    def fake_legal_actions(match, actor="player", *, verify=True):
        seen["verify"] = verify
        return [
            {"type": "end_turn", "payload": {"turn": 1}},
            {"type": "play_card", "payload": {"card_instance_id": "card-1"}},
        ]

    monkeypatch.setattr(ambition_app, "legal_actions", fake_legal_actions)
    payload = ambition_app.decision_telemetry_snapshot(
        {
            "turn": 1,
            "player": {"field": [], "hp": 30},
            "bot": {"field": [], "hp": 30},
        },
        {"type": "end_turn", "payload": {"turn": 1}},
    )

    # A telemetria de decisão é observacional: enumera as opções com verify=False
    # para não reexecutar o dispatcher (simular `end_turn` rodaria a fase inteira
    # do bot no caminho quente de cada jogada).
    assert seen["verify"] is False
    assert payload["actor"] == "human"
    assert payload["legal_action_count"] == 2


def test_bot_legal_action_count_is_measured_before_beam_pruning():
    from app import _bot_legal_attack_count, bot_decision_telemetry_payloads

    def monster(instance_id, field_slot):
        return {
            "id": instance_id,
            "instance_id": instance_id,
            "name": instance_id,
            "type": "MONSTER",
            "attack": 2,
            "guard": 10,
            "current_guard": 10,
            "field_slot": field_slot,
        }

    match = {
        "turn": 3,
        "player": {"hp": 30, "field": [monster(f"player-{index}", index) for index in range(3)]},
        "bot": {"hp": 30, "field": [monster(f"bot-{index}", index) for index in range(3)]},
    }

    assert _bot_legal_attack_count(match) == 9
    decisions = bot_decision_telemetry_payloads(
        match,
        [
            {
                "event_type": "ATTACK_DECLARED",
                "actor": "bot",
                "payload": {
                    "automated": True,
                    "attacker_instance_id": "bot-0",
                    "target_instance_id": "player-0",
                    "legal_action_count": 6,
                },
            }
        ],
    )
    assert decisions[0]["actor"] == "bot"
    assert decisions[0]["legal_action_count"] == 9


def test_live_balance_deduplicates_terminal_outcomes_and_keeps_legacy_events():
    report = live_balance_report(
        [
            {
                "id": 1,
                "event_type": "match_finished",
                "payload": {"match_id": "finished", "is_finished": True, "winner": "player"},
            },
            {
                "id": 2,
                "event_type": "match_finished",
                "payload": {"match_id": "finished", "is_finished": True, "winner": "player"},
            },
            {"id": 3, "event_type": "match_won", "payload": {"match_id": "finished"}},
            {"id": 4, "event_type": "match_won", "payload": {"match_id": "legacy"}},
            {"id": 5, "event_type": "match_won", "payload": {"match_id": "legacy"}},
        ]
    )

    assert report["overall"]["matches_finished"] == 1
    assert report["terminal_events"]["wins"] == 2
