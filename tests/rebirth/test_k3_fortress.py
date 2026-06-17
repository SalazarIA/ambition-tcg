"""K3 Fortaleza — payoff defensivo via keywords (THORNS, ENTRENCH) + sinergia
de win-condition (total_guard).

Estes testes travam o contrato da Onda 1 do roadmap de profundidade: as
mecânicas mudam o INCENTIVO de defender (punir agressão / recompensar segurar a
linha), não os números. Inclui hooks puros e prova de integração no engine real.
"""
from __future__ import annotations

from services import rebirth_keywords as kw
from services.rebirth_bot import attack_utility_projection
from services.rebirth_cards import get_card
from services.rebirth_domain import CARD_SET_VERSION, ENGINE_VERSION, RULESET_VERSION
from services.rebirth_engine import (
    _bot_auto_summon,
    create_card_instance,
    declare_attack,
    next_turn,
    play_card,
    start_match,
)


def _make_card(**overrides):
    base = {"id": "test_001", "name": "Test", "guard": 3, "attack": 4, "keywords": []}
    base.update(overrides)
    return base


# ───────────────────────── hooks puros ─────────────────────────

def test_thorns_reflect_hook():
    assert kw.thorns_reflect(_make_card(keywords=[kw.KEYWORD_THORNS])) == kw.THORNS_REFLECT_AMOUNT
    assert kw.thorns_reflect(_make_card()) == 0


def test_entrench_growth_hook():
    assert kw.entrench_growth(_make_card(keywords=[kw.KEYWORD_ENTRENCH])) == kw.ENTRENCH_GROWTH_AMOUNT
    assert kw.entrench_growth(_make_card()) == 0


def test_new_keywords_are_registered():
    assert kw.KEYWORD_THORNS in kw.ALL_KEYWORDS
    assert kw.KEYWORD_ENTRENCH in kw.ALL_KEYWORDS
    assert kw.KEYWORD_THORNS in kw.KEYWORD_LABELS
    assert kw.KEYWORD_ENTRENCH in kw.KEYWORD_LABELS
    assert kw.KEYWORD_THORNS in kw.KEYWORD_COLORS
    assert kw.KEYWORD_ENTRENCH in kw.KEYWORD_COLORS


def test_total_field_guard_sums_current_guard():
    field = [
        {"current_guard": 4, "instance_id": "a"},
        {"current_guard": 5, "instance_id": "b"},
        {"current_guard": 0, "instance_id": "c"},
    ]
    assert kw.total_field_guard(field) == 9
    assert kw.total_field_guard(field, exclude_instance_id="b") == 4


def test_total_guard_synergy_activates_at_threshold():
    anchor = {
        "instance_id": "anchor",
        "current_guard": 3,
        "synergy": {"condition": "total_guard", "value": 8, "effect": {"attack": 2}},
    }
    field = [anchor, {"current_guard": 5, "instance_id": "ally"}]
    # 3 (anchor) + 5 (ally) = 8 ≥ 8 → ativo
    assert kw.synergy_active(anchor, field) is True
    assert kw.synergy_bonus(anchor) == {"attack": 2, "guard": 0}
    # Sozinho abaixo do limiar → inativo
    lone = dict(anchor, instance_id="lone")
    assert kw.synergy_active(lone, [lone]) is False
    assert "Guarda total" in (kw.synergy_label(anchor) or "")


# ──────────────────── integração no engine real ────────────────────

