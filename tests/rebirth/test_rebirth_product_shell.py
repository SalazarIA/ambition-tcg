from datetime import datetime, timezone
from pathlib import Path

from services.rebirth_beta_ops import external_gate_payload
from services.rebirth_gate_evidence import validate_external_gate_evidence


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def valid_external_evidence():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "legal_review": {
            "approved": True,
            "reviewer": "Operator",
            "approved_at": now,
            "scope": ["terms", "privacy", "data_deletion", "billing_disabled"],
            "evidence_ref": "private-ticket-legal-1",
        },
        "backup_restore": {
            "validated": True,
            "drill_at": now,
            "operator": "Operator",
            "source_commit": "abc123",
            "restore_target": "redacted-restore-db",
            "dump_bytes": 42,
            "schema_check": "passed",
            "health_check": "passed",
            "support_export_check": "passed",
            "evidence_ref": "private-ticket-dr-1",
        },
        "error_tracking": {
            "validated": True,
            "provider": "glitchtip",
            "environment": "closed-beta",
            "test_event_id": "event-123",
            "tested_at": now,
            "evidence_ref": "private-ticket-sentry-1",
        },
    }


def test_rebirth_product_pages_render_active_shell(client):
    expected = {
        "/rebirth/account": "Login / Cadastro",
        "/rebirth/collection": "Minha Coleção",
        "/rebirth/shop": "Loja &amp; Mercado",
        "/rebirth/progression": "Recompensas",
        "/rebirth/profile": "Perfil do Jogador",
        "/rebirth/lab": "Laboratório Rebirth",
        "/rebirth/history": "Histórico de Partidas + Extrato Econômico",
        "/rebirth/desktop": "Polimento da Arena Desktop",
        "/rebirth/onboarding": "Introdução/Tutorial Rebirth",
        "/rebirth/balance": "Balanceamento + Ajuste do Bot",
        "/rebirth/support": "Suporte + Segurança Administrativa",
        "/rebirth/release": "Higiene da Versão Candidata",
    }

    for path, label in expected.items():
        response = client.get(path)
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Ambitionz Rebirth" in body
        assert label in body
        assert "rebirth_product.js" in body
        assert "Socket.IO" not in body
        if path in {"/rebirth/profile", "/rebirth/progression"}:
            assert "data-rebirth-progression-dashboard" in body
            assert "data-rebirth-ledger-list" in body
            assert "authenticated: false" in body
        if path == "/rebirth/shop":
            assert "Mercado de Jogadores" in body
            assert "data-rebirth-market-offers" in body
        if path == "/rebirth/account":
            assert "age_confirmed" in body
            assert "privacy_accepted" in body
        if path == "/rebirth/support":
            assert "data-rebirth-delete-account" in body
            assert "Excluir Minha Conta" in body
            assert "data-rebirth-feedback" in body
        if path == "/rebirth/progression":
            assert "Loop de retenção beta" in body
            assert "rb-quest-grid" in body
            assert "Coach de deck" in body
        if path == "/rebirth/onboarding":
            assert "Glossário de keywords" in body
            assert "rb-keyword-grid" in body
        if path == "/rebirth/release":
            assert "Readiness Final" in body
            assert "Evidência externa" in body
            assert "Gate Beta Público" in body
            assert "evidence_missing" in body
            assert "--evidence /secure/path/rebirth-external-gates.json" in body
            assert "tools/ops/rebirth_public_beta_gate.py --since &lt;cohort-start-iso&gt; --require-ready" in body
            assert (
                "tools/ops/rebirth_release_readiness.py --since &lt;cohort-start-iso&gt; "
                "--evidence /secure/path/rebirth-external-gates.json"
            ) in body


def test_phase0_legal_pages_are_publicly_reachable(client):
    expected = {
        "/terms": "Terms of Use",
        "/privacy": "Privacy Policy",
        "/data-deletion": "Data Deletion",
    }

    for path, title in expected.items():
        response = client.get(path)
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert title in body
        assert "/rebirth/support" in body or "feedback" in body.lower()

    feedback = client.get("/feedback")
    closed_test = client.get("/closed-test")
    first_session = client.get("/first-session")
    assert feedback.status_code == 302
    assert feedback.headers["Location"] == "/rebirth/support"
    assert closed_test.headers["Location"] == "/rebirth/release"
    assert first_session.headers["Location"] == "/rebirth/onboarding"


