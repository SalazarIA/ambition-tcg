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
    """Keywords agora estão LIGADAS na engine, então o spread é escasso por
    design: tier 1 é baseline limpo; tier 2+ carrega a keyword da família
    (evolução/fusão = upgrade mecânico real). TAUNT/BURST/EXECUTE são opt-in
    por carta (lendárias + overrides em rebirth_cards)."""
    # K3 re-centro: FIRE carrega BURST (reach) em todos os tiers — identidade
    # anti-sustain, não recompensa de evolução.
    assert kw.default_keywords_for("FIRE") == [kw.KEYWORD_BURST]
    assert kw.default_keywords_for("FIRE", tier=2) == [kw.KEYWORD_BURST, kw.KEYWORD_RUSH]
    assert kw.default_keywords_for("WATER") == []
    assert kw.default_keywords_for("WATER", tier=2) == [kw.KEYWORD_LIFESTEAL, kw.KEYWORD_REGEN]
    assert kw.default_keywords_for("EARTH", tier=2) == [kw.KEYWORD_SHIELD]
    assert kw.default_keywords_for("SHADOW", tier=2) == [kw.KEYWORD_PIERCE]
    assert kw.default_keywords_for("UNKNOWN") == []
    assert kw.default_keywords_for("UNKNOWN", tier=2) == []


def test_catalog_has_keywords_applied():
    """Todas as evoluções (tier 2) e lendárias carregam keywords funcionais;
    tier 1 fica limpo de propósito (keyword = recompensa de evolução)."""
    tier2 = [c for c in CARD_CATALOG if c.get("type") == "MONSTER" and int(c.get("tier", 1)) >= 2]
    assert tier2, "catálogo precisa de evoluções"
    assert all(c.get("keywords") for c in tier2), "toda evolução deve ter keyword"
    # K3 re-centro: tier 1 é baseline limpo EXCETO FIRE, que carrega BURST
    # (reach) como identidade anti-sustain em todos os tiers.
    tier1 = [c for c in CARD_CATALOG if c.get("type") == "MONSTER" and int(c.get("tier", 1)) == 1 and c.get("rarity") != "LEGENDARY"]
    tier1_fire = [c for c in tier1 if c.get("family") == "FIRE"]
    tier1_rest = [c for c in tier1 if c.get("family") != "FIRE"]
    assert tier1_fire and all("BURST" in (c.get("keywords") or []) for c in tier1_fire), "FIRE tier 1 carrega BURST"
    assert all(not c.get("keywords") for c in tier1_rest), "tier 1 não-FIRE é baseline sem keyword"
    legendaries = [c for c in CARD_CATALOG if c.get("rarity") == "LEGENDARY"]
    assert legendaries and all(c.get("keywords") for c in legendaries)
    with_kw = sum(1 for c in CARD_CATALOG if c.get("keywords"))
    # tier2 (>=2) já inclui as lendárias (tier 3); + as FIRE tier 1 com BURST.
    assert with_kw == len(tier2) + len(tier1_fire)


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
    # K3 re-centro: BURST subiu de 1 → 2 (reach anti-sustain da família FIRE).
    assert kw.on_summon_burst(burst) == 2
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
