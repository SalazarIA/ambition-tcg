from tools.qa.battle_balance_sim import run_simulation


def test_battle_balance_simulation_contract_is_fast_and_deterministic():
    first = run_simulation(matches=8, seed=5201, max_rounds=30)
    second = run_simulation(matches=8, seed=5201, max_rounds=30)

    assert first == second
    assert first["total_matches"] == 8
    assert first["timeout_count"] == 0
    assert first["integrity_error_count"] == 0
    assert first["cards_played_count"] > 0
    assert first["top_cards_played"]
    assert "dead_hand_cards" in first
    assert 2 <= first["average_rounds"] <= 30
