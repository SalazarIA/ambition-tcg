from game.battle import clash_damage_floor, clash_net_damage_floor, duel_storm_damage, resolve_battle
from game.balance import CLASH_MIN_DAMAGE, CLASH_MIN_NET_DAMAGE, DUEL_STORM_DAMAGE, STARTING_HP


def make_player(name, monster_power, intent="Focus"):
    return {
        "sid": name.lower(),
        "user_id": name.lower(),
        "name": name,
        "hp": STARTING_HP,
        "deck": [{"id": f"{name}-draw", "name": "Reserve", "type": "Monster", "cost": 1}],
        "hand": [],
        "graveyard": [],
        "field_m": {
            "id": f"{name}-monster",
            "name": f"{name} Monster",
            "type": "Monster",
            "element": "Fire",
            "power": monster_power,
            "effect": "None",
            "cost": 1,
        },
        "field_st": None,
        "ready": True,
        "shield": 0,
        "energy": 2,
        "max_energy": 2,
        "ambition": 0,
        "wants_unleash": False,
        "ambition_unleashed": False,
        "overreach_count": 0,
        "intent": intent,
    }


def test_close_monster_clash_uses_minimum_tempo_damage():
    match = {
        "p1": make_player("Alice", 1100),
        "p2": make_player("Bob", 1000),
        "round": 1,
        "phase": "Set Phase",
        "resolving": False,
        "logs": [],
    }

    result = resolve_battle(match)

    assert result["winner"] is None
    assert match["p2"]["hp"] == STARTING_HP - CLASH_MIN_DAMAGE
    assert any("Duel pressure raised clash damage" in log for log in result["logs"])


def test_guard_cannot_reduce_a_won_clash_below_net_tempo_damage():
    match = {
        "p1": make_player("Alice", 1100),
        "p2": make_player("Bob", 1000, intent="Guard"),
        "round": 1,
        "phase": "Set Phase",
        "resolving": False,
        "logs": [],
    }

    result = resolve_battle(match)

    assert result["winner"] is None
    assert match["p2"]["hp"] == STARTING_HP - CLASH_MIN_NET_DAMAGE
    assert any("Duel pressure pushed final damage" in log for log in result["logs"])


def test_clash_damage_floor_scales_after_midgame():
    assert clash_damage_floor(1) == CLASH_MIN_DAMAGE
    assert clash_damage_floor(4) > CLASH_MIN_DAMAGE
    assert clash_damage_floor(20) == CLASH_MIN_DAMAGE + 250
    assert clash_net_damage_floor(1) == CLASH_MIN_NET_DAMAGE
    assert clash_net_damage_floor(20) == CLASH_MIN_NET_DAMAGE + 150


def test_late_duel_storm_adds_endgame_pressure_without_touching_early_rounds():
    match = {
        "p1": make_player("Alice", 0),
        "p2": make_player("Bob", 0),
        "round": 8,
        "phase": "Set Phase",
        "resolving": False,
        "logs": [],
    }
    match["p1"]["field_m"] = None
    match["p2"]["field_m"] = None

    result = resolve_battle(match)

    assert duel_storm_damage(7) == 0
    assert duel_storm_damage(8) == DUEL_STORM_DAMAGE
    assert result["winner"] is None
    assert match["p1"]["hp"] == STARTING_HP - DUEL_STORM_DAMAGE
    assert match["p2"]["hp"] == STARTING_HP - DUEL_STORM_DAMAGE
    assert any("Ambition Storm pressured the duel" in log for log in result["logs"])
