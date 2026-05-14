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
