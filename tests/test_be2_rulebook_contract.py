from copy import deepcopy
from pathlib import Path

from services.battle_engine_v2 import (
    CARD_CATALOG_V2,
    STARTING_ENERGY,
    choose_intent,
    create_match,
    guard_value,
    play_card,
    resolve_combat,
    start_round,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def card(card_id):
    return deepcopy(CARD_CATALOG_V2[card_id])


def resolve_one_round(player_intent, opponent_intent, player_card=None, opponent_card=None):
    match = create_match(seed=5301, opponent_is_bot=False)
    start_round(match)
    match["player"]["hand"] = [card(player_card)] if player_card else []
    match["opponent"]["hand"] = [card(opponent_card)] if opponent_card else []
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    choose_intent(match, "player", player_intent)
    choose_intent(match, "opponent", opponent_intent)

    if player_card:
        play_card(match, "player", card_id=player_card, lane="left")
    if opponent_card:
        play_card(match, "opponent", card_id=opponent_card, lane="left")

    match["player"]["ready"] = True
    match["opponent"]["ready"] = True
    resolve_combat(match)
    return match


def test_rulebook_document_covers_current_be2_contract():
    rulebook = (PROJECT_ROOT / "docs" / "BE2_RULEBOOK.md").read_text()

    for phrase in [
        "Round Phases",
        "Energy",
        "Draw",
        "`Strike`",
        "`Guard`",
        "`Focus`",
        "Lanes And Targeting",
        "Reward And Post-Match Boundary",
    ]:
        assert phrase in rulebook


def test_rulebook_energy_progression_matches_engine():
    match = create_match(seed=5302)
    start_round(match)
    assert match["player"]["max_energy"] == STARTING_ENERGY

    choose_intent(match, "player", "Focus")
    choose_intent(match, "opponent", "Focus")
    match["player"]["ready"] = True
    match["opponent"]["ready"] = True
    resolve_combat(match)
    start_round(match)

    assert match["player"]["max_energy"] == STARTING_ENERGY + 1


def test_guard_intent_reduces_incoming_damage_in_controlled_board():
    guard_match = resolve_one_round("Guard", "Strike", opponent_card="arena_brute")
    focus_match = resolve_one_round("Focus", "Strike", opponent_card="arena_brute")

    assert guard_match["player"]["hp"] > focus_match["player"]["hp"]
    assert guard_value(guard_match["player"]) >= 5


def test_strike_intent_increases_pressure_in_controlled_board():
    strike_match = resolve_one_round("Strike", "Focus", player_card="spark_runner")
    focus_match = resolve_one_round("Focus", "Focus", player_card="spark_runner")

    assert strike_match["opponent"]["hp"] < focus_match["opponent"]["hp"]


def test_focus_intent_builds_more_ambition_than_strike():
    focus_match = resolve_one_round("Focus", "Focus")
    strike_match = resolve_one_round("Strike", "Focus")

    assert focus_match["player"]["ambition"] > strike_match["player"]["ambition"]