def test_thorns_reflects_guard_to_attacker_on_field_combat():
    """Atacar uma muralha com Espinhos custa Guarda ao atacante mesmo quando
    o ataque vence o combate — o problema-raiz dos findings (agressão impune)."""
    match = start_match(seed="k3-thorns")
    attacker = create_card_instance("card_002", "player", 1)
    match["player"]["hand"] = [attacker]
    match["player"]["energy"] = 9
    play_card(match, card_instance_id=attacker["instance_id"])

    # Cenário roteirizado: atacante forte e tanky o bastante p/ sobreviver aos
    # 2 de Espinhos e vencer o defensor.
    bf = match["player"]["battlefield"][0]
    bf["attack"] = bf["power"] = 5
    bf["guard"] = bf["max_guard"] = bf["current_guard"] = 6
    bf["just_summoned"] = False

    match["bot"]["hand"] = [{
        "id": "test_thorns", "name": "Muralha Espinhada", "type": "MONSTER",
        "card_type": "MONSTER", "family": "EARTH", "role": "Wall", "tier": 1,
        "cost": 0, "attack": 1, "guard": 2, "power": 1, "element": "Terra",
        "evolution_id": None, "ability_key": "test_card", "ability_name": "Test",
        "ability_text": "Test.", "flavor": "Test.", "art": "x",
        "keywords": [kw.KEYWORD_THORNS], "instance_id": "bot-thorns",
    }]
    _bot_auto_summon(match)

    result = declare_attack(
        match,
        attacker_instance_id=bf["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    assert result["winner"] == "player"
    # Atacante venceu mas levou 2 de Espinhos na Guarda (6 → 4).
    survivor = match["player"]["battlefield"][0]
    assert survivor["instance_id"] == bf["instance_id"]
    assert survivor["current_guard"] == 4
    assert "Espinhos" in result["message"]


def test_thorns_does_not_fire_when_attacker_loses():
    """Se o atacante já perde o combate, não há agressão a punir — sem Espinhos
    (evita double-dip de punição)."""
    match = start_match(seed="k3-thorns-loss")
    attacker = create_card_instance("card_002", "player", 1)
    match["player"]["hand"] = [attacker]
    match["player"]["energy"] = 9
    play_card(match, card_instance_id=attacker["instance_id"])

    bf = match["player"]["battlefield"][0]
    bf["attack"] = bf["power"] = 1            # fraco: perde o combate
    bf["guard"] = bf["max_guard"] = bf["current_guard"] = 6
    bf["just_summoned"] = False

    match["bot"]["hand"] = [{
        "id": "test_thorns2", "name": "Fortaleza", "type": "MONSTER",
        "card_type": "MONSTER", "family": "EARTH", "role": "Wall", "tier": 1,
        "cost": 0, "attack": 9, "guard": 9, "power": 9, "element": "Terra",
        "evolution_id": None, "ability_key": "test_card", "ability_name": "Test",
        "ability_text": "Test.", "flavor": "Test.", "art": "x",
        "keywords": [kw.KEYWORD_THORNS], "instance_id": "bot-thorns2",
    }]
    _bot_auto_summon(match)

    result = declare_attack(
        match,
        attacker_instance_id=bf["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )
    assert result["winner"] == "bot"
    assert "Espinhos" not in result["message"]


def test_entrench_grows_guard_when_holding_the_line():
    """Quem segura a linha (não ataca) fortalece a muralha no turno seguinte."""
    match = start_match(seed="k3-entrench")
    holder = create_card_instance("card_041", "player", 1)
    match["player"]["hand"] = [holder]
    match["player"]["energy"] = 9
    play_card(match, card_instance_id=holder["instance_id"])

    bf = match["player"]["battlefield"][0]
    bf["keywords"] = [kw.KEYWORD_ENTRENCH]
    bf["guard"] = bf["max_guard"] = bf["current_guard"] = 4
    bf["has_attacked"] = False

    # Isola: bot sem cartas → não invoca nem ataca a muralha.
    match["bot"]["hand"] = []
    match["bot"]["deck"] = []

    next_turn(match)

    grown = match["player"]["battlefield"][0]
    assert grown["instance_id"] == bf["instance_id"]
    assert grown["max_guard"] == 5
    assert grown["current_guard"] == 5


# ──────────────────── arquétipo no catálogo (Onda 2) ────────────────────

def test_fortress_keyword_kit_on_earth_cards():
    # TAUNT + THORNS na mesma muralha: o alvo forçado pune quem o ataca.
    assert {kw.KEYWORD_TAUNT, kw.KEYWORD_THORNS} <= set(get_card("card_051")["keywords"])  # Stonehide Bulwark
    assert kw.KEYWORD_THORNS in get_card("card_056")["keywords"]      # Bramblehorn Paragon
    assert kw.KEYWORD_ENTRENCH in get_card("card_058")["keywords"]    # Ironbark Warden
    assert {kw.KEYWORD_TAUNT, kw.KEYWORD_ENTRENCH} <= set(get_card("card_059")["keywords"])  # Terrashield Ascetic
    assert kw.KEYWORD_ENTRENCH in get_card("card_060")["keywords"]    # Boulderwake Primordial
    # SHIELD preservado (identidade EARTH) em toda a linha de muralhas.
    for cid in ("card_051", "card_056", "card_058", "card_059", "card_060"):
        assert kw.KEYWORD_SHIELD in get_card(cid)["keywords"]


def test_fortress_wincon_synergy_anchors():
    for cid in ("card_044", "card_050", "card_060"):
        syn = get_card(cid).get("synergy") or {}
        assert syn.get("condition") == "total_guard", f"{cid} deve ancorar a win-con de Fortaleza"
        assert syn.get("effect", {}).get("attack", 0) >= 2


def test_fortress_kit_keeps_tier1_keyword_clean():
    """A win-con de tier-1 (Granite Pactbearer/Boulderwake Colossus) vem por
    SINERGIA, não por keyword — preserva a regra 'tier-1 limpo de keyword'."""
    assert not get_card("card_044").get("keywords")
    assert not get_card("card_050").get("keywords")


def test_bot_projection_respects_thorns():
    """A IA do bot (Onda 4) sabe que atacar uma muralha espinhada custa Guarda
    ao atacante — evita jogar corpos em THORNS sem lethal."""
    attacker = {"instance_id": "a", "attack": 5, "power": 5, "guard": 2,
                "current_guard": 2, "tier": 1, "keywords": []}
    thorns_wall = {"instance_id": "w", "attack": 1, "power": 1, "guard": 4,
                   "current_guard": 4, "tier": 1, "keywords": [kw.KEYWORD_THORNS]}
    plain_wall = {"instance_id": "p", "attack": 1, "power": 1, "guard": 4,
                  "current_guard": 4, "tier": 1, "keywords": []}
    proj_t = attack_utility_projection(attacker, thorns_wall, bot_battlefield=[attacker],
                                       player_battlefield=[thorns_wall], turn=3)
    proj_p = attack_utility_projection(attacker, plain_wall, bot_battlefield=[attacker],
                                       player_battlefield=[plain_wall], turn=3)
    # Atacante (Guarda 2) vence o clash mas morre pros 2 de Espinhos só no caso THORNS.
    assert proj_t["attacker_destroyed"] is True
    assert proj_p["attacker_destroyed"] is False
    assert proj_t["utility"] < proj_p["utility"]


def test_engine_version_bumped_to_v100():
    assert ENGINE_VERSION.endswith("v100")
    assert CARD_SET_VERSION.endswith("v100")
    assert RULESET_VERSION.endswith("v100")


def test_entrench_does_not_grow_after_attacking():
    """Se a carta atacou no turno anterior, não há entrincheiramento."""
    match = start_match(seed="k3-entrench-attacked")
    holder = create_card_instance("card_041", "player", 1)
    match["player"]["hand"] = [holder]
    match["player"]["energy"] = 9
    play_card(match, card_instance_id=holder["instance_id"])

    bf = match["player"]["battlefield"][0]
    bf["keywords"] = [kw.KEYWORD_ENTRENCH]
    bf["guard"] = bf["max_guard"] = bf["current_guard"] = 4
    bf["has_attacked"] = True  # atacou → sem ENTRENCH

    match["bot"]["hand"] = []
    match["bot"]["deck"] = []

    next_turn(match)

    grown = match["player"]["battlefield"][0]
    assert grown["max_guard"] == 4
    assert grown["current_guard"] == 4
