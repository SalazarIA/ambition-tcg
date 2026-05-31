"""K3: Deck Builder — testes de persistência + endpoints."""
from __future__ import annotations

import pytest

import app as application


@pytest.fixture
def client(monkeypatch):
    application.app.config["TESTING"] = True
    application.app.config["REBIRTH_REQUIRE_CSRF"] = False
    with application.app.test_client() as c:
        yield c


def test_catalog_endpoint_returns_card_list(client):
    res = client.get("/api/rebirth/catalog")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ok"] is True
    assert payload["count"] >= 100
    sample = payload["catalog"][0]
    assert "id" in sample
    assert "name" in sample
    assert "keywords" in sample


def test_deck_builder_page_renders(client):
    res = client.get("/rebirth/deck-builder")
    assert res.status_code == 200
    assert b"Deck Builder" in res.data
    assert b"data-deck-builder" in res.data


def test_decks_list_requires_auth(client):
    res = client.get("/api/rebirth/decks")
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "auth_required"


def test_decks_create_requires_auth(client):
    res = client.post("/api/rebirth/decks", json={"name": "X", "cards": []})
    assert res.status_code == 401


def test_validate_deck_size():
    """Validação isolada: deck precisa ter 30 cartas."""
    from services.rebirth_persistence import RebirthRepository, RebirthPersistenceError
    repo = RebirthRepository.__new__(RebirthRepository)
    # Deck com 10 cards apenas
    with pytest.raises(RebirthPersistenceError) as exc:
        repo._validate_deck_cards(["card_001"] * 10)
    assert exc.value.code == "deck_invalid_size"


def test_validate_deck_max_copies():
    """Validação: max 3 cópias por carta."""
    from services.rebirth_persistence import RebirthRepository, RebirthPersistenceError
    repo = RebirthRepository.__new__(RebirthRepository)
    # 30 cartas no total mas 4 cópias de uma única
    cards = ["card_001"] * 4 + ["card_002"] * 26
    with pytest.raises(RebirthPersistenceError) as exc:
        repo._validate_deck_cards(cards)
    assert exc.value.code == "deck_invalid_copies"


def test_validate_deck_invalid_card_id():
    """Validação: card_id deve existir no catálogo."""
    from services.rebirth_persistence import RebirthRepository, RebirthPersistenceError
    # 30 cartas distribuídas: 1 inválida + 29 válidas (1 cópia cada).
    # Total=30 e copies=1 passam as fases 2 e 3; fase 4 detecta o ID fake.
    repo = RebirthRepository.__new__(RebirthRepository)
    cards = ["card_999"] + [f"card_{i:03d}" for i in range(1, 30)]
    with pytest.raises(RebirthPersistenceError) as exc:
        repo._validate_deck_cards(cards)
    assert exc.value.code == "deck_invalid_card"


def test_validate_deck_accepts_valid_30_card_deck():
    """Caso válido: 30 cartas, 1-3 cópias cada, todos IDs reais."""
    from services.rebirth_persistence import RebirthRepository
    from services.rebirth_cards import CARD_CATALOG
    repo = RebirthRepository.__new__(RebirthRepository)
    valid_ids = [c["id"] for c in CARD_CATALOG if c.get("id", "").startswith("card_")][:10]
    # 3 cópias dos 10 primeiros = 30
    cards = []
    for cid in valid_ids:
        cards.extend([cid] * 3)
    counts = repo._validate_deck_cards(cards)
    assert sum(counts.values()) == 30
    assert all(1 <= c <= 3 for c in counts.values())
