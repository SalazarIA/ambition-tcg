from copy import deepcopy

import pytest

from services.rebirth_bot import attack_utility_projection, search_attack_sequences
from services.rebirth_engine import compare_clash, resolve_turn, start_match


def _unit(instance_id, *, attack, guard, keywords=None, synergy=None, side="bot", slot=0):
    return {
        "id": instance_id,
        "instance_id": instance_id,
        "name": instance_id,
        "type": "MONSTER",
        "card_type": "MONSTER",
        "family": "SHADOW" if side == "bot" else "EARTH",
        "attack": attack,
        "power": attack,
        "guard": guard,
        "current_guard": guard,
        "max_guard": guard,
        "tier": 1,
        "keywords": list(keywords or []),
        "synergy": deepcopy(synergy),
        "owner_side": side,
        "field_slot": slot,
        "slot": slot + 1,
        "exhausted": False,
        "has_attacked": False,
        "has_acted": False,
        "just_summoned": False,
        "statuses": {},
    }


def _combat_match(player_card, bot_card, *, player_hp=30, bot_hp=30):
    match = start_match(seed=f"projection-{player_card['id']}-{bot_card['id']}", shuffle=False)
    match["player"]["hp"] = player_hp
    match["player"]["max_hp"] = max(player_hp, int(match["player"].get("max_hp", 30) or 30))
    match["bot"]["hp"] = bot_hp
    match["bot"]["max_hp"] = max(bot_hp, int(match["bot"].get("max_hp", 30) or 30))
    match["player"]["field"] = [player_card, None, None]
    match["player"]["battlefield"] = [player_card]
    match["bot"]["field"] = [bot_card, None, None]
    match["bot"]["battlefield"] = [bot_card]
    return match


def test_search_uses_actual_bot_hp_for_low_hp_synergy_engine_parity():
    low_hp_synergy = {
        "condition": "low_hp",
        "value": 15,
        "effect": {"attack": 2},
    }
    attacker = _unit("bot-low-hp", attack=4, guard=6, synergy=low_hp_synergy)
    target = _unit("player-target", attack=5, guard=3, side="player")

    low_hp_rows = search_attack_sequences(
        [attacker],
        [target],
        bot_hp=10,
        player_hp=30,
        depth=1,
        budget=4,
    )
    full_hp_rows = search_attack_sequences(
        [attacker],
        [target],
        bot_hp=30,
        player_hp=30,
        depth=1,
        budget=4,
    )

    match = _combat_match(deepcopy(target), deepcopy(attacker), bot_hp=10)
    engine_winner, clash = compare_clash(
        match,
        match["player"]["battlefield"][0],
        match["bot"]["battlefield"][0],
    )

    assert engine_winner == "bot"
    assert clash["bot_attack"] == 6
    assert low_hp_rows[0]["outcome"] == "win"
    assert full_hp_rows[0]["outcome"] == "loss"


@pytest.mark.parametrize(
    ("keywords", "expected_hero_damage"),
    [
        ([], 2),
        (["PIERCE"], 5),
    ],
)
def test_field_overflow_projection_matches_engine_and_marks_lethal(keywords, expected_hero_damage):
    attacker = _unit("bot-overflow", attack=8, guard=6, keywords=keywords)
    target = _unit("player-blocker", attack=1, guard=2, side="player")

    projection = attack_utility_projection(
        attacker,
        target,
        bot_battlefield=[attacker],
        player_battlefield=[target],
        bot_hp=11,
        player_hp=expected_hero_damage,
        turn=4,
    )

    match = _combat_match(
        deepcopy(target),
        deepcopy(attacker),
        player_hp=expected_hero_damage,
        bot_hp=11,
    )
    result = resolve_turn(
        match,
        match["player"]["battlefield"][0],
        match["bot"]["battlefield"][0],
        persistent_field=True,
        attacking_side="bot",
    )

    assert result["hero_damage"]["player"] == expected_hero_damage
    assert projection["hero_damage"] == result["hero_damage"]
    assert projection["player_hp_after"] == match["player"]["hp"] == 0
    assert projection["lethal_window"] is True
    assert match["winner"] == "bot"


def test_losing_projection_propagates_pierce_to_bot_hp_and_rejects_self_lethal():
    attacker = _unit("bot-loser", attack=1, guard=2)
    target = _unit(
        "player-piercer",
        attack=8,
        guard=6,
        keywords=["PIERCE"],
        side="player",
    )

    projection = attack_utility_projection(
        attacker,
        target,
        bot_battlefield=[attacker],
        player_battlefield=[target],
        bot_hp=5,
        player_hp=30,
        turn=4,
    )

    match = _combat_match(deepcopy(target), deepcopy(attacker), bot_hp=5)
    result = resolve_turn(
        match,
        match["player"]["battlefield"][0],
        match["bot"]["battlefield"][0],
        persistent_field=True,
        attacking_side="bot",
    )

    assert result["hero_damage"] == {"player": 0, "bot": 5}
    assert projection["hero_damage"] == result["hero_damage"]
    assert projection["bot_hp_after"] == match["bot"]["hp"] == 0
    assert projection["allowed"] is False
    assert projection["reason"] == "avoid_self_lethal"
    assert match["winner"] == "player"
