"""v69: nerfs cirúrgicos do trio opressor (Bramblehorn / Mossback / Coalheart)."""

from services.rebirth_cards import CARD_BALANCE_OVERRIDES, get_card
from services.rebirth_engine import damage_details


def make_card(**fields):
    base = {"attack": 0, "power": 0, "guard": 0, "ability_key": "", "name": "X"}
    base.update(fields)
    base.setdefault("power", base["attack"])
    return base


def test_v69_bramblehorn_cost_override_applied():
    card = get_card("card_046")
    assert card["name"] == "Bramblehorn Knight"
    assert card["cost"] == 3, "v69 nerf: Bramblehorn deve subir de 2 para 3 mana"


def test_v69_mossback_cost_override_applied():
    card = get_card("card_045")
    assert card["name"] == "Mossback Brute"
    assert card["cost"] == 3, "v69 nerf: Mossback deve subir de 2 para 3 mana"


def test_v69_balance_overrides_documents_only_targeted_cards():
    # Garante que o nerf não vazou pra cartas além do trio documentado.
    assert set(CARD_BALANCE_OVERRIDES.keys()) == {"card_045", "card_046"}


def test_v69_fire_execute_bonus_reduced_to_two():
    attacker = make_card(name="Coalheart Runner", attack=6, ability_key="fire_execute")
    defender = make_card(name="Alvo", guard=2)
    base = damage_details(attacker, defender, defender_wounded=False)
    boosted = damage_details(attacker, defender, defender_wounded=True)
    assert boosted["amount"] - base["amount"] == 2, "v69 nerf: fire_execute deve ser +2 (era +3)"
    msg = " ".join(boosted["events"])
    assert "+2 de dano" in msg, "mensagem do log deve refletir o novo bônus de +2"
    assert "+3" not in msg, "log não pode mais mencionar +3"


def test_v69_fire_execute_unchanged_against_healthy_targets():
    attacker = make_card(name="Coalheart Runner", attack=6, ability_key="fire_execute")
    defender = make_card(name="Alvo", guard=4)
    result = damage_details(attacker, defender, defender_wounded=False)
    # Sem o trigger de wounded, fire_execute não soma — só vira finisher contra ferido.
    assert all("fire_execute" not in event for event in result["events"])
    assert all("+2 de dano" not in event for event in result["events"])
