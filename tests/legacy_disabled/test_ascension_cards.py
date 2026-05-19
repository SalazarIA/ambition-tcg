from collections import Counter

from services.ascension_cards import (
    CARD_TYPES,
    build_ascension_starter_deck,
    get_ascension_catalog,
    get_card_by_id,
    migrate_legacy_card_to_ascension,
    validate_ascension_deck,
)


def test_catalog_has_required_card_types_and_original_names():
    catalog = get_ascension_catalog()
    types = {card["type"] for card in catalog}
    names = {card["name"] for card in catalog}

    assert set(CARD_TYPES) <= types
    assert "Ember Vowbound" in names
    assert "Glass Tyrant" in names
    assert "Debt of the Starless" in names
    assert "Last Crown Protocol" in names


def test_starter_deck_is_deterministic_and_validates():
    first = build_ascension_starter_deck(seed="rebirth")
    second = build_ascension_starter_deck(seed="rebirth")
    counts = Counter(card["type"] for card in first)
    result = validate_ascension_deck(first)

    assert [card["id"] for card in first] == [card["id"] for card in second]
    assert len(first) == 30
    assert result["valid"] is True
    assert counts["champion"] >= 10
    assert counts["technique"] >= 8
    assert counts["relic"] >= 4
    assert counts["scheme"] >= 4
    assert counts["ascension"] <= 2


def test_get_card_by_id_returns_defensive_copy():
    card = get_card_by_id("ember_vowbound")
    card["name"] = "Changed"

    assert get_card_by_id("ember_vowbound")["name"] == "Ember Vowbound"


def test_migrate_legacy_card_to_ascension_preserves_purpose_without_lanes():
    migrated = migrate_legacy_card_to_ascension({"id": "arena_brute", "name": "Arena Brute", "type": "Monster", "attack": 3})

    assert migrated["type"] == "champion"
    assert "summon" in migrated["modes"]
    assert "bind" in migrated["modes"]
    assert migrated["legacy"]["id"] == "arena_brute"
