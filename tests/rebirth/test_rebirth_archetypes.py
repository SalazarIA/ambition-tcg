"""Onda 2 do roadmap industrial: diversidade de arquétipos (I4-I6)."""

from services.rebirth_cards import (
    family_synergy_coverage,
    get_card,
    keyword_coverage,
)
from services.rebirth_combat_rules import damage_details
from services.rebirth_keywords import ALL_KEYWORDS, synergy_active


def _unit(instance_id, *, attack, guard, family="FIRE", keywords=None):
    return {
        "id": instance_id,
        "instance_id": instance_id,
        "name": instance_id,
        "type": "MONSTER",
        "family": family,
        "attack": attack,
        "power": attack,
        "guard": guard,
        "current_guard": guard,
        "keywords": list(keywords or []),
    }


# --- I4: eixos próprios para WATER (high_hp) e SHADOW (low_hp) ---


def test_high_hp_synergy_rewards_water_inevitability():
    card = _unit("w", attack=4, guard=3, family="WATER")
    card["synergy"] = {"condition": "high_hp", "value": 24, "effect": {"attack": 2}}
    assert synergy_active(card, [card], owner_hp=26) is True
    assert synergy_active(card, [card], owner_hp=18) is False


def test_water_and_shadow_capstones_carry_their_axis():
    assert get_card("card_039")["synergy"]["condition"] == "high_hp"
    assert get_card("card_040")["synergy"]["condition"] == "high_hp"
    assert get_card("card_080")["synergy"]["condition"] == "low_hp"


# --- I5: SIEGE/Cerco perfura muralhas sem virar buff geral ---


def test_siege_ignores_half_the_guard_mitigation():
    attacker_plain = _unit("a", attack=6, guard=4, keywords=[])
    attacker_siege = _unit("s", attack=6, guard=4, keywords=["SIEGE"])
    wall = _unit("wall", attack=2, guard=10, family="EARTH")
    plain = damage_details(attacker_plain, wall)["amount"]
    siege = damage_details(attacker_siege, wall)["amount"]
    assert siege > plain


def test_siege_does_not_help_against_low_guard():
    attacker_plain = _unit("a", attack=6, guard=4, keywords=[])
    attacker_siege = _unit("s", attack=6, guard=4, keywords=["SIEGE"])
    weak = _unit("weak", attack=2, guard=1)
    # É counter à muralha, não um buff de dano genérico: contra Guarda baixa o
    # Cerco não muda nada (1//2 == 1//4 == 0).
    assert damage_details(attacker_siege, weak)["amount"] == damage_details(attacker_plain, weak)["amount"]


def test_fire_capstones_carry_siege():
    assert "SIEGE" in get_card("card_018")["keywords"]
    assert "SIEGE" in get_card("card_020")["keywords"]


# --- I6: auditoria de cobertura (keywords e eixos de família) ---


def test_every_keyword_has_at_least_one_carrier():
    coverage = keyword_coverage()
    missing = [keyword for keyword in ALL_KEYWORDS if not coverage.get(keyword)]
    assert missing == [], f"keywords sem portador no catálogo: {missing}"


def test_every_monster_family_has_a_distinct_win_condition_axis():
    coverage = family_synergy_coverage()
    for family in ("FIRE", "WATER", "EARTH", "SHADOW"):
        assert coverage.get(family), f"família {family} sem eixo de sinergia"
    # Identidades pós-Onda 2: cada família tem seu próprio eixo de vitória.
    assert "total_guard" in coverage["EARTH"]
    assert "high_hp" in coverage["WATER"]
    assert "low_hp" in coverage["SHADOW"]
