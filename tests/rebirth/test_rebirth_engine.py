from copy import deepcopy

import pytest

from services.rebirth_engine import (
    RebirthError,
    compare_power,
    declare_attack,
    evolve_duplicate,
    evolve_bot_if_ready,
    next_turn,
    play_card,
    start_match,
)
from services.rebirth_cards import create_card_instance
from services.rebirth_state import public_state


def test_start_match_creates_valid_state_with_hands():
    match = start_match(seed="start")

    assert match["match_id"].startswith("rebirth-")
    assert match["architecture"] == "Ambitionz Rebirth"
    assert match["turn"] == 1
    assert match["phase"] == "choose"
    assert match["player"]["hp"] == 30
    assert match["bot"]["hp"] == 30
    assert match["player"]["max_hp"] == 30
    assert match["player"]["energy"] == 1
    assert match["player"]["max_energy"] == 1
    assert match["player"]["battlefield"] == []
    assert match["bot"]["battlefield"] == []
    assert match["player"]["hand"][0]["id"] == "card_001"
    assert len(match["player"]["hand"]) == 5
    assert len(match["bot"]["hand"]) == 5
    assert len(match["player"]["deck"]) == 25


def test_compare_power_returns_expected_winner():
    player = {"attack": 5}
    bot = {"attack": 3}

    assert compare_power(player, bot) == "player"
    assert compare_power(bot, player) == "bot"
    assert compare_power({"attack": 4}, {"attack": 4}) == "clash"


def test_play_card_summons_monster_to_persistent_battlefield():
    match = start_match(seed="summon")
    card = next(card for card in match["player"]["hand"] if card["id"] == "card_002")
    match["bot"]["hand"] = [create_card_instance("card_041", "bot", 1)]

    play_card(match, card_instance_id=card["instance_id"])

    assert match["phase"] == "choose"
    assert match["turn_phase"] == "MAIN_PHASE"
    assert match["result"]["outcome"] == "Summon"
    assert match["player"]["hp"] == 30
    assert match["bot"]["hp"] == 30
    assert match["player"]["energy"] == 0
    assert match["player"]["played_card"]["id"] == "card_002"
    assert match["player"]["battlefield"][0]["instance_id"] == card["instance_id"]
    assert match["player"]["battlefield"][0]["current_guard"] == card["guard"]
    assert match["bot"]["battlefield"][0]["id"] == "card_041"


def test_play_card_fills_slots_in_order_and_blocks_when_battlefield_full():
    """v54 restored 3 slots per side. Summoning fills 0,1,2; the 4th attempt
    raises battlefield_full and the hand keeps the card."""
    match = start_match(seed="summon-slot")
    match["bot"]["hand"] = []

    # First 3 monster cards from the starting hand — the seed yields
    # [card_001, card_001, card_002, card_021, card_041]; we take the first 3.
    cards = [card for card in match["player"]["hand"] if card.get("type") == "MONSTER"][:3]
    assert len(cards) == 3, "starting hand must have at least 3 monsters for this test"
    match["player"]["energy"] = 9

    for index, card in enumerate(cards):
        play_card(match, card_instance_id=card["instance_id"])
        assert match["player"]["battlefield"][index]["field_slot"] == index

    assert len(match["player"]["field"]) == 3
    assert [c["instance_id"] for c in match["player"]["field"]] == [c["instance_id"] for c in cards]

    fourth = create_card_instance("card_004", "player", 99)
    match["player"]["hand"] = [fourth]
    match["player"]["energy"] = 2

    with pytest.raises(RebirthError) as error:
        play_card(match, card_instance_id=fourth["instance_id"])

    assert error.value.code == "battlefield_full"
    assert match["player"]["hand"][0]["instance_id"] == fourth["instance_id"]


