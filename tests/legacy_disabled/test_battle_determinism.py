from copy import deepcopy

from services.battle_engine_v2 import (
    CARD_CATALOG_V2,
    choose_intent,
    create_match,
    empty_lanes,
    play_card,
    play_full_bot_match,
    playable_cards,
    resolve_round,
    stable_match_snapshot,
    start_round,
)


def card(card_id):
    return deepcopy(CARD_CATALOG_V2[card_id])


def play_first_reasonable_card(match):
    player = match["player"]
    cards = playable_cards(player)
    if not cards:
        return

    creature = next((candidate for candidate in cards if candidate.get("kind") == "creature" and empty_lanes(player)), None)
    chosen = creature or cards[0]
    lane = empty_lanes(player)[0] if chosen.get("kind") == "creature" else None
    target = "enemy_hero" if chosen.get("kind") != "creature" else None
    play_card(match, "player", card_index=player["hand"].index(chosen), lane=lane, target=target)


def run_three_round_script(seed):
    match = create_match(seed=seed)
    start_round(match)

    for intent in ["Strike", "Guard", "Focus"]:
        if match.get("winner"):
            break
        choose_intent(match, "player", intent)
        play_first_reasonable_card(match)
        match["player"]["ready"] = True
        resolve_round(match)

    return stable_match_snapshot(match)


def test_start_round_is_deterministic_for_same_seed():
    first = create_match(seed=49056)
    second = create_match(seed=49056)
    start_round(first)
    start_round(second)

    assert stable_match_snapshot(first) == stable_match_snapshot(second)


def test_strike_play_ready_sequence_is_deterministic():
    def run():
        match = create_match(seed=49057)
        start_round(match)
        match["player"]["hand"] = [card("spark_runner")]
        match["player"]["energy"] = 10
        choose_intent(match, "player", "Strike")
        play_card(match, "player", card_id="spark_runner", lane="left")
        match["player"]["ready"] = True
        resolve_round(match)
        return stable_match_snapshot(match)

    assert run() == run()


def test_three_round_script_is_deterministic():
    assert run_three_round_script(49058) == run_three_round_script(49058)


def test_full_bot_match_result_is_deterministic():
    first = play_full_bot_match(seed=49059)
    second = play_full_bot_match(seed=49059)

    assert first["winner"] == second["winner"]
    assert first["reason"] == second["reason"]
    assert stable_match_snapshot(first) == stable_match_snapshot(second)
