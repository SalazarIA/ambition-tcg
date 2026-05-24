import pytest

from services.rebirth_cards import CARD_CATALOG, get_card
from services.rebirth_persistence import RebirthPersistenceError, RebirthRepository


def register(client, username="persist_user", email="persist@example.com"):
    return client.post(
        "/api/rebirth/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )


def summon_and_attack(client, state, card=None):
    if card is None:
        energy = int(state["player"].get("energy", state["player"].get("max_energy", 1)) or 1)
        card = next(
            (c for c in state["player"]["hand"] if int(c.get("cost", 1) or 1) <= energy),
            state["player"]["hand"][0],
        )
    summoned = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    )
    assert summoned.status_code == 200
    after_summon = summoned.get_json()["state"]
    if not after_summon["bot"]["battlefield"]:
        after_summon = client.post(
            "/api/rebirth/next-turn",
            json={"match_id": after_summon["match_id"]},
        ).get_json()["state"]
    attack_payload = {
        "match_id": after_summon["match_id"],
        "attacker_instance_id": after_summon["player"]["battlefield"][-1]["instance_id"],
    }
    if after_summon["bot"]["battlefield"]:
        attack_payload["target_instance_id"] = after_summon["bot"]["battlefield"][0]["instance_id"]
    return client.post("/api/rebirth/attack", json=attack_payload)


def test_register_login_logout_and_session_are_persisted(client, flask_app):
    created = register(client)
    payload = created.get_json()

    assert created.status_code == 200
    assert payload["account"]["authenticated"] is True
    assert payload["account"]["user"]["username"] == "persist_user"
    assert payload["wallet"]["COINZ"] >= 0
    assert payload["collection"]["summary"]["loadout_size"] == 30

    db_user = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"]).get_user(payload["account"]["user"]["id"])
    assert db_user["email"] == "persist@example.com"

    session_response = client.get("/api/rebirth/session")
    assert session_response.get_json()["account"]["authenticated"] is True

    logout = client.post("/api/rebirth/auth/logout", json={})
    assert logout.status_code == 200
    assert logout.get_json()["account"]["authenticated"] is False

    login = client.post("/api/rebirth/auth/login", json={"email": "persist@example.com", "password": "password123"})
    assert login.status_code == 200
    assert login.get_json()["account"]["user"]["username"] == "persist_user"
    assert login.get_json()["collection"]["summary"]["loadout_size"] == 30


def test_duplicate_account_and_bad_login_return_stable_errors(client):
    register(client, username="dupe_user", email="dupe@example.com")
    duplicate = register(client, username="dupe_user", email="dupe@example.com")
    bad_login = client.post("/api/rebirth/auth/login", json={"email": "dupe@example.com", "password": "wrong"})

    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "auth_conflict"
    assert bad_login.status_code == 401
    assert bad_login.get_json()["error"]["code"] == "invalid_credentials"


def test_loadout_persists_and_start_match_uses_account_loadout(client):
    register(client, username="deck_user", email="deck@example.com")
    card_ids = [card["id"] for card in client.get("/api/rebirth/collection").get_json()["collection"]["loadout"]]

    saved = client.post("/api/rebirth/loadout", json={"card_ids": card_ids})
    assert saved.status_code == 200
    assert saved.get_json()["loadout"]["summary"]["size"] == 30

    start = client.post("/api/rebirth/start", json={"seed": "account-loadout"})
    state = start.get_json()["state"]
    visible_ids = [card["id"] for card in state["player"]["hand"]]

    assert state["player"]["name"] == "deck_user"
    assert visible_ids == card_ids[:5]


def test_booster_mutates_collection_and_progression(client):
    register(client, username="owner_user", email="owner@example.com")
    before = client.get("/api/rebirth/collection").get_json()["collection"]["summary"]["owned_cards"]

    opened = client.post("/api/rebirth/booster/open", json={"seed": "ownership"})
    payload = opened.get_json()
    after = client.get("/api/rebirth/collection").get_json()["collection"]["summary"]["owned_cards"]
    progress = client.get("/api/rebirth/progression").get_json()["progression"]["profile"]

    assert opened.status_code == 200
    assert payload["booster"]["summary"]["count"] == 5
    assert after == before + 5
    assert progress["boosters_opened"] == 1
    assert progress["xp"] >= 40


