from services.rebirth_balance_lab import (
    decision_regret,
    initiative_report,
    paired_matchup,
    round_robin,
    summarize_regret,
)


def _fake_simulator(**kwargs):
    player = kwargs["player_card_ids"][0]
    bot = kwargs["bot_card_ids"][0]
    if player == bot:
        winner = "player" if str(kwargs["seed"]).endswith("0") else "bot"
    else:
        winner = "player" if player < bot else "bot"
    return {"winner": winner, "turns": 8}


def test_paired_matchup_swaps_sides_for_every_seed():
    report = paired_matchup(
        ["a"],
        ["b"],
        deck_a_name="Aggro",
        deck_b_name="Control",
        seeds=["s0", "s1"],
        simulator=_fake_simulator,
    )
    assert report["game_count"] == 4
    assert {(game["seed"], game["orientation"]) for game in report["games"]} == {
        ("s0", "ab"),
        ("s0", "ba"),
        ("s1", "ab"),
        ("s1", "ba"),
    }
    assert report["summary"]["deck_win_rates"]["Aggro"] == 1.0


def test_mirror_and_initiative_are_reported_separately():
    mirror = paired_matchup(["a"], ["a"], seeds=["s0", "s1"], simulator=_fake_simulator)
    initiative = initiative_report([mirror])
    assert mirror["summary"]["deck_win_rates"]["A"] == 0.5
    assert initiative["player_side_win_rate"] == 0.5
    assert initiative["initiative_bias"] == 0.0


def test_round_robin_is_deterministic_and_serializable():
    report = round_robin(
        {"Aggro": ["a"], "Control": ["c"], "Mid": ["b"]},
        seeds=2,
        simulator=_fake_simulator,
    )
    assert report["deck_count"] == 3
    assert set(report["matrix"]) == {"Aggro", "Control", "Mid"}
    assert len(report["matchups"]) == 6
    assert report["standings"][0]["deck"] == "Aggro"


def test_regret_helpers_report_meaningful_mistakes():
    assert decision_regret(8, 11) == 3.0
    assert decision_regret(12, 11) == 0.0
    summary = summarize_regret(
        [
            {"chosen_score": 8, "best_score": 11},
            {"chosen_score": 10, "best_score": 10.5},
            {"chosen_score": None, "best_score": 9},
        ],
        meaningful_threshold=1,
    )
    assert summary["decision_count"] == 2
    assert summary["meaningful_regret_count"] == 1
    assert summary["average_regret"] == 1.75
