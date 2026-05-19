from copy import deepcopy

from services.rebirth.rebirth_engine import play_rebirth_card, resolve_rebirth_round, select_intent, start_rebirth_match
from services.rebirth.rebirth_state import activate_card_from_hand


def test_rebirth_match_starts_with_expected_state():
    match = start_rebirth_match(seed="engine-start")

    assert match["player"]["hp"] == 30
    assert match["opponent"]["hp"] == 30
    assert len(match["player"]["hand"]) == 4
    assert len(match["opponent"]["hand"]) == 4
    assert match["player"]["active_card"] is None
    assert match["opponent"]["active_card"] is None


def test_rebirth_only_one_active_card_and_replacement_discards_old():
    match = start_rebirth_match(seed="engine-active")
    first = match["player"]["hand"][0]["id"]
    second = match["player"]["hand"][1]["id"]

    activate_card_from_hand(match, "player", first)
    first_active = deepcopy(match["player"]["active_card"])
    activate_card_from_hand(match, "player", second)

    assert match["player"]["active_card"]["id"] == second
    assert len([match["player"]["active_card"]]) == 1
    assert match["player"]["discard"][0]["id"] == first_active["id"]


def test_rebirth_strike_increases_damage():
    strike = start_rebirth_match(seed="strike-a")
    neutral = start_rebirth_match(seed="strike-a")
    card_id = strike["player"]["hand"][0]["id"]

    play_rebirth_card(strike, "player", card_id)
    play_rebirth_card(neutral, "player", neutral["player"]["hand"][0]["id"])
    select_intent(strike, "player", "STRIKE")
    select_intent(neutral, "player", "FOCUS")
    resolve_rebirth_round(strike)
    resolve_rebirth_round(neutral)

    assert strike["opponent"]["hp"] < neutral["opponent"]["hp"]


def test_rebirth_guard_reduces_damage_received():
    guard = start_rebirth_match(seed="guard-a")
    focus = start_rebirth_match(seed="guard-a")

    play_rebirth_card(guard, "player", guard["player"]["hand"][0]["id"])
    play_rebirth_card(focus, "player", focus["player"]["hand"][0]["id"])
    select_intent(guard, "player", "GUARD")
    select_intent(focus, "player", "FOCUS")
    resolve_rebirth_round(guard)
    resolve_rebirth_round(focus)

    assert guard["player"]["hp"] >= focus["player"]["hp"]


def test_rebirth_focus_increases_ambition():
    match = start_rebirth_match(seed="focus-a")

    select_intent(match, "player", "FOCUS")
    resolve_rebirth_round(match)

    assert match["player"]["ambition"] >= 2


def test_rebirth_resolve_generates_log_and_winner():
    match = start_rebirth_match(seed="winner-a")
    card_id = next(card["id"] for card in match["player"]["hand"] if card["attack"] >= 4)

    play_rebirth_card(match, "player", card_id)
    select_intent(match, "player", "STRIKE")
    match["opponent"]["hp"] = 1
    resolve_rebirth_round(match)

    assert match["combat_log"]
    assert match["winner"] == "player"
    assert match["is_finished"] is True

