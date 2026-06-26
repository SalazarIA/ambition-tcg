"""Crafting (pó/DUST) — desmanchar duplicata -> pó; criar carta <- pó.
Só Comum/Incomum (lendárias são placeholders). Backend determinístico."""
import pytest

from services.rebirth_cards import get_card
from services.rebirth_persistence import RebirthRepository, RebirthPersistenceError


def _repo(flask_app):
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.ensure_schema()
    return repo


def _user(repo, name):
    u = repo.create_user(name, name + "@example.com", "password123")
    return u["id"] if isinstance(u, dict) else u


def _legendary_id():
    from services import rebirth_cards as C
    pool = getattr(C, "CARD_CATALOG", None) or getattr(C, "ALL_CARDS", None)
    if pool:
        for card in (pool.values() if hasattr(pool, "values") else pool):
            if card.get("rarity") == "LEGENDARY":
                return card.get("id")
    return None


def test_disenchant_then_craft_roundtrip(flask_app):
    repo = _repo(flask_app)
    uid = _user(repo, "crafter")
    repo.add_cards(uid, [get_card("card_001")] * 9)  # Comum, 9 cópias extras
    assert repo.get_dust(uid) == 0
    last = None
    for _ in range(8):
        last = repo.disenchant_card(uid, "card_001")  # +5 pó cada
    assert last["dust"] == 40
    crafted = repo.craft_card(uid, "card_001")  # Comum custa 40
    assert crafted["spent"] == 40
    assert crafted["dust"] == 0


def test_craft_rejects_insufficient_dust(flask_app):
    repo = _repo(flask_app)
    uid = _user(repo, "broke")
    with pytest.raises(RebirthPersistenceError):
        repo.craft_card(uid, "card_001")  # 0 pó


def test_legendary_is_not_craftable(flask_app):
    leg = _legendary_id()
    if not leg:
        pytest.skip("nenhuma lendária no catálogo")
    repo = _repo(flask_app)
    uid = _user(repo, "leg")
    with pytest.raises(RebirthPersistenceError):
        repo.craft_card(uid, leg)
