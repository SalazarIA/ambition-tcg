from copy import deepcopy

import pytest

from services.rebirth_engine import (
    RebirthError,
    compare_power,
    evolve_duplicate,
    next_turn,
    play_card,
    start_match,
)
from services.rebirth_state import public_state


def test_start_match_creates_valid_state_with_hands():
    match = start_match(seed="start")

    assert match["match_id"].startswith("rebirth-")
    assert match["architecture"] == "Ambitionz Rebirth"
    assert match["turn"] == 1
    assert match["phase"] == "choose"
    assert match["player"]["hp"] == 3
    assert match["bot"]["hp"] == 3
    assert len(match["player"]["hand"]) == 5
    assert len(match["bot"]["hand"]) == 5


def test_compare_power_returns_expected_winner():
    player = {"power": 5}
    bot = {"power": 3}

    assert compare_power(player, bot) == "player"
    assert compare_power(bot, player) == "bot"
    assert compare_power({"power": 4}, {"power": 4}) == "clash"


def test_play_card_resolves_turn_and_applies_life_damage():
    match = start_match(seed="damage")
    card = next(card for card in match["player"]["hand"] if card["id"] == "iron_beetle")

    play_card(match, card_instance_id=card["instance_id"])

    assert match["phase"] == "result"
    assert match["result"]["outcome"] in {"Victory", "Defeat", "Clash"}
    assert match["bot"]["hp"] == 2
    assert match["player"]["played_card"]["id"] == "iron_beetle"
    assert match["bot"]["played_card"] is not None


def test_equal_power_clash_causes_no_damage():
    match = start_match(seed="tie")
    player_card = next(card for card in match["player"]["hand"] if card["id"] == "spark_hare")

    match["bot"]["hand"] = [
        {
            "id": "mist_lynx",
            "name": "Mist Lynx",
            "family": "Mist",
            "tier": 1,
            "power": 4,
            "element": "Water",
            "evolution_id": None,
            "flavor": "Test card.",
            "instance_id": "bot-test-mist",
        }
    ]

    play_card(match, card_instance_id=player_card["instance_id"])

    assert match["result"]["outcome"] == "Clash"
    assert match["player"]["hp"] == 3
    assert match["bot"]["hp"] == 3


def test_evolution_by_duplicate_creates_stronger_card():
    match = start_match(seed="evolve")

    evolved = evolve_duplicate(match, "ember_cub")

    assert evolved["id"] == "ember_fang"
    assert evolved["name"] == "Ember Fang"
    assert evolved["power"] == 5
    assert evolved["tier"] == 2
    assert match["player"]["hand"][0]["id"] == "ember_fang"
    assert len([card for card in match["player"]["discard"] if card["id"] == "ember_cub"]) == 2


def test_evolution_requires_duplicate():
    match = start_match(seed="no-duplicate")

    with pytest.raises(RebirthError) as error:
        evolve_duplicate(match, "spark_hare")

    assert error.value.code == "no_evolution"

    match = start_match(seed="no-duplicate-2")
    first_ember = next(card for card in match["player"]["hand"] if card["id"] == "ember_cub")
    match["player"]["hand"] = [first_ember]

    with pytest.raises(RebirthError) as duplicate_error:
        evolve_duplicate(match, "ember_cub")

    assert duplicate_error.value.code == "duplicate_required"


def test_match_finishes_when_hp_reaches_zero():
    match = start_match(seed="finish")
    match["bot"]["hp"] = 1
    card = next(card for card in match["player"]["hand"] if card["id"] == "iron_beetle")

    play_card(match, card_instance_id=card["instance_id"])

    assert match["is_finished"] is True
    assert match["phase"] == "game_over"
    assert match["winner"] == "player"


def test_next_turn_resets_result_and_refills_hand():
    match = start_match(seed="next")
    original_card = deepcopy(match["player"]["hand"][0])

    play_card(match, card_instance_id=original_card["instance_id"])
    next_turn(match)

    assert match["turn"] == 2
    assert match["phase"] == "choose"
    assert match["result"] is None
    assert match["player"]["played_card"] is None
    assert len(match["player"]["hand"]) == 5
    assert original_card["id"] in {card["id"] for card in match["player"]["discard"]}


def test_public_state_exposes_player_hand_and_hides_bot_hand():
    match = start_match(seed="public")
    state = public_state(match)

    assert "hand" in state["player"]
    assert "hand_count" in state["bot"]
    assert "hand" not in state["bot"]
    assert state["available_evolutions"][0]["card_id"] == "ember_cub"
