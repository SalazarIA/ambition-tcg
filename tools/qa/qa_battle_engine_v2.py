# =========================================================
# QA Battle Engine V2
# Validates complete card battler flow.
# =========================================================

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.battle_engine_v2 import (
    MAX_ROUNDS,
    choose_intent,
    create_match,
    empty_lanes,
    play_card,
    play_full_bot_match,
    playable_cards,
    request_unleash,
    resolve_round,
    start_round,
    validate_match_integrity,
)


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_create_and_start():
    match = create_match(seed=1)
    assert_true(match["phase"] == "created", "match should be created")
    assert_true(len(match["player"]["hand"]) == 5, "player should start with 5 cards")

    start_round(match)

    assert_true(match["phase"] == "choose_action", "phase should be choose_action")
    assert_true(match["round"] == 1, "round should be 1")
    assert_true(len(match["player"]["hand"]) == 5, "player should preserve opening hand on round 1")

    ok, errors = validate_match_integrity(match)
    assert_true(ok, f"integrity errors: {errors}")


def test_intent_does_not_play_card():
    match = create_match(seed=2)
    start_round(match)

    hand_before = len(match["player"]["hand"])
    choose_intent(match, "player", "Strike")
    hand_after = len(match["player"]["hand"])

    assert_true(hand_before == hand_after, "intent should not play card")


def test_play_creature_to_field():
    match = create_match(seed=3)
    start_round(match)
    choose_intent(match, "player", "Strike")

    cards = playable_cards(match["player"])
    creature = next((card for card in cards if card.get("kind") == "creature"), None)

    assert_true(creature is not None, "expected playable creature")

    play_card(match, "player", card_id=creature["id"], lane=empty_lanes(match["player"])[0])

    creature_in_lane = next(card for card in match["player"]["board"].values() if card)
    assert_true(creature_in_lane is not None, "creature should occupy a lane")
    assert_true(creature_in_lane["current_hp"] > 0, "lane creature should have hp")


def test_round_resolves():
    match = create_match(seed=4)
    start_round(match)

    choose_intent(match, "player", "Strike")
    cards = playable_cards(match["player"])
    if cards:
        lane = empty_lanes(match["player"])[0] if cards[0].get("kind") == "creature" else None
        play_card(match, "player", card_id=cards[0]["id"], lane=lane)

    match["player"]["ready"] = True
    resolve_round(match)

    assert_true(match["phase"] in {"choose_action", "finished"}, "round should advance or finish")

    ok, errors = validate_match_integrity(match)
    assert_true(ok, f"integrity errors: {errors}")


def test_unleash():
    match = create_match(seed=5)
    start_round(match)

    match["player"]["ambition"] = 10
    request_unleash(match, "player")

    assert_true(match["player"]["unleash"] is True, "unleash should be prepared")
    assert_true(match["player"]["ambition"] == 0, "ambition should be spent")


def test_300_matches():
    total = 300
    winners = Counter()
    reasons = Counter()
    rounds = []

    for seed in range(total):
        match = play_full_bot_match(seed=seed)
        ok, errors = validate_match_integrity(match)

        assert_true(ok, f"integrity failed seed {seed}: {errors}")
        assert_true(match["winner"] in {"player", "opponent", "draw"}, f"invalid winner seed {seed}")
        assert_true(match["round"] <= MAX_ROUNDS + 1, f"too many rounds seed {seed}")

        winners[match["winner"]] += 1
        reasons[match["reason"]] += 1
        rounds.append(match["round"])

    avg_rounds = sum(rounds) / len(rounds)

    print("")
    print("=== BATTLE ENGINE V2 SIMULATION ===")
    print(f"Matches: {total}")
    print(f"Average rounds: {avg_rounds:.2f}")
    print(f"Min rounds: {min(rounds)}")
    print(f"Max rounds: {max(rounds)}")
    print(f"Winners: {dict(winners)}")
    print(f"Reasons: {dict(reasons)}")

    draw_rate = winners.get("draw", 0) / total
    assert_true(draw_rate <= 0.08, f"draw rate too high: {draw_rate:.1%}")
    assert_true(5 <= avg_rounds <= 14, f"average rounds out of target: {avg_rounds:.2f}")

    print("PASS: 300 V2 simulated duels completed")


def main():
    print("=== QA BATTLE ENGINE V2 ===")

    test_create_and_start()
    print("PASS create_and_start")

    test_intent_does_not_play_card()
    print("PASS intent_does_not_play_card")

    test_play_creature_to_field()
    print("PASS play_creature_to_field")

    test_round_resolves()
    print("PASS round_resolves")

    test_unleash()
    print("PASS unleash")

    test_300_matches()

    print("")
    print("ALL BATTLE ENGINE V2 QA PASSED")


if __name__ == "__main__":
    main()
