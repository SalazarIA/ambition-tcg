"""K2: Sinergias condicionais — testes unitários."""
from __future__ import annotations

from services import rebirth_keywords as kw


def _card(instance_id="c1", family="FIRE", **extras):
    base = {"instance_id": instance_id, "family": family, "attack": 4, "guard": 3}
    base.update(extras)
    return base


def test_synergy_inactive_without_field():
    c = _card(synergy={"condition": "controls_family", "value": "FIRE", "effect": {"attack": 2}})
    assert kw.synergy_active(c, owner_field=[]) is False


def test_controls_family_synergy_triggers_with_ally():
    me = _card(instance_id="me", family="FIRE",
               synergy={"condition": "controls_family", "value": "FIRE", "effect": {"attack": 2}})
    ally = _card(instance_id="ally", family="FIRE")
    other = _card(instance_id="other", family="WATER")
    assert kw.synergy_active(me, owner_field=[me, ally]) is True
    assert kw.synergy_active(me, owner_field=[me, other]) is False
    # Sozinho (só ele no campo): False (ignora a si mesmo)
    assert kw.synergy_active(me, owner_field=[me]) is False


def test_low_hp_synergy():
    c = _card(synergy={"condition": "low_hp", "value": 10, "effect": {"attack": 3}})
    assert kw.synergy_active(c, owner_field=[c], owner_hp=8) is True
    assert kw.synergy_active(c, owner_field=[c], owner_hp=15) is False


def test_field_count_synergy():
    c = _card(instance_id="me",
              synergy={"condition": "field_count", "value": 2, "effect": {"guard": 2}})
    a = _card(instance_id="a")
    b = _card(instance_id="b")
    assert kw.synergy_active(c, owner_field=[c, a, b]) is True
    assert kw.synergy_active(c, owner_field=[c, a]) is False


def test_tier_2_synergy():
    c = _card(synergy={"condition": "tier_2", "value": None, "effect": {"attack": 1}})
    base = _card(tier=1, instance_id="b")
    evolved = _card(tier=2, instance_id="e")
    assert kw.synergy_active(c, owner_field=[c, base]) is False
    assert kw.synergy_active(c, owner_field=[c, evolved]) is True


def test_synergy_bonus_extraction():
    c = _card(synergy={"condition": "controls_family", "value": "FIRE", "effect": {"attack": 3, "guard": 1}})
    bonus = kw.synergy_bonus(c)
    assert bonus == {"attack": 3, "guard": 1}
    # Sem sinergia
    assert kw.synergy_bonus(_card()) == {"attack": 0, "guard": 0}


def test_synergy_label_pt_br():
    c = _card(synergy={"condition": "controls_family", "value": "fire", "effect": {"attack": 2}})
    label = kw.synergy_label(c)
    assert "Fire" in label
    assert "+2 Ataque" in label

    c2 = _card(synergy={"condition": "low_hp", "value": 12, "effect": {"guard": 1}})
    assert "≤ 12" in kw.synergy_label(c2)
    assert "+1 Guarda" in kw.synergy_label(c2)


def test_unknown_condition_returns_none():
    c = _card(synergy={"condition": "xyz", "value": "x", "effect": {"attack": 1}})
    assert kw.synergy_active(c, owner_field=[c]) is False
    assert kw.synergy_label(c) is None
