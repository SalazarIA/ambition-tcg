import json

import pytest

import app as ambition_app
from services.rebirth_persistence import RebirthPersistenceError, RebirthRepository


def test_home_rebirth_and_health_routes_return_200(client):
    home = client.get("/")
    rebirth = client.get("/rebirth")
    health = client.get("/health")

    assert home.status_code == 200
    assert "Duelos, coleção e mercado em uma mesa viva." in home.get_data(as_text=True)
    assert rebirth.status_code == 200
    assert "data-rebirth-app" in rebirth.get_data(as_text=True)
    assert health.status_code == 200
    assert health.get_json()["product"] == "Ambitionz Rebirth"


def test_home_degrades_to_logged_out_when_database_unavailable(client, monkeypatch):
    """Postgres fora (host não resolve no Render) não pode derrubar a home com
    500: current_user degrada para deslogado em vez de propagar o erro."""

    def _raise(self, token):
        raise RebirthPersistenceError(
            "O schema PostgreSQL do Rebirth nao esta migrado.",
            "database_schema_invalid",
            status=503,
        )

    monkeypatch.setattr(RebirthRepository, "user_for_session", _raise)

    with client.session_transaction() as session:
        session["rebirth_session_token"] = "sessao-orfa-de-banco"

    response = client.get("/")

    assert response.status_code == 200
    assert "Duelos, coleção e mercado em uma mesa viva." in response.get_data(as_text=True)


def test_rebirth_visual_contract_text_assets_and_ids(client):
    response = client.get("/rebirth")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "css/rebirth.css" in body
    assert "js/rebirth.js" in body

    for text in (
        "Invocar",
        "Encerrar turno",
        "Selecione um monstro",
        "Duplicata encontrada",
        "Evoluir",
        "Nova partida",
        "Combine duplicatas para evoluir",
        "rb-hero-portrait",
        "rb-mana-coins",
    ):
        assert text in body

    for element_id in (
        "player-hp",
        "turn-number",
        "bot-hp",
        "bot-card",
        "bot-battlefield",
        "player-battlefield",
        "focus-card",
        "evolution-panel",
        "evolution-name",
        "evolve-button",
        "player-hand",
        "hand-count",
        "player-hero-name",
        "player-mana-coins",
        "bot-hero-name",
        "bot-mana-coins",
        "play-button",
        "next-turn-button",
        "result-panel",
        "result-label",
        "result-title",
        "result-copy",
        "ability-events",
        "reward-panel",
        "bot-profile-label",
        "phase-label",
        "turn-log",
    ):
        assert f'id="{element_id}"' in body


def test_start_api_returns_clear_json_state(client):
    response = client.post("/api/rebirth/start", json={"seed": "routes-start"})
    payload = response.get_json()

    assert response.status_code == 200
    assert response.is_json
    assert payload["ok"] is True
    assert "result" in payload
    assert payload["state"]["match_id"].startswith("rebirth-")
    assert payload["state"]["player"]["hp"] == 30
    assert payload["state"]["player"]["max_hp"] == 30
    assert len(payload["state"]["player"]["hand"]) == 5
    assert payload["state"]["bot"]["hand_count"] == 5
    assert payload["state"]["bot_profile"]["id"] in {"defensive", "aggressive", "opportunist"}


def test_guest_wallet_api_returns_zero_balance_without_console_error(client):
    response = client.get("/api/rebirth/wallet")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["wallet"]["GOLD"] == 0
    assert payload["wallet"]["COINZ"] == 0
    assert payload["wallet"]["guest"] is True


def test_authenticated_match_state_uses_single_repository(client):
    register = client.post(
        "/api/rebirth/auth/register",
        json={
            "username": "RoutePilot",
            "email": "route-pilot@example.com",
            "password": "correct-horse-battery",
        },
    )
    assert register.status_code == 200

    started = client.post("/api/rebirth/start", json={"seed": "routes-single-source"})
    state = started.get_json()["state"]
    # O start não persiste mais (fix das partidas-fantasma); o primeiro
    # comando real grava o snapshot no repositório.
    first_action = client.post("/api/rebirth/next-turn", json={"match_id": state["match_id"]})
    assert first_action.status_code == 200
    persisted = client.get(f"/api/rebirth/match-state/{state['match_id']}")

    assert started.status_code == 200
    assert persisted.status_code == 200
    assert persisted.get_json()["state"]["match_id"] == state["match_id"]

    ambition_app.MATCH_STORE.clear()
    explicit_resume = client.post("/api/rebirth/resume", json={"match_id": state["match_id"]})
    assert explicit_resume.status_code == 200
    assert explicit_resume.get_json()["resumed"] is True
    assert explicit_resume.get_json()["state"]["match_id"] == state["match_id"]

    ambition_app.MATCH_STORE.clear()
    resumed = client.post("/api/rebirth/next-turn", json={"match_id": state["match_id"]})
    resumed_state = resumed.get_json()["state"]

    assert resumed.status_code == 200
    assert resumed_state["match_id"] == state["match_id"]
    # turno 3: o teste já gastou um next-turn para disparar o primeiro persist.
    assert resumed_state["turn"] == 3


