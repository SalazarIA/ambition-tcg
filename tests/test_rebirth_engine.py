from copy import deepcopy

from services.rebirth.rebirth_engine import (
    DAMAGE_CAP,
    bot_select_action,
    play_rebirth_card,
    resolve_rebirth_round,
    select_intent,
    start_rebirth_match,
)
from services.rebirth.rebirth_state import activate_card_from_hand


def test_rebirth_match_starts_with_expected_state():
    match = start_rebirth_match(seed="engine-start")

    assert match["player"]["hp"] == 32
    assert match["opponent"]["hp"] == 32
    assert len(match["player"]["hand"]) == 4
    assert len(match["opponent"]["hand"]) == 4
    assert match["player"]["active_card"] is None
    assert match["opponent"]["active_card"] is None
    assert match["phase"] == "INTENT"


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


def test_rebirth_play_card_logs_replacement():
    match = start_rebirth_match(seed="engine-replace-log")
    first = match["player"]["hand"][0]["id"]
    second = match["player"]["hand"][1]["id"]

    play_rebirth_card(match, "player", first)
    play_rebirth_card(match, "player", second)

    assert match["player"]["discard"]
    assert any(entry["type"] == "active_card_replaced" for entry in match["combat_log"])


def test_rebirth_bot_selects_card_and_intent():
    match = start_rebirth_match(seed="engine-bot")

    bot_select_action(match)

    assert match["opponent"]["active_card"] is not None
    assert match["opponent"]["selected_intent"] in {"STRIKE", "GUARD", "FOCUS"}


def test_rebirth_strike_increases_damage():
    strike = start_rebirth_match(seed="strike-a")
    neutral = start_rebirth_match(seed="strike-a")

    play_rebirth_card(strike, "player", strike["player"]["hand"][0]["id"])
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
    assert any(entry["type"] == "guard_applied" for entry in guard["combat_log"])


def test_rebirth_focus_increases_ambition():
    match = start_rebirth_match(seed="focus-a")

    select_intent(match, "player", "FOCUS")
    resolve_rebirth_round(match)

    assert match["player"]["ambition"] >= 2
    assert any(entry["type"] == "ambition_gained" for entry in match["combat_log"])


def test_rebirth_phase_advances_through_resolve_back_to_intent():
    match = start_rebirth_match(seed="phase-a")

    assert match["phase"] == "INTENT"
    play_rebirth_card(match, "player", match["player"]["hand"][0]["id"])
    select_intent(match, "player", "FOCUS")
    assert match["phase"] == "ACTION"
    resolve_rebirth_round(match)

    assert match["round"] == 2
    assert match["phase"] == "INTENT"


def test_rebirth_damage_is_capped():
    match = start_rebirth_match(seed="damage-cap")
    play_rebirth_card(match, "player", match["player"]["hand"][0]["id"])
    match["player"]["active_card"]["attack"] = 99
    select_intent(match, "player", "STRIKE")
    select_intent(match, "opponent", "FOCUS")
    resolve_rebirth_round(match)

    player_damage_events = [
        entry for entry in match["combat_log"]
        if entry["type"] == "damage_dealt" and entry["payload"].get("source") == "player"
    ]
    assert player_damage_events
    assert player_damage_events[-1]["payload"]["amount"] <= DAMAGE_CAP


def test_rebirth_resolve_generates_rich_log_and_cinematic():
    match = start_rebirth_match(seed="rich-log")

    play_rebirth_card(match, "player", match["player"]["hand"][0]["id"])
    select_intent(match, "player", "STRIKE")
    resolve_rebirth_round(match)

    assert any(entry["type"] == "attack_calculated" for entry in match["combat_log"])
    assert any(entry["type"] == "damage_dealt" for entry in match["combat_log"])
    assert any(entry["type"] == "round_resolved" for entry in match["combat_log"])
    assert match["cinematic_event"]
    assert {"type", "title", "message", "intensity"} <= set(match["cinematic_event"])


def test_rebirth_match_finished_when_hp_reaches_zero():
    match = start_rebirth_match(seed="winner-a")
    card_id = next(card["id"] for card in match["player"]["hand"] if card["attack"] >= 4)

    play_rebirth_card(match, "player", card_id)
    select_intent(match, "player", "STRIKE")
    match["opponent"]["hp"] = 1
    resolve_rebirth_round(match)

    assert match["winner"] == "player"
    assert match["is_finished"] is True
    assert any(entry["type"] == "match_finished" for entry in match["combat_log"])
