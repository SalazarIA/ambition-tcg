from copy import deepcopy

from services.battle_engine_v2 import (
    CARD_CATALOG_V2,
    choose_intent,
    create_match,
    play_card,
    start_round,
)


def card(card_id):
    return deepcopy(CARD_CATALOG_V2[card_id])


def test_resolver_summons_creature_and_grants_ambition():
    match = create_match(seed=5101)
    start_round(match)
    match["player"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Strike")

    play_card(match, "player", card_id="spark_runner", lane="center")

    assert match["player"]["board"]["center"]["card_id"] == "spark_runner"
    assert match["player"]["ambition"] == 2
    assert any(event["type"] == "card_played" for event in match["combat_log"])


def test_resolver_applies_direct_hero_damage_with_strike_bonus():
    match = create_match(seed=5102)
    start_round(match)
    match["player"]["hand"] = [card("pressure_move")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Strike")

    play_card(match, "player", card_id="pressure_move", target="enemy_hero")

    assert match["opponent"]["hp"] == 25
    assert match["player"]["last_damage_dealt"] == 3
    event_types = {event["type"] for event in match["combat_log"]}
    assert {"card_played", "direct_attack", "hero_damage", "ambition_gain"}.issubset(event_types)


def test_resolver_boosts_guard_shield():
    match = create_match(seed=5103)
    start_round(match)
    match["player"]["hand"] = [card("hold_position")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Guard")

    play_card(match, "player", card_id="hold_position", target="self")

    assert match["player"]["shield"] == 7
    assert any(event["type"] == "shield_gain" and event.get("amount") == 7 for event in match["combat_log"])


def test_resolver_lane_target_damage_clears_dead_creature():
    match = create_match(seed=5104, opponent_is_bot=False)
    start_round(match)
    match["player"]["hand"] = [card("clean_hit")]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    choose_intent(match, "player", "Strike")
    choose_intent(match, "opponent", "Focus")
    play_card(match, "opponent", card_id="spark_runner", lane="left")

    play_card(match, "player", card_id="clean_hit", target="lane:left")

    assert match["opponent"]["board"]["left"] is None
    assert any(card.get("card_id") == "spark_runner" for card in match["opponent"]["discard"])
    assert any(event["type"] == "creature_damage" for event in match["combat_log"])


def test_spell_resolver_heals_player_with_real_spell_event():
    match = create_match(seed=5105, opponent_is_bot=False)
    start_round(match)
    heal_spell = {
        "id": "test_healing_rain",
        "name": "Healing Rain",
        "kind": "spell",
        "official_type": "Spell",
        "cost": 1,
        "heal": 5,
        "text": "Restore HP.",
    }
    match["player"]["hp"] = 20
    match["player"]["hand"] = [heal_spell]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Focus")

    play_card(match, "player", card_id="test_healing_rain", target="self")

    assert match["player"]["hp"] == 25
    assert any(event["type"] == "spell_heal" for event in match["combat_log"])


def test_spell_resolver_can_shield_ally_creature_target():
    match = create_match(seed=5106, opponent_is_bot=False)
    start_round(match)
    match["player"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Guard")
    play_card(match, "player", card_id="spark_runner", lane="left")

    shield_spell = {
        "id": "test_barrier",
        "name": "Lane Barrier",
        "kind": "spell",
        "official_type": "Spell",
        "cost": 1,
        "shield": 4,
        "text": "Shield an allied creature.",
    }
    match["player"]["played_card"] = None
    match["player"]["played_this_round"] = False
    match["player"]["hand"] = [shield_spell]
    match["player"]["energy"] = 10

    play_card(
        match,
        "player",
        card_id="test_barrier",
        target_type="creature",
        target_owner="self",
        target_lane="left",
    )

    assert match["player"]["board"]["left"]["shield"] == 6
    assert any(event["type"] == "shield_gain" and event.get("target_type") == "creature" for event in match["combat_log"])


def test_trap_resolver_triggers_and_consumes_on_enemy_attack():
    match = create_match(seed=5107, opponent_is_bot=False)
    start_round(match)
    counter_trap = {
        "id": "test_counter_trap",
        "name": "Counter Sigil",
        "kind": "trap",
        "official_type": "Trap",
        "cost": 1,
        "damage": 5,
        "shield": 0,
        "text": "Counter damage when the enemy attacks.",
    }
    match["player"]["hand"] = [counter_trap]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    choose_intent(match, "player", "Guard")
    choose_intent(match, "opponent", "Strike")
    play_card(match, "player", card_id="test_counter_trap", card_type="trap", target="self")
    play_card(match, "opponent", card_id="spark_runner", lane="left")

    match["player"]["ready"] = True
    match["opponent"]["ready"] = True
    from services.battle_engine_v2 import resolve_combat
    resolve_combat(match)

    assert match["player"]["prepared_traps"] == []
    assert any(card.get("id") == "test_counter_trap" for card in match["player"]["discard"])
    assert any(event["type"] == "trap_triggered" for event in match["combat_log"])
