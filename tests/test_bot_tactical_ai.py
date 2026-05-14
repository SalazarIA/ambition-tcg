from copy import deepcopy

from services.battle_engine_v2 import (
    CARD_CATALOG_V2,
    bot_choose_action,
    choose_intent,
    create_match,
    play_card,
    start_round,
)


def card(card_id):
    return deepcopy(CARD_CATALOG_V2[card_id])


def test_bot_prioritizes_pressure_when_player_hp_is_low():
    match = create_match(seed=5401)
    start_round(match)
    match["player"]["hp"] = 5
    match["opponent"]["hand"] = [card("spark_runner")]
    match["opponent"]["energy"] = 10

    bot_choose_action(match)

    assert match["opponent"]["intent"] == "Strike"
    assert match["opponent"]["board"]["left"]["card_id"] == "spark_runner"
    assert match["opponent"]["ready"] is True


def test_bot_guards_when_low_hp_under_pressure():
    match = create_match(seed=5402)
    start_round(match)
    match["player"]["hand"] = [card("arena_brute")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Strike")
    play_card(match, "player", card_id="arena_brute", lane="left")
    match["opponent"]["hp"] = 8
    match["opponent"]["hand"] = [card("hold_position")]
    match["opponent"]["energy"] = 10

    bot_choose_action(match)

    assert match["opponent"]["intent"] == "Guard"
    assert match["opponent"]["shield"] >= 7
    assert match["opponent"]["ready"] is True


def test_bot_prioritizes_creature_when_board_is_empty():
    match = create_match(seed=5403)
    start_round(match)
    match["opponent"]["hand"] = [card("hold_position"), card("spark_runner")]
    match["opponent"]["energy"] = 10

    bot_choose_action(match)

    assert match["opponent"]["board"]["left"]["card_id"] == "spark_runner"


def test_bot_does_not_stall_without_playable_cards():
    match = create_match(seed=5404)
    start_round(match)
    match["opponent"]["hand"] = [card("arena_brute")]
    match["opponent"]["energy"] = 0

    bot_choose_action(match)

    assert match["opponent"]["ready"] is True
    assert match["opponent"]["played_this_round"] is False