def test_equal_power_clash_causes_no_damage():
    match = start_match(seed="tie")
    player_card = next(card for card in match["player"]["hand"] if card["id"] == "card_002")

    match["bot"]["hand"] = [
        {
            "id": "test_equal",
            "name": "Equal Test",
            "type": "MONSTER",
            "card_type": "MONSTER",
            "family": "TEST",
            "role": "Beast",
            "tier": 1,
            "cost": 0,
            "attack": 5,
            "guard": 5,
            "power": 5,
            "element": "Shadow",
            "evolution_id": None,
            "ability_key": "test_card",
            "ability_name": "Test",
            "ability_text": "Test card.",
            "flavor": "Test card.",
            "art": "/static/assets/rebirth/cards/nightfang.svg",
            "instance_id": "bot-test-mist",
        }
    ]

    play_card(match, card_instance_id=player_card["instance_id"])
    declare_attack(
        match,
        attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    assert match["result"]["outcome"] == "Clash"
    assert match["player"]["hp"] == 30
    assert match["bot"]["hp"] == 30


def test_evolution_by_duplicate_creates_stronger_card():
    match = start_match(seed="evolve")

    evolved = evolve_duplicate(match, "card_001")

    assert evolved["id"] == "card_011"
    assert evolved["attack"] > 4
    assert evolved["tier"] == 2
    assert match["player"]["hand"][0]["id"] == "card_011"
    assert len([card for card in match["player"]["discard"] if card["id"] == "card_001"]) == 2


def test_evolution_requires_duplicate():
    match = start_match(seed="no-duplicate")

    with pytest.raises(RebirthError) as error:
        evolve_duplicate(match, "card_002")

    assert error.value.code == "duplicate_not_available"

    match = start_match(seed="no-duplicate-2")
    first_dreadclaw = next(card for card in match["player"]["hand"] if card["id"] == "card_001")
    match["player"]["hand"] = [first_dreadclaw]

    with pytest.raises(RebirthError) as duplicate_error:
        evolve_duplicate(match, "card_001")

    assert duplicate_error.value.code == "duplicate_not_available"


def test_match_finishes_when_hp_reaches_zero():
    match = start_match(seed="finish")
    match["bot"]["hp"] = 3
    card = next(card for card in match["player"]["hand"] if card["id"] == "card_002")
    match["bot"]["hand"] = []

    play_card(match, card_instance_id=card["instance_id"])
    declare_attack(match, attacker_instance_id=card["instance_id"])

    assert match["is_finished"] is True
    assert match["phase"] == "finished"
    assert match["winner"] == "player"


def test_match_finishes_by_hp_when_future_cards_are_exhausted():
    match = start_match(seed="exhaustion", bot_profile_id="defensive")
    match["player"]["hp"] = 21
    match["bot"]["hp"] = 7
    match["player"]["deck"] = []
    match["bot"]["deck"] = []
    match["player"]["hand"] = [create_card_instance("card_002", "player", 1)]
    match["bot"]["hand"] = []
    card_instance_id = match["player"]["hand"][0]["instance_id"]

    play_card(match, card_instance_id=card_instance_id)

    assert match["is_finished"] is True
    assert match["phase"] == "finished"
    assert match["winner"] == "player"
    assert "exhaustion" in match["result"]["message"]


def test_bot_evolves_duplicate_before_answering():
    match = start_match(seed="bot-evolve", bot_profile_id="aggressive")
    match["bot"]["hand"] = [
        create_card_instance("card_001", "bot", 1),
        create_card_instance("card_001", "bot", 2),
        create_card_instance("card_041", "bot", 3),
    ]

    evolved = evolve_bot_if_ready(match)

    assert evolved["id"] == "card_011"
    assert match["bot"]["hand"][0]["id"] == "card_011"
    assert len([card for card in match["bot"]["discard"] if card["id"] == "card_001"]) == 2
    assert "Bot evolved" in match["log"][-1]


def test_spell_resolves_immediately_through_effect_stack_and_discards():
    match = start_match(seed="spell")
    match["player"]["energy"] = 2
    match["player"]["max_energy"] = 2
    match["player"]["hand"] = [create_card_instance("card_081", "player", 1)]
    match["player"]["deck"] = [
        create_card_instance("card_003", "player", 2),
        create_card_instance("card_004", "player", 3),
    ]

    play_card(match, card_instance_id=match["player"]["hand"][0]["instance_id"])

    assert match["phase"] == "choose"
    assert match["turn_phase"] == "MAIN_PHASE"
    assert match["result"]["outcome"] == "Spell"
    assert [card["id"] for card in match["player"]["hand"]] == ["card_003", "card_004"]
    assert match["player"]["discard"][0]["id"] == "card_081"


def test_trap_arms_face_down_and_triggers_in_combat():
    match = start_match(seed="trap", bot_profile_id="defensive")
    match["player"]["energy"] = 2
    match["player"]["max_energy"] = 2
    match["player"]["hand"] = [create_card_instance("card_091", "player", 1)]
    play_card(match, card_instance_id=match["player"]["hand"][0]["instance_id"])

    assert match["phase"] == "choose"
    assert match["player"]["traps"][0]["face_down"] is True
    assert match["player"]["traps"][0]["armed"] is True

    match["player"]["hand"] = [create_card_instance("card_002", "player", 2)]
    match["bot"]["hand"] = [create_card_instance("card_041", "bot", 1)]
    match["player"]["energy"] = 1
    match["bot"]["energy"] = 1
    play_card(match, card_instance_id=match["player"]["hand"][0]["instance_id"])
    declare_attack(
        match,
        attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    assert match["phase"] in {"result", "finished"}
    assert not match["player"]["traps"]
    assert any(card["id"] == "card_091" and card["revealed"] for card in match["player"]["discard"])
    assert any("negates" in event for event in match["result"]["ability_events"])


def test_defeated_monster_leaves_battlefield_and_goes_to_discard():
    """Regression: destroyed monsters used to stay on the field forever because
    field_slots() rebuilt from side["battlefield"], which was never cleared.
    """
    match = start_match(seed="defeat-removes-card")
    attacker = next(card for card in match["player"]["hand"] if card["id"] == "card_002")
    weak_defender = create_card_instance("card_041", "bot", 1)
    weak_defender["guard"] = 1
    weak_defender["current_guard"] = 1
    defender_instance_id = weak_defender["instance_id"]
    match["bot"]["hand"] = [weak_defender]

    play_card(match, card_instance_id=attacker["instance_id"])
    declare_attack(
        match,
        attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    assert match["bot"]["battlefield"] == []
    assert match["bot"]["field"] == [None, None, None]
    assert any(card["instance_id"] == defender_instance_id for card in match["bot"]["discard"])

    next_turn(match)
    surviving_ids = {card.get("instance_id") for card in match["bot"]["battlefield"]}
    assert defender_instance_id not in surviving_ids, "defeated monster must not resurrect after next_turn"


def test_next_turn_resets_result_and_refills_hand():
    match = start_match(seed="next")
    original_card = deepcopy(match["player"]["hand"][0])

    play_card(match, card_instance_id=original_card["instance_id"])
    next_turn(match)

    assert match["turn"] == 2
    assert match["phase"] == "choose"
    assert match["result"] is None
    assert match["player"]["played_card"] is None
    assert match["player"]["energy"] == 2
    assert match["player"]["max_energy"] == 2
    assert len(match["player"]["hand"]) == 5
    assert original_card["id"] in {card["id"] for card in match["player"]["battlefield"]}
    assert original_card["id"] not in {card["id"] for card in match["player"]["discard"]}


def test_next_turn_rejects_invalid_phase():
    match = start_match(seed="next-invalid")
    match["phase"] = "combat"

    with pytest.raises(RebirthError) as error:
        next_turn(match)

    assert error.value.code == "invalid_phase"


def test_public_state_exposes_player_hand_and_hides_bot_hand():
    match = start_match(seed="public")
    state = public_state(match)

    assert "hand" in state["player"]
    assert "hand_count" in state["bot"]
    assert "hand" not in state["bot"]
    assert state["player"]["max_hp"] == 30
    assert state["player"]["battlefield"] == []
    assert state["bot"]["battlefield"] == []
    assert state["player_field"] == [None, None, None]
    assert state["bot_field"] == [None, None, None]
    assert state["available_evolutions"][0]["card_id"] == "card_001"

    for field in [
        "match_id",
        "phase",
        "turn",
        "player",
        "bot",
        "bot_profile",
        "available_evolutions",
        "last_clash",
        "result",
        "winner",
        "log",
    ]:
        assert field in state
