"""K1: Sistema de keywords mecânicas — testes unitários."""
from __future__ import annotations

import pytest

from services import rebirth_keywords as kw
from services.rebirth_cards import CARD_CATALOG


def _make_card(**overrides):
    base = {"id": "test_001", "name": "Test", "guard": 3, "attack": 4, "keywords": []}
    base.update(overrides)
    return base


def test_default_keywords_by_family():
    """Cada família ganha seu keyword default; tier ≥ 2 ganha bônus (quando aplicável).

    Calibração K2: TAUNT/BURST/EXECUTE removidos dos defaults pra preservar
    balance dos testes v67/v71/v73/v74 — viram opt-in pra cartas lendárias.
    """
    assert kw.default_keywords_for("FIRE") == [kw.KEYWORD_RUSH]
    assert kw.default_keywords_for("FIRE", tier=2) == [kw.KEYWORD_RUSH]
    assert kw.default_keywords_for("WATER") == [kw.KEYWORD_LIFESTEAL]
    assert kw.default_keywords_for("WATER", tier=2) == [kw.KEYWORD_LIFESTEAL, kw.KEYWORD_REGEN]
    assert kw.default_keywords_for("EARTH") == [kw.KEYWORD_SHIELD]
    assert kw.default_keywords_for("SHADOW") == [kw.KEYWORD_PIERCE]
    assert kw.default_keywords_for("UNKNOWN") == []


def test_catalog_has_keywords_applied():
    """Pelo menos 70% das cartas têm keywords (monstros + evoluções)."""
    with_kw = sum(1 for c in CARD_CATALOG if c.get("keywords"))
    assert with_kw >= 70, f"Apenas {with_kw} cards com keywords (esperado ≥70)"


def test_has_keyword_helper():
    card = _make_card(keywords=[kw.KEYWORD_RUSH, kw.KEYWORD_BURST])
    assert kw.has_keyword(card, kw.KEYWORD_RUSH)
    assert kw.has_keyword(card, kw.KEYWORD_BURST)
    assert not kw.has_keyword(card, kw.KEYWORD_TAUNT)
    assert not kw.has_keyword(None, kw.KEYWORD_RUSH)


def test_rush_allows_attack_when_just_summoned():
    rush = _make_card(keywords=[kw.KEYWORD_RUSH])
    no_rush = _make_card(keywords=[])
    # Recém invocada
    assert kw.can_attack_this_turn(rush, just_summoned=True) is True
    assert kw.can_attack_this_turn(no_rush, just_summoned=True) is False
    # Já estava em campo: ambas atacam
    assert kw.can_attack_this_turn(rush, just_summoned=False) is True
    assert kw.can_attack_this_turn(no_rush, just_summoned=False) is True


def test_burst_returns_damage_on_summon():
    burst = _make_card(keywords=[kw.KEYWORD_BURST])
    no_burst = _make_card(keywords=[])
    assert kw.on_summon_burst(burst) == 1
    assert kw.on_summon_burst(no_burst) == 0


def test_lifesteal_heal_proportional():
    leech = _make_card(keywords=[kw.KEYWORD_LIFESTEAL])
    assert kw.lifesteal_heal_amount(leech, 5) == 5
    assert kw.lifesteal_heal_amount(leech, 0) == 0
    assert kw.lifesteal_heal_amount(_make_card(), 5) == 0


def test_pierce_overflow():
    pierce = _make_card(keywords=[kw.KEYWORD_PIERCE])
    no_pierce = _make_card(keywords=[])
    # 6 de dano em guard 4 → 2 overflow
    assert kw.pierce_overflow(pierce, 6, 4) == 2
    # Dano ≤ guard: sem overflow
    assert kw.pierce_overflow(pierce, 3, 4) == 0
    # Sem keyword: sem pierce
    assert kw.pierce_overflow(no_pierce, 10, 4) == 0


def test_taunt_forces_target():
    taunt = _make_card(keywords=[kw.KEYWORD_TAUNT])
    plain = _make_card(keywords=[])
    assert kw.forces_target(taunt)
    assert not kw.forces_target(plain)
    assert kw.has_taunt_on_side([plain, taunt])
    assert not kw.has_taunt_on_side([plain, plain])


def test_shield_absorbs_first_hit():
    shield = _make_card(keywords=[kw.KEYWORD_SHIELD])
    assert kw.shield_absorbs(shield) is True
    # Após consumir
    shield["shield_consumed"] = True
    assert kw.shield_absorbs(shield) is False
    # Sem keyword
    assert kw.shield_absorbs(_make_card()) is False


def test_regen_amount():
    regen = _make_card(keywords=[kw.KEYWORD_REGEN])
    assert kw.regen_amount(regen) == 1
    assert kw.regen_amount(_make_card()) == 0


def test_execute_kills_low_guard():
    executor = _make_card(keywords=[kw.KEYWORD_EXECUTE])
    weak_target = _make_card(guard=1)
    strong_target = _make_card(guard=3)
    assert kw.execute_kills(executor, weak_target)
    assert not kw.execute_kills(executor, strong_target)
    assert not kw.execute_kills(_make_card(), weak_target)
    assert not kw.execute_kills(executor, None)
