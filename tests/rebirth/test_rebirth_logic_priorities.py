from copy import deepcopy

from services.rebirth_bot import (
    MCTSAgent,
    attack_utility_projection,
    difficulty_payload,
    estimated_attack,
)
from services.rebirth_cards import create_card_instance, get_card
from services.rebirth_engine import declare_attack, start_match
from services.rebirth_keywords import (
    KEYWORD_SUNDER,
    SUNDER_ATTACK_BONUS,
    sunder_active,
)
from services.rebirth_state import compact_battlefield, public_state


def _unit(instance_id, *, attack, guard, family="FIRE", keywords=None, slot=0):
    return {
        "id": instance_id,
        "instance_id": instance_id,
        "name": instance_id,
        "type": "MONSTER",
        "card_type": "MONSTER",
        "family": family,
        "attack": attack,
        "power": attack,
        "guard": guard,
        "current_guard": guard,
        "max_guard": guard,
        "tier": 2,
        "keywords": list(keywords or []),
        "field_slot": slot,
        "slot": slot + 1,
        "exhausted": False,
        "has_attacked": False,
        "has_acted": False,
        "just_summoned": False,
    }


def test_difficulty_is_separate_from_personality_and_public():
    match = start_match(
        seed="difficulty-contract",
        bot_profile_id="aggressive",
        bot_difficulty_id="hard",
    )
    state = public_state(match)
    assert state["bot_profile"]["id"] == "aggressive"
    assert state["bot_difficulty"]["id"] == "hard"
    assert difficulty_payload("easy")["depth"] < difficulty_payload("hard")["depth"]


def test_shared_attack_math_includes_board_synergy_for_bot_projection():
    anchor = _unit("anchor", attack=4, guard=3, family="EARTH")
    anchor["synergy"] = {
        "condition": "total_guard",
        "value": 6,
        "effect": {"attack": 2},
    }
    ally = _unit("ally", attack=2, guard=4, family="EARTH", slot=1)
    target = _unit("target", attack=3, guard=3)
    without_board = estimated_attack(anchor, target, owner_field=[anchor])
    with_board = estimated_attack(anchor, target, owner_field=[anchor, ally])
    assert with_board == without_board + 2


def test_beam_search_returns_real_multi_attack_principal_variation():
    bot = [
        _unit("a", attack=7, guard=5, slot=0),
        _unit("b", attack=6, guard=5, slot=1),
    ]
    player = [
        _unit("x", attack=2, guard=2, slot=0),
        _unit("y", attack=2, guard=2, slot=1),
    ]
    decision = MCTSAgent(difficulty_id="hard").choose_attack(
        bot,
        player,
        player_hp=30,
        turn=5,
        profile_id="aggressive",
        match_id="beam-sequence",
    )
    assert decision is not None
    assert decision["search_depth"] >= 2
    assert len(decision["principal_variation"]) >= 2
    assert decision["legal_action_count"] >= 2


def test_sunder_requires_mixed_board_and_wall_target():
    attacker = _unit("sunder", attack=6, guard=4, family="SHADOW", keywords=[KEYWORD_SUNDER])
    shadow_ally = _unit("shadow", attack=3, guard=3, family="SHADOW", slot=1)
    water_ally = _unit("water", attack=3, guard=3, family="WATER", slot=1)
    wall = _unit("wall", attack=2, guard=7, family="EARTH", keywords=["TAUNT", "SHIELD"])
    plain = _unit("plain", attack=2, guard=7, family="EARTH")

    assert not sunder_active(attacker, [attacker, shadow_ally], wall)
    assert not sunder_active(attacker, [attacker, water_ally], plain)
    assert sunder_active(attacker, [attacker, water_ally], wall)
    assert (
        estimated_attack(attacker, wall, owner_field=[attacker, water_ally])
        == estimated_attack(attacker, wall, owner_field=[attacker]) + SUNDER_ATTACK_BONUS
    )


def _script_sunder_match(*, mixed_board):
    match = start_match(seed=f"sunder-{mixed_board}", bot_profile_id="defensive", shuffle=False)
    attacker = create_card_instance("card_073", "player", 900)
    attacker["attack"] = attacker["power"] = 10
    attacker["current_guard"] = attacker["guard"] = attacker["max_guard"] = 8
    attacker["field_slot"] = 0
    attacker["slot"] = 1
    attacker["just_summoned"] = False
    attacker["exhausted"] = attacker["has_attacked"] = attacker["has_acted"] = False
    ally = create_card_instance("card_021" if mixed_board else "card_071", "player", 901)
    ally["field_slot"] = 1
    ally["slot"] = 2
    ally["just_summoned"] = False
    match["player"]["field"] = [attacker, ally, None]
    match["player"]["battlefield"] = [attacker, ally]

    wall = create_card_instance("card_051", "bot", 902)
    wall["attack"] = wall["power"] = 1
    wall["guard"] = wall["max_guard"] = wall["current_guard"] = 8
    wall["field_slot"] = 0
    wall["slot"] = 1
    wall["shield_consumed"] = False
    match["bot"]["field"] = [wall, None, None]
    match["bot"]["battlefield"] = [wall]
    return match, attacker, wall


def test_sunder_breaks_shield_and_applies_damage_in_same_combat():
    match, attacker, wall = _script_sunder_match(mixed_board=True)
    before = wall["current_guard"]
    result = declare_attack(
        match,
        attacker_instance_id=attacker["instance_id"],
        target_instance_id=wall["instance_id"],
    )
    survivor = next(
        (card for card in compact_battlefield(match["bot"]) if card["instance_id"] == wall["instance_id"]),
        None,
    )
    assert any(event["event_type"] == "SHIELD_KEYWORD_BROKEN" for event in match["events"])
    assert "Ruptura" in result["message"]
    assert survivor is None or survivor["current_guard"] < before


def test_without_mixed_board_shield_still_absorbs():
    match, attacker, wall = _script_sunder_match(mixed_board=False)
    before = wall["current_guard"]
    declare_attack(
        match,
        attacker_instance_id=attacker["instance_id"],
        target_instance_id=wall["instance_id"],
    )
    survivor = next(
        card for card in compact_battlefield(match["bot"]) if card["instance_id"] == wall["instance_id"]
    )
    assert survivor["current_guard"] == before
    assert any(event["event_type"] == "SHIELD_KEYWORD_ABSORBED" for event in match["events"])


def test_bot_projection_values_sunder_over_plain_shield_hit():
    attacker = _unit("sunder", attack=7, guard=5, family="SHADOW", keywords=[KEYWORD_SUNDER])
    ally = _unit("water", attack=2, guard=3, family="WATER", slot=1)
    wall = _unit("wall", attack=2, guard=5, family="EARTH", keywords=["TAUNT", "SHIELD"])
    with_sunder = attack_utility_projection(
        attacker,
        wall,
        bot_battlefield=[attacker, ally],
        player_battlefield=[wall],
    )
    without_mixed = attack_utility_projection(
        deepcopy(attacker),
        deepcopy(wall),
        bot_battlefield=[deepcopy(attacker)],
        player_battlefield=[deepcopy(wall)],
    )
    assert with_sunder["shield_broken_by_sunder"] is True
    assert with_sunder["utility"] > without_mixed["utility"]


def test_catalog_midrange_capstones_carry_sunder():
    assert KEYWORD_SUNDER in get_card("card_073")["keywords"]
    assert KEYWORD_SUNDER in get_card("card_077")["keywords"]
    assert KEYWORD_SUNDER in get_card("card_079")["keywords"]
