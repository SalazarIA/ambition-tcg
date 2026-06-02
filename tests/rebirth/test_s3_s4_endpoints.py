"""S3 + S4 endpoint smoke tests.

Cobre os endpoints adicionados nos sprints recentes:
  - GET  /api/rebirth/ranking/me
  - GET  /api/rebirth/ranking/top
  - GET  /rebirth/ranking
  - GET  /rebirth/billing
  - POST /api/rebirth/billing/checkout   (desligado por padrão)
  - POST /api/rebirth/billing/webhook    (desligado por padrão; 503 se billing ligado sem secret)
  - GET  /robots.txt
  - GET  /sitemap.xml
"""
from __future__ import annotations

import os
import pytest

import app as application


@pytest.fixture
def client(monkeypatch):
    application.app.config["TESTING"] = True
    application.app.config["REBIRTH_REQUIRE_CSRF"] = False
    previous_billing = application.app.config.get("REBIRTH_ENABLE_BILLING")
    previous_live = application.app.config.get("REBIRTH_ALLOW_STRIPE_LIVE")
    application.app.config["REBIRTH_ENABLE_BILLING"] = False
    application.app.config["REBIRTH_ALLOW_STRIPE_LIVE"] = False
    # Garante que Stripe NÃO está configurado pra testar fallback 503.
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    with application.app.test_client() as c:
        yield c
    application.app.config["REBIRTH_ENABLE_BILLING"] = previous_billing
    application.app.config["REBIRTH_ALLOW_STRIPE_LIVE"] = previous_live


def test_ranking_page_renders(client):
    res = client.get("/rebirth/ranking")
    assert res.status_code == 200
    assert b"Ranking" in res.data
    assert b"Temporada" in res.data


def test_ranking_top_api_anonymous(client):
    res = client.get("/api/rebirth/ranking/top")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ok"] is True
    assert isinstance(payload["top"], list)


def test_ranking_me_requires_auth(client):
    res = client.get("/api/rebirth/ranking/me")
    assert res.status_code == 401
    payload = res.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "auth_required"


def test_billing_page_renders(client):
    res = client.get("/rebirth/billing")
    assert res.status_code == 200
    assert b"Gemas" in res.data
    # 3 packs renderizados
    assert b'data-package-id="gems_100"' in res.data
    assert b'data-package-id="gems_550"' in res.data
    assert b'data-package-id="gems_1300"' in res.data


def test_billing_checkout_requires_auth(client):
    res = client.post("/api/rebirth/billing/checkout", json={"package_id": "gems_100"})
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "auth_required"


def test_billing_webhook_disabled_by_default(client):
    res = client.post(
        "/api/rebirth/billing/webhook",
        json={"type": "ping"},
    )

    assert res.status_code == 200
    assert res.get_data(as_text=True) == "billing_disabled"


def test_billing_webhook_without_secret_rejected_when_billing_enabled(client):
    application.app.config["REBIRTH_ENABLE_BILLING"] = True
    res = client.post(
        "/api/rebirth/billing/webhook",
        json={"type": "ping"},
    )

    assert res.status_code == 503


def test_robots_txt_disallows_api(client):
    res = client.get("/robots.txt")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "User-agent: *" in body
    assert "Disallow: /api/" in body
    assert "Sitemap:" in body


def test_sitemap_xml_lists_public_pages(client):
    res = client.get("/sitemap.xml")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "<?xml" in body
    assert "<urlset" in body
    for path in ("/rebirth", "/rebirth/campaign", "/rebirth/ranking", "/rebirth/billing"):
        assert path in body, f"sitemap não inclui {path}"
