from collections import Counter

from services.rebirth_cards import (
    BASE_MONSTERS,
    BOT_DECK,
    CARD_BY_ID,
    CARD_CATALOG,
    PLAYER_DECK,
    SPELL_CARDS,
    TRAP_CARDS,
    create_card_instance,
    validate_deck_distribution,
)
from services.rebirth_engine import ENGINE_ABILITY_KEYS, resolve_turn, start_match


def match_with_cards(player_card_id, bot_card_id, *, turn=1, player_wounded=False, bot_wounded=False):
    match = start_match(seed=f"{player_card_id}-{bot_card_id}-{turn}")
    match["turn"] = turn
    match["player"]["hand"] = []
    match["bot"]["hand"] = []
    match["player"]["wounded"] = player_wounded
    match["bot"]["wounded"] = bot_wounded
    return match, create_card_instance(player_card_id, "player", 1), create_card_instance(bot_card_id, "bot", 1)


def test_rebirth_catalog_has_100_cards_default_art_and_engine_abilities():
    card_ids = [card["id"] for card in CARD_CATALOG]
    art_paths = [card["art"] for card in CARD_CATALOG]

    assert card_ids == [f"card_{index:03d}" for index in range(1, 101)]
    assert len(art_paths) == len(set(art_paths)) == 100

    families = Counter(card["family"] for card in CARD_CATALOG)
    assert {family: families[family] for family in ("FIRE", "WATER", "EARTH", "SHADOW")} == {
        "FIRE": 20,
        "WATER": 20,
        "EARTH": 20,
        "SHADOW": 20,
    }
    assert len(SPELL_CARDS) == 10
    assert len(TRAP_CARDS) == 10

    for card in CARD_CATALOG:
        assert card["ability_key"] in ENGINE_ABILITY_KEYS
        assert card["ability_name"]
        assert card["ability_text"]
        assert card["art"] == f"static/img/cards/{card['id']}.png"
        assert card["type"] in {"MONSTER", "SPELL", "TRAP"}
        assert card["card_type"] == card["type"]


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


def test_default_starter_decks_are_30_card_tcg_distributions():
    assert validate_deck_distribution(list(PLAYER_DECK)) == {"MONSTER": 20, "SPELL": 5, "TRAP": 5}
    assert validate_deck_distribution(list(BOT_DECK)) == {"MONSTER": 20, "SPELL": 5, "TRAP": 5}


def test_family_abilities_have_visible_combat_effects():
    match, player_card, bot_card = match_with_cards("card_002", "card_021")
    result = resolve_turn(match, player_card, bot_card)
    assert result["outcome"] == "Victory"
    assert "burn" in result["message"].lower()
    assert match["bot"]["statuses"]["burn"]["turns"] == 2

    match, player_card, bot_card = match_with_cards("card_045", "card_021")
    result = resolve_turn(match, player_card, bot_card)
    assert result["outcome"] == "Victory"
    assert "shield" in result["message"].lower()
    assert match["player"]["statuses"]["shield"]["potency"] == 2

    match, player_card, bot_card = match_with_cards("card_063", "card_022", bot_wounded=True)
    result = resolve_turn(match, player_card, bot_card)
    assert result["outcome"] == "Victory"
    assert result["effective_attack"] == {"player": 5, "bot": 5}
    assert "cut through the tie" in result["message"]

    match, player_card, bot_card = match_with_cards("card_071", "card_021")
    match["player"]["hp"] = 20
    result = resolve_turn(match, player_card, bot_card)
    assert result["outcome"] == "Victory"
    assert "heals 2 HP" in result["message"]
    assert match["player"]["hp"] == 22
