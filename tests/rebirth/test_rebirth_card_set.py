import json
from pathlib import Path

from services.rebirth_art import REBIRTH_ART_VERSION, art_profile
from services.rebirth_cards import BASE_MONSTERS, BOT_DECK, CARD_BY_ID, CARD_CATALOG, PLAYER_DECK, create_card_instance
from services.rebirth_engine import ENGINE_ABILITY_KEYS, resolve_turn, start_match


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def match_with_cards(player_card_id, bot_card_id, *, turn=1, player_wounded=False, bot_wounded=False):
    match = start_match(seed=f"{player_card_id}-{bot_card_id}-{turn}")
    match["turn"] = turn
    match["player"]["hand"] = []
    match["bot"]["hand"] = []
    match["player"]["wounded"] = player_wounded
    match["bot"]["wounded"] = bot_wounded
    return match, create_card_instance(player_card_id, "player", 1), create_card_instance(bot_card_id, "bot", 1)


def test_rebirth_card_catalog_has_final_art_and_engine_abilities():
    manifest = json.loads((PROJECT_ROOT / "static/assets/rebirth/manifest.json").read_text(encoding="utf-8"))
    card_ids = [card["id"] for card in CARD_CATALOG]
    art_paths = [card["art"] for card in CARD_CATALOG]

    assert manifest["version"] == REBIRTH_ART_VERSION == "rebirth-021"
    assert len(card_ids) == len(set(card_ids))
    assert len(art_paths) == len(set(art_paths))
    assert set(card_ids) == set(manifest["cards"])

    for card in CARD_CATALOG:
        profile = art_profile(card["id"])
        path = PROJECT_ROOT / card["art"].lstrip("/")

        assert card["ability_key"] in ENGINE_ABILITY_KEYS
        assert card["ability_name"]
        assert card["ability_text"]
        assert card["art"] == profile["path"] == manifest["cards"][card["id"]]
        assert card["art"].endswith("-art.png")
        assert path.exists()
        assert card["art_status"] != "placeholder"


def test_rebirth_evolutions_are_tier_two_and_not_in_default_decks():
    starter_ids = set(PLAYER_DECK + BOT_DECK)
    for card in BASE_MONSTERS:
        evolution_id = card.get("evolution_id")
        if not evolution_id:
            continue

        evolved = CARD_BY_ID[evolution_id]
        assert evolved["family"] == card["family"]
        assert int(evolved["tier"]) > int(card["tier"])
        assert evolved["attack"] > card["attack"]
        assert evolution_id not in starter_ids


def test_dreadclaw_and_dreadmaw_reward_wounded_pressure():
    match, player_card, bot_card = match_with_cards("dreadclaw", "voidstalker", turn=3, bot_wounded=True)
    result = resolve_turn(match, player_card, bot_card)

    assert result["damage"]["bot"] == 7
    assert "found the wound" in result["message"]

    match, player_card, bot_card = match_with_cards("dreadmaw", "voidstalker", turn=3, bot_wounded=True)
    result = resolve_turn(match, player_card, bot_card)

    assert result["damage"]["bot"] == 11
    assert "old wound" in result["message"]


def test_guardian_cards_reduce_incoming_damage():
    match, player_card, bot_card = match_with_cards("embermaw", "stoneshell")
    result = resolve_turn(match, player_card, bot_card)

    assert result["damage"]["bot"] == 4
    assert "Molten Bite" in result["message"]
    assert "reduced incoming damage" in result["message"]

    match, player_card, bot_card = match_with_cards("embermaw_alpha", "ironbulwark")
    result = resolve_turn(match, player_card, bot_card)

    assert result["damage"]["bot"] == 5
    assert "Inferno Bite" in result["message"]
    assert "reduced incoming damage" in result["message"]


def test_shadow_cards_break_ties_against_wounded_targets():
    match, player_card, bot_card = match_with_cards("shadewisp", "ironbastion", bot_wounded=True)
    result = resolve_turn(match, player_card, bot_card)

    assert result["outcome"] == "Victory"
    assert result["effective_attack"] == {"player": 3, "bot": 3}
    assert "cut through the tie" in result["message"]

    match, player_card, bot_card = match_with_cards("nightfang", "dreadclaw", bot_wounded=True)
    result = resolve_turn(match, player_card, bot_card)

    assert result["outcome"] == "Victory"
    assert "marked the target" in result["message"]


def test_air_fire_void_abilities_have_visible_effects():
    match, player_card, bot_card = match_with_cards("skywarden", "shadewisp")
    result = resolve_turn(match, player_card, bot_card)
    assert result["effective_attack"]["player"] == 5
    assert "High Guard" in result["message"]

    match, player_card, bot_card = match_with_cards("stormwarden", "voidstalker")
    result = resolve_turn(match, player_card, bot_card)
    assert result["damage"]["bot"] == 8
    assert "low guard" in result["message"]

    match, player_card, bot_card = match_with_cards("voidstalker", "dreadclaw", turn=1)
    result = resolve_turn(match, player_card, bot_card)
    assert result["effective_attack"]["player"] == 6
    assert "Silent Pursuit" in result["message"]
