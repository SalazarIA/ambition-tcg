"""Item 2: adversarial security suite (IDOR / CSRF / payload / economy).

Codex Fase 0 asks to *prove* there is no hidden P0 before opening the beta:
authorization of match state, payload abuse, and economy idempotency. These
tests drive the real HTTP surface as a hostile second actor.
"""
import app as ambition_app


def _register(client, username):
    resp = client.post(
        "/api/rebirth/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "password123"},
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def _first_playable_monster(state):
    energy = int(state["player"].get("energy") or state["player"].get("max_energy") or 1)
    for card in state["player"]["hand"]:
        if card["type"] == "MONSTER" and int(card.get("cost", 1) or 1) <= energy:
            return card
    return state["player"]["hand"][0]


# ---------------------------------------------------------------- IDOR (auth)

def test_user_cannot_act_on_another_users_match(flask_app):
    alice = flask_app.test_client()
    bob = flask_app.test_client()
    _register(alice, "alice_adv")
    _register(bob, "bob_adv")

    started = alice.post("/api/rebirth/start", json={"seed": "alice-adv"}).get_json()
    match_id = started["state"]["match_id"]
    instance = started["state"]["player"]["hand"][0]["instance_id"]

    # Bob tries to play a card into Alice's match.
    resp = bob.post(
        "/api/rebirth/play-card",
        json={"match_id": match_id, "card_instance_id": instance},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "match_forbidden"

    # …and to attack in it.
    resp_atk = bob.post(
        "/api/rebirth/attack",
        json={"match_id": match_id, "attacker_instance_id": instance},
    )
    assert resp_atk.status_code == 403
    assert resp_atk.get_json()["error"]["code"] == "match_forbidden"


def test_user_cannot_read_another_users_match_events(flask_app):
    alice = flask_app.test_client()
    bob = flask_app.test_client()
    _register(alice, "alice_read")
    _register(bob, "bob_read")

    started = alice.post("/api/rebirth/start", json={"seed": "alice-read"}).get_json()
    match_id = started["state"]["match_id"]
    monster = _first_playable_monster(started["state"])
    alice.post("/api/rebirth/play-card", json={"match_id": match_id, "card_instance_id": monster["instance_id"]})

    # Bob's history/events are scoped to Bob — Alice's match must not leak.
    # Secure outcome: empty scope OR a missing_match error, never Alice's events.
    events = bob.get(f"/api/rebirth/match-history/{match_id}/events").get_json()
    assert not events.get("events")  # None or [] — no leak
    if events.get("ok") is False:
        assert events["error"]["code"] == "missing_match"


# ---------------------------------------------------------------- IDOR (guest)

def test_guest_cannot_resume_another_guests_match(flask_app):
    guest_a = flask_app.test_client()
    guest_b = flask_app.test_client()
    started = guest_a.post("/api/rebirth/start", json={"seed": "guest-a"}).get_json()
    match_id = started["state"]["match_id"]

    resp = guest_b.post("/api/rebirth/resume", json={"match_id": match_id})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "match_forbidden"


# ---------------------------------------------------------------- CSRF

def test_mutation_requires_csrf_when_enabled(flask_app):
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = True
    try:
        client = flask_app.test_client()
        blocked = client.post("/api/rebirth/start", json={"seed": "no-csrf"})
        assert blocked.status_code == 403
        assert blocked.get_json()["error"]["code"] == "csrf_required"

        token = client.get("/api/rebirth/csrf").get_json()["csrf"]
        ok = client.post(
            "/api/rebirth/start", json={"seed": "with-csrf"}, headers={"X-Rebirth-CSRF": token}
        )
        assert ok.status_code == 200
    finally:
        flask_app.config["REBIRTH_REQUIRE_CSRF"] = False


# ---------------------------------------------------------------- payload abuse

def test_combat_payload_rejects_unexpected_field(client):
    started = client.post("/api/rebirth/start", json={"seed": "payload"}).get_json()
    match_id = started["state"]["match_id"]
    instance = started["state"]["player"]["hand"][0]["instance_id"]
    resp = client.post(
        "/api/rebirth/play-card",
        json={"match_id": match_id, "card_instance_id": instance, "winner": "player"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] in {"unexpected_combat_fields", "authoritative_state_violation"}


def test_combat_payload_rejects_authoritative_state(client):
    started = client.post("/api/rebirth/start", json={"seed": "authoritative"}).get_json()
    match_id = started["state"]["match_id"]
    instance = started["state"]["player"]["hand"][0]["instance_id"]
    resp = client.post(
        "/api/rebirth/play-card",
        json={"match_id": match_id, "card_instance_id": instance, "has_attacked": False},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] in {"authoritative_state_violation", "unexpected_combat_fields"}


# ---------------------------------------------------------------- economy

def test_daily_reward_locked_before_any_clash(client):
    _register(client, "econ_locked")
    resp = client.post("/api/rebirth/progression/claim-daily")
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "reward_locked"


def test_daily_reward_is_not_granted_twice(client):
    _register(client, "econ_idem")
    started = client.post("/api/rebirth/start", json={"seed": "econ-idem"}).get_json()
    state = started["state"]
    match_id = state["match_id"]
    monster = _first_playable_monster(state)
    client.post("/api/rebirth/play-card", json={"match_id": match_id, "card_instance_id": monster["instance_id"]})
    after_bot = client.post("/api/rebirth/next-turn", json={"match_id": match_id}).get_json()["state"]
    # Attack the bot's unit to resolve a clash (mirrors the journey e2e).
    client.post(
        "/api/rebirth/attack",
        json={
            "match_id": match_id,
            "attacker_instance_id": after_bot["player"]["battlefield"][0]["instance_id"],
            "target_instance_id": after_bot["bot"]["battlefield"][0]["instance_id"],
        },
    )

    first = client.post("/api/rebirth/progression/claim-daily")
    assert first.status_code == 200, first.get_json()
    xp_after_first = client.get("/api/rebirth/progression").get_json()["progression"]["profile"]["xp"]

    # Replay is rejected idempotently — no second grant.
    second = client.post("/api/rebirth/progression/claim-daily")
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] in {"reward_already_claimed", "transaction_replayed"}
    xp_after_second = client.get("/api/rebirth/progression").get_json()["progression"]["profile"]["xp"]
    assert xp_after_second == xp_after_first  # no double grant