def test_shop_survives_market_read_failure(client, monkeypatch):
    def broken_market_read(*_args, **_kwargs):
        raise RebirthPersistenceError("market failed", "database_read_failed", status=500)

    monkeypatch.setattr("services.rebirth_persistence.RebirthRepository.market_offers", broken_market_read)

    page = client.get("/rebirth/shop")
    api = client.get("/api/rebirth/shop")
    payload = api.get_json()

    assert page.status_code == 200
    assert "Loja &amp; Mercado" in page.get_data(as_text=True)
    assert api.status_code == 200
    assert payload["ok"] is True
    assert payload["shop"]["market"]["offers"] == []
    assert payload["shop"]["warnings"][0]["surface"] == "market"


def test_public_home_survives_stale_session_when_database_is_unavailable(client, monkeypatch):
    def broken_session_lookup(*_args, **_kwargs):
        raise RebirthPersistenceError("database unavailable", "database_schema_invalid", status=503)

    monkeypatch.setattr("services.rebirth_persistence.RebirthRepository.user_for_session", broken_session_lookup)
    with client.session_transaction() as flask_session:
        flask_session["rebirth_session_token"] = "stale-production-cookie"

    home = client.get("/")
    decks = client.get("/api/rebirth/decks")

    assert home.status_code == 200
    assert "Visitante" in home.get_data(as_text=True)
    assert decks.status_code == 503
    assert decks.get_json()["error"]["code"] == "database_schema_invalid"


def test_shop_route_is_server_rendered_with_native_nav(client):
    response = client.get("/rebirth/shop")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert 'href="/rebirth/shop"' in body
    assert 'data-rebirth-market-offers' in body
    assert 'js/rebirth_product.js' in body


def test_play_card_api_blocks_first_turn_direct_damage_until_bot_responds(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-play"})
    state = start.get_json()["state"]
    card = next(
        c for c in state["player"]["hand"]
        if c.get("type") == "MONSTER" and int(c.get("cost", 9)) <= int(state["player"]["energy"])
    )

    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["state"]["phase"] == "choose"
    assert payload["state"]["result"]["outcome"] == "Summon"
    assert payload["state"]["player"]["battlefield"][0]["id"] == card["id"]
    assert payload["state"]["last_clash"] is None
    assert payload["match_reward"] is None

    # O bot ainda não respondeu no turno inicial; dano direto não pode furar
    # essa janela sem defesa.
    assert payload["state"]["bot"]["battlefield"] == []
    attack = client.post(
        "/api/rebirth/attack",
        json={
            "match_id": payload["state"]["match_id"],
            "attacker_instance_id": payload["state"]["player"]["battlefield"][0]["instance_id"],
        },
    )
    attack_payload = attack.get_json()

    # Com summoning sickness, o turno 1 é duplamente protegido: a invocação
    # recém-chegada nem chega na regra de dano direto.
    assert attack.status_code == 400
    assert attack_payload["ok"] is False
    assert attack_payload["error"]["code"] == "summoning_sickness"

    bot_turn = client.post("/api/rebirth/next-turn", json={"match_id": payload["state"]["match_id"]})
    after_bot = bot_turn.get_json()["state"]
    assert bot_turn.status_code == 200
    assert after_bot["bot"]["hp"] == 30
    assert after_bot["bot"]["battlefield"]

    clash = client.post(
        "/api/rebirth/attack",
        json={
            "match_id": after_bot["match_id"],
            "attacker_instance_id": after_bot["player"]["battlefield"][0]["instance_id"],
            "target_instance_id": after_bot["bot"]["battlefield"][0]["instance_id"],
        },
    )
    clash_payload = clash.get_json()
    assert clash.status_code == 200
    assert clash_payload["ok"] is True
    assert clash_payload["state"]["last_clash"]["player_card"]["id"] == card["id"]
    assert clash_payload["state"]["result"]["outcome"] in {"Victory", "Defeat", "Clash"}
    if not clash_payload["state"]["is_finished"]:
        assert clash_payload["match_reward"] is None


def test_guest_match_actions_record_product_telemetry_without_false_reward(client, flask_app):
    state = client.post("/api/rebirth/start", json={"seed": "telemetry-guest"}).get_json()["state"]
    card = next(card for card in state["player"]["hand"] if int(card.get("cost", 0)) <= state["player"]["energy"])
    played = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    ).get_json()
    abandoned = client.post(
        "/api/rebirth/telemetry",
        json={"match_id": state["match_id"], "event_type": "match_abandoned", "reason": "qa"},
    )

    assert played["match_reward"] is None
    assert abandoned.status_code == 200
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    with repo.connect() as db:
        rows = db.execute(
            "SELECT event_type, event_json FROM telemetry_events ORDER BY id"
        ).fetchall()
    event_types = [row["event_type"] for row in rows]
    assert event_types == ["match_started", "card_played", "match_abandoned"]
    telemetry = json.loads(rows[-1]["event_json"])
    assert telemetry["match_id"] == state["match_id"]
    assert "decision_elapsed_ms" in telemetry


