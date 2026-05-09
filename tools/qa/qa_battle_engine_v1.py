# =========================================================
# QA Battle Engine V1
# Valida motor de duelo completo sem frontend.
# =========================================================

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.battle_engine_v1 import (
    MAX_ROUNDS,
    choose_action,
    create_match,
    playable_cards,
    play_full_bot_match,
    resolve_round,
    start_round,
    validate_match_integrity,
)


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_create_match():
    match = create_match(seed=1)
    assert_true(match["phase"] == "round_start", "match should start in round_start")
    assert_true(len(match["player"]["hand"]) == 5, "player should start with 5 cards")
    assert_true(len(match["opponent"]["hand"]) == 5, "opponent should start with 5 cards")
    ok, errors = validate_match_integrity(match)
    assert_true(ok, f"integrity failed: {errors}")


def test_round_flow():
    match = create_match(seed=2)
    start_round(match)

    assert_true(match["round"] == 1, "round should be 1")
    assert_true(match["phase"] == "choose_action", "phase should be choose_action")

    cards = playable_cards(match["player"])
    if cards:
        chosen = cards[0]
        hand_index = match["player"]["hand"].index(chosen)
        choose_action(match, "player", "Strike", hand_index)
    else:
        choose_action(match, "player", "Focus", None)

    resolve_round(match)

    assert_true(match["phase"] in {"round_start", "finished"}, "phase should advance")
    ok, errors = validate_match_integrity(match)
    assert_true(ok, f"integrity failed: {errors}")


def test_100_full_matches():
    winners = Counter()
    rounds = []

    for seed in range(100):
        match = play_full_bot_match(seed=seed)
        ok, errors = validate_match_integrity(match)

        assert_true(ok, f"integrity failed on seed {seed}: {errors}")
        assert_true(match["winner"] in {"player", "opponent", "draw"}, f"invalid winner on seed {seed}")
        assert_true(match["round"] <= MAX_ROUNDS, f"match exceeded max rounds on seed {seed}")

        winners[match["winner"]] += 1
        rounds.append(match["round"])

    avg_rounds = sum(rounds) / len(rounds)

    print("")
    print("=== BATTLE ENGINE V1 SIMULATION ===")
    print(f"Matches: {len(rounds)}")
    print(f"Average rounds: {avg_rounds:.2f}")
    print(f"Winners: {dict(winners)}")
    print("PASS: 100 simulated duels completed without crash")


def main():
    print("=== QA BATTLE ENGINE V1 ===")

    test_create_match()
    print("PASS create_match")

    test_round_flow()
    print("PASS round_flow")

    test_100_full_matches()

    print("")
    print("ALL BATTLE ENGINE V1 QA PASSED")


if __name__ == "__main__":
    main()