def test_collection_renders_root_relative_card_art_urls(client):
    body = client.get("/rebirth/collection").get_data(as_text=True)

    assert 'src="/static/img/cards/baralho/' in body
    assert 'src="static/img/cards/baralho/' not in body
    assert "O que importa agora" in body
    assert "rb-catalog-drawer" in body
    assert "Ver catálogo completo" in body
    assert "built-in method" not in body


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
    assert shell.get_json()["shell"]["status"][0]["value"] == "Clash TCG"
    assert auth.status_code == 200
    assert auth.get_json()["auth"]["steps"][0]["title"] == "Criar"
    assert collection.status_code == 200
    collection_payload = collection.get_json()["collection"]
    assert collection_payload["summary"]["loadout_size"] == 30
    assert collection_payload["collection_sections"][0]["title"] == "Núcleo do baralho"
    assert len(collection_payload["collection_sections"][0]["cards"]) <= 12
    assert shop.status_code == 200
    assert shop.get_json()["shop"]["offers"][0]["price"] == "Grátis na beta"
    assert progression.status_code == 200
    assert progression.get_json()["progression"]["profile"]["level"] == 1
    assert profile.status_code == 200
    assert profile.get_json()["profile"]["stats"][0]["label"] == "Nível"
    assert history_locked.status_code == 401
    assert history_locked.get_json()["error"]["code"] == "auth_required"
    assert ledger_locked.status_code == 401
    assert ledger_locked.get_json()["error"]["code"] == "auth_required"
    assert desktop.status_code == 200
    assert "tabuleiro vertical" in desktop.get_json()["desktop"]["checks"][0]
    assert onboarding.status_code == 200
    assert onboarding.get_json()["onboarding"]["steps"][0]["title"] == "Escolha Um Monstro"
    assert len(onboarding.get_json()["onboarding"]["keyword_glossary"]) >= 8
    assert balance.status_code == 200
    assert balance.get_json()["balance"]["matches"] == 8
    assert release.status_code == 200
    assert release.get_json()["release"]["checks"][0]["name"] == "Produto Ativo"
    assert any(check["name"] == "LGPD Self-Service" for check in release.get_json()["release"]["checks"])
    assert release.get_json()["release"]["external_gates"]["checks"][0]["key"] == "legal_review"
    assert release.get_json()["release"]["external_gates"]["evidence"]["legal_review"]["errors"] == ["evidence_missing"]
    assert release.get_json()["release"]["dashboard"]["cards"][0]["label"] == "D1 ativos"
    assert release.get_json()["release"]["public_beta_gate"]["version"] == "public-beta-gate-v1"
    assert release.get_json()["release"]["public_beta_gate"]["ready"] is False
    assert release.get_json()["release"]["release_readiness"]["version"] == "rebirth-release-readiness-v1"
    assert release.get_json()["release"]["release_readiness"]["ready"] is False

    windowed_release = client.get("/api/rebirth/release?since=2026-06-01T00:00:00+00:00")
    windowed_payload = windowed_release.get_json()["release"]
    assert windowed_release.status_code == 200
    assert windowed_payload["dashboard"]["since"] == "2026-06-01T00:00:00+00:00"
    assert windowed_payload["live_balance"]["since"] == "2026-06-01T00:00:00+00:00"
    assert windowed_payload["public_beta_gate"]["since"] == "2026-06-01T00:00:00+00:00"


def test_external_beta_gate_parses_string_booleans():
    gates = external_gate_payload(
        {
            "REBIRTH_ENABLE_BILLING": "false",
            "REBIRTH_ALLOW_STRIPE_LIVE": "false",
            "REBIRTH_LEGAL_REVIEWED": "true",
            "REBIRTH_BACKUP_RESTORE_DRILL": "true",
            "REBIRTH_GITHUB_QA_GREEN": "true",
            "SENTRY_DSN": "https://example.invalid/1",
        }
    )

    assert gates["ready"] is True
    assert gates["billing_enabled"] is False
    assert {check["key"]: check["state"] for check in gates["checks"]}["billing_off"] == "passed"


def test_external_beta_gate_accepts_secret_free_evidence():
    gates = external_gate_payload(
        {
            "REBIRTH_ENABLE_BILLING": "false",
            "REBIRTH_ALLOW_STRIPE_LIVE": "false",
        },
        workflow={"conclusion": "success"},
        evidence=valid_external_evidence(),
    )
    states = {check["key"]: check["state"] for check in gates["checks"]}

    assert gates["ready"] is True
    assert states["legal_review"] == "passed"
    assert states["backup_restore"] == "passed"
    assert states["error_tracking"] == "passed"
    assert gates["evidence"]["legal_review"]["valid"] is True


def test_external_gate_evidence_rejects_examples_and_secrets():
    evidence = valid_external_evidence()
    evidence["example"] = True
    evidence["backup_restore"]["restore_target"] = "postgresql://user:password@example.invalid/db"
    report = validate_external_gate_evidence(evidence)

    assert report["legal_review"]["valid"] is False
    assert "example_evidence_file" in report["legal_review"]["errors"]
    assert report["backup_restore"]["valid"] is False
    assert "secret_like_value_detected" in report["backup_restore"]["errors"]


def test_rebirth_loadout_preview_validates_owned_cards(client):
    client.post(
        "/api/rebirth/auth/register",
        json={"username": "loadout_user", "email": "loadout@example.com", "password": "password123"},
    )
    valid = [card["id"] for card in client.get("/api/rebirth/collection").get_json()["collection"]["loadout"]]
    response = client.post("/api/rebirth/loadout", json={"card_ids": valid})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["loadout"]["summary"]["size"] == 30
    assert payload["loadout"]["summary"]["duplicate_pairs"] >= 1

    invalid = client.post("/api/rebirth/loadout", json={"card_ids": ["card_001"]})
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "invalid_loadout"


def test_rebirth_booster_demo_returns_five_cards_without_economy(client):
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
    assert payload["booster"]["summary"]["count"] == 5
    assert payload["booster"]["summary"]["rarity_slots"] == ["COMMON", "COMMON", "COMMON", "UNCOMMON", "UNCOMMON"]
    assert len(payload["booster"]["cards"]) == 5

    shop = client.get("/api/rebirth/shop").get_json()["shop"]
    assert "Boosters são grátis durante a beta Rebirth" in shop["disclaimer"]


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
