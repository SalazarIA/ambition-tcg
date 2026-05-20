from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_rebirth_product_pages_render_active_shell(client):
    expected = {
        "/rebirth/account": "Create Account",
        "/rebirth/collection": "Cards",
        "/rebirth/shop": "Packs",
        "/rebirth/progression": "Rewards",
        "/rebirth/profile": "Player Profile",
        "/rebirth/lab": "Rebirth Lab",
        "/rebirth/history": "Match History + Economy Ledger",
        "/rebirth/desktop": "Desktop Arena Polish",
        "/rebirth/onboarding": "Onboarding/Tutorial Rebirth",
        "/rebirth/balance": "Balance + Bot Tuning",
        "/rebirth/support": "Support + Admin Safety",
        "/rebirth/release": "Release Candidate Hygiene",
    }

    for path, label in expected.items():
        response = client.get(path)
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Ambitionz Rebirth" in body
        assert label in body
        assert "rebirth_product.js" in body
        assert "Socket.IO" not in body


def test_rebirth_product_api_contracts_are_rebirth_native(client):
    shell = client.get("/api/rebirth/shell")
    auth = client.get("/api/rebirth/auth-plan")
    collection = client.get("/api/rebirth/collection")
    shop = client.get("/api/rebirth/shop")
    progression = client.get("/api/rebirth/progression")
    profile = client.get("/api/rebirth/profile")
    history_locked = client.get("/api/rebirth/match-history")
    ledger_locked = client.get("/api/rebirth/economy-ledger")
    desktop = client.get("/api/rebirth/desktop")
    onboarding = client.get("/api/rebirth/onboarding")
    balance = client.get("/api/rebirth/balance/simulate?matches=8")
    release = client.get("/api/rebirth/release")

    assert shell.status_code == 200
    assert shell.get_json()["shell"]["status"][0]["value"] == "One Card Clash"
    assert auth.status_code == 200
    assert auth.get_json()["auth"]["steps"][0]["title"] == "Create"
    assert collection.status_code == 200
    assert collection.get_json()["collection"]["summary"]["loadout_size"] == 8
    assert shop.status_code == 200
    assert shop.get_json()["shop"]["offers"][0]["price"] == "Free"
    assert progression.status_code == 200
    assert progression.get_json()["progression"]["profile"]["level"] == 1
    assert profile.status_code == 200
    assert profile.get_json()["profile"]["stats"][0]["label"] == "Level"
    assert history_locked.status_code == 401
    assert history_locked.get_json()["error"]["code"] == "auth_required"
    assert ledger_locked.status_code == 401
    assert ledger_locked.get_json()["error"]["code"] == "auth_required"
    assert desktop.status_code == 200
    assert "Portrait board" in desktop.get_json()["desktop"]["checks"][0]
    assert onboarding.status_code == 200
    assert onboarding.get_json()["onboarding"]["steps"][0]["title"] == "Pick One Monster"
    assert balance.status_code == 200
    assert balance.get_json()["balance"]["matches"] == 8
    assert release.status_code == 200
    assert release.get_json()["release"]["checks"][0]["name"] == "Product Truth"


def test_rebirth_loadout_preview_validates_owned_cards(client):
    client.post(
        "/api/rebirth/auth/register",
        json={"username": "loadout_user", "email": "loadout@example.com", "password": "password123"},
    )
    valid = [
        "dreadclaw",
        "dreadclaw",
        "stoneshell",
        "shadewisp",
        "skywarden",
        "ironbastion",
        "embermaw",
        "voidstalker",
    ]
    response = client.post("/api/rebirth/loadout", json={"card_ids": valid})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["loadout"]["summary"]["size"] == 8
    assert payload["loadout"]["summary"]["duplicate_pairs"] == 1

    invalid = client.post("/api/rebirth/loadout", json={"card_ids": ["dreadclaw"]})
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "invalid_loadout"


def test_rebirth_booster_demo_returns_four_cards_without_economy(client):
    unauthenticated = client.post("/api/rebirth/booster/open", json={"seed": "booster-test"})
    assert unauthenticated.status_code == 401
    assert unauthenticated.get_json()["error"]["code"] == "auth_required"

    client.post(
        "/api/rebirth/auth/register",
        json={"username": "booster_user", "email": "booster@example.com", "password": "password123"},
    )
    response = client.post("/api/rebirth/booster/open", json={"seed": "booster-test"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["booster"]["booster_id"] == "starter_booster_demo"
    assert payload["booster"]["summary"]["count"] == 4
    assert len(payload["booster"]["cards"]) == 4

    shop = client.get("/api/rebirth/shop").get_json()["shop"]
    assert "Packs are free during the Rebirth beta" in shop["disclaimer"]


def test_rebirth_product_shell_does_not_load_legacy_assets():
    combined = "\n".join(
        [
            read("templates/index.html"),
            read("templates/rebirth.html"),
            read("templates/rebirth_product.html"),
            read("static/js/rebirth_product.js"),
        ]
    )

    for forbidden in [
        "arena_clean",
        "arena3d",
        "ambitionz_theme",
        "ambitionz_progression",
        "ambitionz_ui",
        "card_system",
        "Socket.IO",
        "/api/booster",
    ]:
        assert forbidden not in combined
