"""Catalog coverage matrix — every active Rebirth card individually verified.

Why this file exists:
    `test_rebirth_card_set.py` already asserts the aggregate shape (100 base ids
    plus deterministic legendary contracts,
    family counts, deck distribution). What it does NOT guarantee is that each
    specific card produces a consistent payload, derives a valid cost, and
    exposes an ability_key that the engine can route. If a refactor of
    `_monster_cost` or the family-config tables silently breaks a single card,
    the aggregate test stays green while the broken card ships.

    Parametrizing per card_id gives one failed pytest line per broken card —
    `test_card_payload_shape[card_037]` — instead of one opaque aggregate
    failure. Cheap to run (~500 cases, all in-memory, no I/O).

Targets:
    - services.rebirth_cards._monster_cost: pure function, must not raise
    - services.rebirth_cards.create_card_instance: must produce a usable instance
    - services.rebirth_cards.CARD_BY_ID: ability_key must be in the engine's
      registered set ENGINE_ABILITY_KEYS
"""
from __future__ import annotations

import pytest

from services.rebirth_cards import (
    CARD_BY_ID,
    CARD_CATALOG,
    _monster_cost,
    create_card_instance,
    get_card,
)
from services.rebirth_engine import ENGINE_ABILITY_KEYS

ALL_CARD_IDS = [card["id"] for card in CARD_CATALOG]
MONSTER_IDS = [card["id"] for card in CARD_CATALOG if card["type"] == "MONSTER"]
SPELL_IDS = [card["id"] for card in CARD_CATALOG if card["type"] == "SPELL"]
TRAP_IDS = [card["id"] for card in CARD_CATALOG if card["type"] == "TRAP"]

# Guard: the matrix is meaningless if the catalog size changes silently.
assert len(ALL_CARD_IDS) == 103, "Catalog must contain exactly 103 cards"
assert len(MONSTER_IDS) == 83, "Catalog must contain exactly 83 monsters"
assert len(SPELL_IDS) == 10, "Catalog must contain exactly 10 spells"
assert len(TRAP_IDS) == 10, "Catalog must contain exactly 10 traps"


pytestmark = pytest.mark.catalog


@pytest.mark.parametrize("card_id", ALL_CARD_IDS)
def test_card_payload_shape(card_id):
    """Every card exposes the canonical Rebirth payload keys with valid types."""
    card = CARD_BY_ID[card_id]

    # Identity
    assert card["id"] == card_id
    is_base_id = card_id.startswith("card_") and card_id[5:].isdigit()
    assert is_base_id or card_id.startswith("legend_")
    if is_base_id:
        assert 1 <= int(card_id[5:]) <= 100

    # Type classification
    assert card["type"] in {"MONSTER", "SPELL", "TRAP"}
    assert card["card_type"] == card["type"], "type and card_type must match"

    # Rarity is part of the gacha contract
    assert card["rarity"] in {"COMMON", "UNCOMMON", "LEGENDARY"}

    # Cost must be a positive int the energy ramp can ever afford (max 10).
    assert isinstance(card["cost"], int)
    assert 1 <= card["cost"] <= 10

    # Art path is deterministic and optimized for the browser.
    if is_base_id:
        assert card["art"] == f"static/img/cards/baralho/{int(card_id.split('_')[-1])}.webp"
        assert card["art_status"] == "optimized_webp_path"
    else:
        assert card["art"].startswith("/static/assets/rebirth/cards/")
        assert card["art_status"] == "rebirth_legendary_contract"

    # Ability metadata must be populated (engine reads ability_key, UI reads name/text)
    assert isinstance(card["ability_key"], str) and card["ability_key"], "ability_key must be non-empty"
    assert card["ability_name"], "ability_name must be non-empty for UI"
    assert card["ability_text"], "ability_text must be non-empty for UI"


@pytest.mark.parametrize("card_id", ALL_CARD_IDS)
def test_ability_key_resolves_in_engine(card_id):
    """Every card's ability_key must be a key the engine knows how to dispatch.

    This is the trap the briefing called out: a card refers to an ability_key
    that the engine doesn't handle → silent no-op in combat.
    """
    card = CARD_BY_ID[card_id]
    assert card["ability_key"] in ENGINE_ABILITY_KEYS, (
        f"{card_id} ability_key {card['ability_key']!r} is not registered in the engine"
    )