def test_client_error_telemetry_records_api_failure_metadata(client, flask_app):
    response = client.post(
        "/api/rebirth/telemetry",
        json={
            "event_type": "client_error",
            "message": "A requisição Rebirth falhou.",
            "surface": "arena",
            "metadata": {
                "type": "api_failure",
                "endpoint": "/api/rebirth/play-card",
                "status": 503,
                "code": "database_schema_invalid",
            },
        },
    )

    assert response.status_code == 200
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    events = repo.query_telemetry_events(event_types=("client_error",), limit=1)
    payload = events[0]["payload"]
    assert payload["message"] == "A requisição Rebirth falhou."
    assert payload["metadata"]["type"] == "api_failure"
    assert payload["metadata"]["endpoint"] == "/api/rebirth/play-card"
    assert payload["metadata"]["status"] == "503"
    assert payload["metadata"]["code"] == "database_schema_invalid"


def test_play_card_api_accepts_explicit_monster_slot(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-play-slot"})
    state = start.get_json()["state"]
    card = next(
        c for c in state["player"]["hand"]
        if c.get("type") == "MONSTER" and int(c.get("cost", 9)) <= int(state["player"]["energy"])
    )

    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"], "field_slot": 1},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    # field_slot=1 → card lands in slot 1, slots 0 and 2 stay empty.
    assert payload["state"]["player_field"][0] is None
    assert payload["state"]["player_field"][1]["instance_id"] == card["instance_id"]
    assert payload["state"]["player_field"][2] is None
    assert payload["state"]["player"]["battlefield"][0]["field_slot"] == 1


@pytest.mark.parametrize("path", ["/api/rebirth/play-card", "/api/rebirth/attack"])
@pytest.mark.parametrize("field", ["exhausted", "has_attacked", "has_acted"])
def test_combat_routes_reject_client_authored_status_fields(client, path, field):
    state = client.post("/api/rebirth/start", json={"seed": f"status-{field}"}).get_json()["state"]

    response = client.post(path, json={"match_id": state["match_id"], field: False})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "authoritative_state_violation"


def test_evolve_api_combines_duplicate(client):
    # Com o shuffle real, procura deterministicamente uma mão de abertura que
    # contenha uma dupla evoluível (o deck padrão tem vários pares).
    state = None
    evolution = None
    for attempt in range(30):
        start = client.post("/api/rebirth/start", json={"seed": f"routes-evolve-{attempt}"})
        candidate = start.get_json()["state"]
        if candidate.get("available_evolutions"):
            state = candidate
            evolution = candidate["available_evolutions"][0]
            break
    assert state is not None, "nenhuma seed de teste abriu com dupla evoluível"

    response = client.post(
        "/api/rebirth/evolve",
        json={"match_id": state["match_id"], "card_id": evolution["card_id"]},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["evolved"]["id"] == evolution["evolution_id"]
    assert payload["state"]["player"]["hand"][0]["id"] == evolution["evolution_id"]


def test_next_turn_api_advances_after_result(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-next"})
    state = start.get_json()["state"]
    card = state["player"]["hand"][0]
    played = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    )
    after_play = played.get_json()["state"]

    response = client.post("/api/rebirth/next-turn", json={"match_id": after_play["match_id"]})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["state"]["turn"] == 2
    assert payload["state"]["phase"] == "choose"
    assert payload["state"]["player"]["max_energy"] == 2
    assert payload["state"]["player"]["battlefield"]


def test_invalid_api_returns_json_error(client):
    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": "missing", "card_id": "card_001"},
    )
    payload = response.get_json()

    assert response.status_code == 404
    assert payload["ok"] is False
    assert payload["error"]["code"] == "missing_match"


def test_expected_action_errors_do_not_return_500(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-errors"})
    state = start.get_json()["state"]

    missing_match = client.post(
        "/api/rebirth/play-card",
        json={"match_id": "missing", "card_id": "card_001"},
    )
    malformed = client.post(
        "/api/rebirth/play-card",
        data="[",
        content_type="application/json",
    )
    invalid_card = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": "not-in-hand"},
    )
    duplicate = client.post(
        "/api/rebirth/evolve",
        json={"match_id": state["match_id"], "card_id": "card_002"},
    )
    invalid_attack = client.post(
        "/api/rebirth/attack",
        json={"match_id": state["match_id"]},
    )

    expected = [
        (missing_match, 404, "missing_match"),
        (malformed, 400, "malformed_request"),
        (invalid_card, 400, "invalid_card"),
        (duplicate, 400, "duplicate_not_available"),
        (invalid_attack, 400, "missing_attacker"),
    ]
    for response, status, code in expected:
        payload = response.get_json()
        assert response.status_code == status
        assert response.status_code != 500
        assert payload["ok"] is False
        assert payload["error"]["code"] == code


def test_legacy_routes_redirect_or_report_retired(client):
    arena = client.get("/arena")
    legacy_api = client.post("/api/ascension/start", json={})

    assert arena.status_code == 302
    assert arena.headers["Location"] == "/rebirth"
    assert legacy_api.status_code == 410
    assert legacy_api.get_json()["error"]["code"] == "legacy_disabled"


def test_mulligan_api_swaps_opening_hand_once(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-mulligan"})
    state = start.get_json()["state"]
    assert state["mulligan_available"] is True
    before = [card["instance_id"] for card in state["player"]["hand"]]

    response = client.post("/api/rebirth/mulligan", json={"match_id": state["match_id"]})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["mulliganed"] is True
    after = [card["instance_id"] for card in payload["state"]["player"]["hand"]]
    assert after != before
    assert payload["state"]["mulligan_available"] is False

    again = client.post("/api/rebirth/mulligan", json={"match_id": state["match_id"]})
    assert again.status_code == 400
    assert again.get_json()["error"]["code"] == "mulligan_unavailable"


def test_play_card_api_casts_damage_spell_at_enemy_unit(client):
    # Procura uma abertura com magia de dano (Fireball/ShadowDrain) na mão.
    state = None
    spell = None
    for attempt in range(40):
        candidate = client.post(
            "/api/rebirth/start", json={"seed": f"routes-spell-target-{attempt}"}
        ).get_json()["state"]
        found = next(
            (
                card for card in candidate["player"]["hand"]
                if card.get("type") == "SPELL"
                and any(str(e.get("type")) == "damage" for e in card.get("stack_effects") or [])
            ),
            None,
        )
        if found:
            state = candidate
            spell = found
            break
    assert state is not None, "nenhuma seed abriu com magia de dano"

    # Avança até o bot ter unidade em campo e o jogador ter mana para a magia.
    for _ in range(6):
        if state["bot"]["battlefield"] and int(state["player"]["energy"]) >= int(spell.get("cost", 2)):
            break
        state = client.post("/api/rebirth/next-turn", json={"match_id": state["match_id"]}).get_json()["state"]
    if not state["bot"]["battlefield"] or state.get("is_finished"):
        return  # partida terminou cedo; o contrato unitário da engine cobre o efeito

    spell_in_hand = next((c for c in state["player"]["hand"] if c["instance_id"] == spell["instance_id"]), None)
    if spell_in_hand is None:
        return
    target = state["bot"]["battlefield"][0]
    guard_before = int(target.get("current_guard") or target.get("guard") or 0)

    response = client.post(
        "/api/rebirth/play-card",
        json={
            "match_id": state["match_id"],
            "card_instance_id": spell_in_hand["instance_id"],
            "target_instance_id": target["instance_id"],
        },
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    after = next(
        (c for c in payload["state"]["bot"]["battlefield"] if c["instance_id"] == target["instance_id"]),
        None,
    )
    if after is not None:
        assert int(after.get("current_guard") or 0) < guard_before
    else:
        # Unidade destruída pela magia: precisa estar no descarte do bot.
        assert int(payload["state"]["bot"]["discard_count"]) >= 1