def test_legacy_booster_history_card_ids_do_not_break_product_pages(client, flask_app):
    user = register(client, username="legacy_booster_user", email="legacy-booster@example.com").get_json()["account"]["user"]
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.ensure_schema()
    with repo.connect() as db:
        db.execute(
            """
            INSERT INTO booster_history (user_id, booster_id, seed, cards_json, opened_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user["id"], "legacy_pack", "legacy", '["voidstalker", "card_001"]', "2026-05-21T00:00:00"),
        )

    history = repo.booster_history(user["id"])
    shop = client.get("/rebirth/shop")
    profile = client.get("/rebirth/profile")

    assert history[0]["invalid_card_ids"] == ["voidstalker"]
    assert [card["id"] for card in history[0]["cards"]] == ["card_001"]
    assert shop.status_code == 200
    assert profile.status_code == 200


def test_market_listing_locks_card_and_purchase_transfers_value(client, flask_app):
    seller = register(client, username="seller_user", email="seller@example.com").get_json()["account"]["user"]
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    seller_loadout = repo.loadout_card_ids(seller["id"])
    extra_card_id = next(card["id"] for card in CARD_CATALOG if card["id"] not in set(seller_loadout))
    repo.add_cards(seller["id"], [get_card(extra_card_id)])

    listed = client.post(
        "/api/rebirth/market/list",
        json={"card_id": extra_card_id, "price": 100, "currency_type": "GOLD"},
    )
    listed_payload = listed.get_json()

    assert listed.status_code == 200
    assert listed_payload["market"]["offer"]["card_id"] == extra_card_id
    assert repo.collection_counts(seller["id"]).get(extra_card_id, 0) == 0

    double_list = client.post(
        "/api/rebirth/market/list",
        json={"card_id": extra_card_id, "price": 100, "currency_type": "GOLD"},
    )
    assert double_list.status_code == 409
    assert double_list.get_json()["error"]["code"] == "card_not_available"

    client.post("/api/rebirth/auth/logout", json={})
    buyer = register(client, username="buyer_user", email="buyer@example.com").get_json()["account"]["user"]
    market = client.get("/api/rebirth/market/offers").get_json()["market"]["offers"]
    assert any(offer["id"] == listed_payload["market"]["offer"]["id"] for offer in market)

    bought = client.post("/api/rebirth/market/buy", json={"offer_id": listed_payload["market"]["offer"]["id"]})
    bought_payload = bought.get_json()

    assert bought.status_code == 200
    assert bought_payload["market"]["purchase"]["fee"] == 5
    assert bought_payload["market"]["purchase"]["seller_net"] == 95
    assert bought_payload["market"]["purchase"]["buyer_balance"] == 900
    assert bought_payload["wallet"]["GOLD"] == 900
    assert repo.get_user_balance(buyer["id"], "GOLD") == 900
    assert repo.get_user_balance(seller["id"], "GOLD") == 1095
    assert repo.collection_counts(buyer["id"])[extra_card_id] >= 1
    assert all(offer["id"] != listed_payload["market"]["offer"]["id"] for offer in bought_payload["market"]["offers"])

    repeated = client.post("/api/rebirth/market/buy", json={"offer_id": listed_payload["market"]["offer"]["id"]})
    assert repeated.status_code == 409
    assert repeated.get_json()["error"]["code"] == "market_offer_unavailable"

    ledger = repo.economy_ledger(seller["id"], limit=20)
    assert any(entry["reason"] == "market_fee_sink" and entry["delta"] == -5 for entry in ledger)
    with repo.connect() as db:
        wallet_rows = db.execute(
            """
            SELECT user_id, currency, entry_type, amount, source
            FROM wallet_ledger
            WHERE reference_id = ?
            ORDER BY entry_type, amount
            """,
            (listed_payload["market"]["offer"]["id"],),
        ).fetchall()
    assert {row["source"] for row in wallet_rows} == {"MARKET_SALE"}
    assert sum(row["amount"] if row["entry_type"] == "CREDIT" else -row["amount"] for row in wallet_rows) == -5


def test_market_listing_rejects_card_required_by_active_loadout(client, flask_app):
    created = register(client, username="locked_seller", email="locked-seller@example.com").get_json()["account"]["user"]
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    locked_card_id = repo.loadout_card_ids(created["id"])[0]

    response = client.post(
        "/api/rebirth/market/list",
        json={"card_id": locked_card_id, "price": 50, "currency_type": "GOLD"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "card_locked_by_loadout"


def test_match_progression_daily_reward_and_tutorial_are_persisted(client):
    register(client, username="reward_user", email="reward@example.com")
    start = client.post("/api/rebirth/start", json={"seed": "reward-match"}).get_json()["state"]
    played = summon_and_attack(client, start)

    assert played.status_code == 200
    assert played.get_json()["progression"]["clashes"] == 1
    reward = played.get_json()["match_reward"]
    assert reward["persisted"] is True
    assert reward["xp"] >= 25
    assert reward["daily"]["ready"] is True
    assert {"key": "first_clash", "name": "Primeiro Clash"} in reward["achievements"]

    daily = client.post("/api/rebirth/progression/claim-daily", json={})
    tutorial = client.post("/api/rebirth/onboarding/complete", json={"step": 4})
    profile = client.get("/api/rebirth/progression").get_json()["progression"]["profile"]

    assert daily.status_code == 200
    assert daily.get_json()["claim"]["xp"] == 25
    assert tutorial.status_code == 200
    assert tutorial.get_json()["tutorial"]["progression"]["tutorial_complete"] is True
    assert profile["tutorial_complete"] is True
    assert profile["clashes"] == 1


def test_profile_achievements_follow_rebirth_actions(client):
    register(client, username="badge_user", email="badge@example.com")
    profile = client.get("/api/rebirth/profile").get_json()["profile"]["profile"]
    achievements = {item["key"]: item for item in profile["achievements"]}

    assert achievements["founder"]["unlocked"] is True
    assert profile["unlocked_achievements"] == 1

    opened = client.post("/api/rebirth/booster/open", json={"seed": "badge-booster"})
    start = client.post("/api/rebirth/start", json={"seed": "badge-match"}).get_json()["state"]
    played = summon_and_attack(client, start)
    daily = client.post("/api/rebirth/progression/claim-daily", json={})
    tutorial = client.post("/api/rebirth/onboarding/complete", json={"step": 4})

    assert opened.status_code == 200
    assert played.status_code == 200
    assert daily.status_code == 200
    assert tutorial.status_code == 200

    profile = client.get("/api/rebirth/profile").get_json()["profile"]["profile"]
    achievements = {item["key"]: item for item in profile["achievements"]}

    assert achievements["first_booster"]["unlocked"] is True
    assert achievements["first_clash"]["unlocked"] is True
    assert achievements["daily_claimed"]["unlocked"] is True
    assert achievements["tutorial_complete"]["unlocked"] is True
    assert profile["unlocked_achievements"] >= 5


def test_tutorial_reward_is_idempotent_and_cannot_farm_xp(client):
    register(client, username="tutorial_once", email="tutorial-once@example.com")

    first = client.post("/api/rebirth/onboarding/complete", json={"step": 4}).get_json()["tutorial"]
    repeated = client.post("/api/rebirth/onboarding/complete", json={"step": 4}).get_json()["tutorial"]

    assert first["xp"] == 60
    assert first["already_claimed"] is False
    assert repeated["xp"] == 0
    assert repeated["already_claimed"] is True
    assert repeated["progression"]["xp"] == first["progression"]["xp"]


def test_replayed_clash_state_cannot_duplicate_xp_or_transaction(client, flask_app):
    registered = register(client, username="clash_once", email="clash-once@example.com").get_json()
    user_id = registered["account"]["user"]["id"]
    start = client.post("/api/rebirth/start", json={"seed": "clash-replay"}).get_json()["state"]
    first = summon_and_attack(client, start).get_json()
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])

    xp_after_first = first["progression"]["xp"]
    with pytest.raises(RebirthPersistenceError) as error:
        repo.record_clash_result(user_id, first["state"])
    with repo.connect() as db:
        transactions = db.execute(
            "SELECT COUNT(*) AS amount FROM economy_transactions WHERE user_id = ? AND transaction_type = 'MATCH_CLASH'",
            (user_id,),
        ).fetchone()["amount"]
    progression = repo.progression(user_id)

    assert error.value.code == "transaction_replayed"
    assert progression["xp"] == xp_after_first
    assert progression["clashes"] == 1
    assert transactions == 1


def test_duplicate_economy_claim_rolls_back_the_transaction(client, flask_app):
    user_id = register(client, username="atomic_once", email="atomic-once@example.com").get_json()["account"]["user"]["id"]
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    key = "atomic-test-key"

    with repo.connect() as db:
        repo._claim_economy_idempotency(db, user_id, key=key, scope="XP", reference_id="first")
    original_xp = repo.progression(user_id)["xp"]

    with pytest.raises(RebirthPersistenceError) as error:
        with repo.connect() as db:
            db.execute("UPDATE user_progress SET xp = xp + 999 WHERE user_id = ?", (user_id,))
            repo._claim_economy_idempotency(db, user_id, key=key, scope="XP", reference_id="duplicate")

    assert error.value.code == "transaction_replayed"
    assert repo.progression(user_id)["xp"] == original_xp


def test_coinz_receipt_credit_is_disabled_until_official_store_validation(client):
    register(client, username="no_purchase", email="no-purchase@example.com")

    response = client.post(
        "/api/rebirth/shop/verify-receipt",
        json={"platform": "google_play", "product_id": "coins_1200", "receipt": "simulated-forged"},
    )

    assert response.status_code == 410
    assert response.get_json()["error"]["code"] == "monetization_disabled"
    assert client.get("/api/rebirth/wallet").get_json()["wallet"]["COINZ"] == 0


def test_balance_simulation_is_capped_and_deterministic(client):
    response = client.get("/api/rebirth/balance/simulate?matches=500")
    payload = response.get_json()["balance"]

    assert response.status_code == 200
    assert payload["matches"] == 200
    assert payload["summary"]["average_turns"] > 0
    assert payload["bot_tuning"]["policy"].startswith("alterna perfis defensivo")
    assert {item["profile_id"] for item in payload["profile_results"]} == {"defensive", "aggressive", "opportunist"}
    assert payload["card_stats"][0]["ability_key"]
    assert payload["ability_stats"][0]["plays"] > 0