@pytest.mark.parametrize("card_id", MONSTER_IDS)
def test_monster_cost_matches_curve(card_id):
    """Monster cost must equal _monster_cost(attack, guard, is_evolved).

    Catches drift between the catalog generator and the cost formula — e.g.
    if someone edits the curve in `_monster_card` but forgets to update
    `_monster_cost`, or vice versa.
    """
    card = CARD_BY_ID[card_id]
    assert card["attack"] == card["power"], "attack and power must be aliases"
    if card["rarity"] == "LEGENDARY":
        assert 1 <= card["cost"] <= 10
        return
    expected = _monster_cost(card["attack"], card["guard"], int(card["tier"]) > 1)
    assert card["cost"] == expected, (
        f"{card_id}: catalog cost {card['cost']} differs from _monster_cost-derived {expected}"
    )


@pytest.mark.parametrize("card_id", MONSTER_IDS)
def test_monster_attack_and_guard_are_positive_ints(card_id):
    """Defends against NoneType / float / negative ramps in the stat curves."""
    card = CARD_BY_ID[card_id]
    assert isinstance(card["attack"], int) and card["attack"] > 0
    assert isinstance(card["guard"], int) and card["guard"] >= 0


@pytest.mark.parametrize("card_id", ALL_CARD_IDS)
def test_create_card_instance_does_not_raise(card_id):
    """Every card must be instantiable for both sides — defends combat setup."""
    for owner in ("player", "bot"):
        instance = create_card_instance(card_id, owner, 1)
        assert instance["id"] == card_id
        assert instance["owner"] == owner
        assert instance["instance_id"].startswith(f"{owner}-01-{card_id}")
        assert instance["status_effects"] == []


@pytest.mark.parametrize("card_id", ALL_CARD_IDS)
def test_get_card_returns_deep_copy(card_id):
    """get_card must return an isolated copy — mutating the result must not
    poison the global catalog. Crucial for the engine which mutates instances."""
    a = get_card(card_id)
    a["ability_key"] = "MUTATED"
    a["attack"] = 999
    b = get_card(card_id)
    assert b["ability_key"] != "MUTATED"
    if "attack" in b:
        assert b["attack"] != 999


# -- Type-segregated invariants ---------------------------------------------

@pytest.mark.parametrize("card_id", MONSTER_IDS)
def test_monster_has_family_and_element(card_id):
    card = CARD_BY_ID[card_id]
    assert card["family"] in {"FIRE", "WATER", "EARTH", "SHADOW"}
    assert card["element"], "monsters must carry an element label"
    assert card["tier"] in (1, 2, 3)
    if card["rarity"] == "LEGENDARY":
        assert card["evolution_id"] is None
        return
    # Tier-1 monsters point to their tier-2 evolution; tier-2 are terminal.
    if int(card["tier"]) == 1:
        assert card["evolution_id"], f"{card_id} tier-1 monster missing evolution_id"
        assert card["evolution_id"] in CARD_BY_ID, f"{card_id} evolution_id is dangling"
    else:
        assert card["evolution_id"] is None, f"{card_id} tier-2 must not chain further"


@pytest.mark.parametrize("card_id", SPELL_IDS)
def test_spell_carries_stack_effects(card_id):
    card = CARD_BY_ID[card_id]
    assert card["family"] == "SPELL"
    assert card["ability_key"].startswith("spell_")
    assert isinstance(card.get("stack_effects"), list) and card["stack_effects"], (
        f"{card_id} spell must define non-empty stack_effects"
    )


@pytest.mark.parametrize("card_id", TRAP_IDS)
def test_trap_is_face_down_with_trigger(card_id):
    card = CARD_BY_ID[card_id]
    assert card["family"] == "TRAP"
    assert card["ability_key"].startswith("trap_")
    assert card.get("face_down") is True
    assert card.get("trigger_phase") == "COMBAT_PHASE"
    assert card.get("trigger"), f"{card_id} trap missing trigger spec"


# -- _monster_cost direct edge-case sweep -----------------------------------

@pytest.mark.parametrize(
    "attack,guard,evolved,expected",
    [
        # total <= 8 → 1
        (4, 3, False, 1),
        (4, 4, False, 1),
        (5, 3, False, 1),
        # total 9..11 → 2
        (5, 4, False, 2),
        (6, 5, False, 2),
        (7, 4, False, 2),
        # total 12..13 → 3
        (7, 5, False, 3),
        (8, 5, False, 3),
        # total >= 14 → 4
        (8, 6, False, 4),
        (9, 5, False, 4),
        # evolved bumps +1
        (4, 3, True, 2),
        (8, 6, True, 5),
    ],
)
def test_monster_cost_formula(attack, guard, evolved, expected):
    assert _monster_cost(attack, guard, evolved) == expected
