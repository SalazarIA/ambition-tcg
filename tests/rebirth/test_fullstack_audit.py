from collections import Counter

import app as ambition_app
import services.rebirth_engine as rebirth_engine
from services.rebirth_cards import create_card_instance, get_card, validate_deck_distribution
from services.rebirth_persistence import RebirthRepository
from services.rebirth_state import TurnPhase, field_slots, set_turn_phase


def _rows(repo, query, params=()):
    with repo.connect() as db:
        return [dict(row) for row in db.execute(query, params).fetchall()]


def _one(repo, query, params=()):
    with repo.connect() as db:
        row = db.execute(query, params).fetchone()
        return dict(row) if row else None


def test_rebirth_fullstack_audit_register_booster_bot_arena_and_ledger(client, flask_app, monkeypatch):
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])

    registered = client.post(
        "/api/rebirth/auth/register",
        json={
            "username": "audit_rebirth",
            "email": "audit_rebirth@example.com",
            "password": "password123",
        },
    )
    register_payload = registered.get_json()

    assert registered.status_code == 200
    assert register_payload["ok"] is True
    assert register_payload["account"]["authenticated"] is True
    assert register_payload["account"]["user"]["username"] == "audit_rebirth"
    assert register_payload["wallet"]["GOLD"] == 1000
    assert register_payload["collection"]["summary"]["loadout_size"] == 30

    user_id = register_payload["account"]["user"]["id"]
    with client.session_transaction() as session:
        assert session["rebirth_user_id"] == user_id
        assert session["rebirth_csrf_token"] == register_payload["csrf"]

    db_user = repo.get_user(user_id)
    collection_counts = repo.collection_counts(user_id)
    loadout_ids = repo.loadout_card_ids(user_id)
    starter_rarities = {get_card(card_id)["rarity"] for card_id in collection_counts}
    starter_ledger = repo.economy_ledger(user_id, limit=100)
    starter_transactions = _rows(repo, "SELECT * FROM economy_transactions WHERE user_id = ?", (user_id,))

    assert db_user["email"] == "audit_rebirth@example.com"
    assert sum(collection_counts.values()) == 30
    assert len(loadout_ids) == 30
    assert validate_deck_distribution(loadout_ids)
    assert starter_rarities <= {"COMMON", "UNCOMMON"}
    assert {"starter_collection", "starter_wallet"}.issubset({entry["reason"] for entry in starter_ledger})
    assert any(row["transaction_type"] == "STARTER_WALLET" and row["currency"] == "GOLD" for row in starter_transactions)

    booster = client.post("/api/rebirth/booster/open", json={"seed": "fullstack-audit-booster"})
    booster_payload = booster.get_json()
    booster_cards = booster_payload["booster"]["cards"]
    booster_rarities = Counter(card["rarity"] for card in booster_cards)

    assert booster.status_code == 200
    assert booster_payload["booster"]["summary"]["count"] == 5
    assert booster_rarities == {"COMMON": 3, "UNCOMMON": 2}
    assert booster_payload["booster"]["summary"]["rarity_slots"] == ["COMMON", "COMMON", "COMMON", "UNCOMMON", "UNCOMMON"]
    assert repo.progression(user_id)["boosters_opened"] == 1
    assert _one(repo, "SELECT COUNT(*) AS amount FROM booster_history WHERE user_id = ?", (user_id,))["amount"] == 1
    assert any(
        row["transaction_type"] == "BOOSTER_OPENED" and row["amount"] == 40 and row["currency"] == "XP"
        for row in _rows(repo, "SELECT * FROM economy_transactions WHERE user_id = ?", (user_id,))
    )

    started = client.post("/api/rebirth/start", json={"seed": "fullstack-audit-match"})
    start_payload = started.get_json()

    assert started.status_code == 200
    assert start_payload["ok"] is True
    state = start_payload["state"]
    assert state["phase"] == "choose"
    assert state["player"]["name"] == "audit_rebirth"
    assert len(state["player_field"]) == 1
    assert len(state["bot_field"]) == 1

    match = ambition_app.MATCH_STORE.get(state["match_id"])
    player_card = create_card_instance("card_009", "player", 1)
    bot_cards = [
        create_card_instance("card_041", "bot", 1),
        create_card_instance("card_061", "bot", 2),
        create_card_instance("card_021", "bot", 3),
    ]
    match["player"]["hand"] = [player_card]
    match["player"]["energy"] = max(1, int(player_card.get("cost", 1) or 1))
    match["player"]["max_energy"] = match["player"]["energy"]
    match["bot"]["hand"] = bot_cards
    match["bot"]["energy"] = max(1, max(int(c.get("cost", 1) or 1) for c in bot_cards))
    match["bot"]["max_energy"] = match["bot"]["energy"]
    match["bot_profile"] = {
        "id": "aggressive",
        "name": "Aggressive Bot",
        "copy": "Audit profile",
        "policy": "choose through services.rebirth_bot",
    }

    bot_decisions = []
    original_choose_response = rebirth_engine.choose_response

    def tracked_choose_response(bot_hand, chosen_player_card, profile_id=None, **context):
        decision = original_choose_response(bot_hand, chosen_player_card, profile_id=profile_id, **context)
        bot_decisions.append(
            {
                "profile_id": profile_id,
                "player_card_id": chosen_player_card["id"],
                "decision_card_id": decision["id"],
                "match_id": context.get("match_id"),
            }
        )
        return decision

    monkeypatch.setattr(rebirth_engine, "choose_response", tracked_choose_response)

    summoned = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": player_card["instance_id"]},
    )
    summon_payload = summoned.get_json()
    after_summon = summon_payload["state"]

    assert summoned.status_code == 200
    assert after_summon["player"]["battlefield"][0]["id"] == "card_009"
    assert after_summon["bot"]["battlefield"][0]["id"] == bot_decisions[0]["decision_card_id"]
    assert bot_decisions == [
        {
            "profile_id": "aggressive",
            "player_card_id": "card_009",
            "decision_card_id": after_summon["bot"]["battlefield"][0]["id"],
            "match_id": state["match_id"],
        }
    ]
    assert any(event["type"] == "BOT_DECISION" for event in after_summon["events"])
    assert summon_payload["match_reward"]["persisted"] is False

    attacked = client.post(
        "/api/rebirth/attack",
        json={
            "match_id": state["match_id"],
            "attacker_instance_id": after_summon["player"]["battlefield"][0]["instance_id"],
            "target_instance_id": after_summon["bot"]["battlefield"][0]["instance_id"],
        },
    )
    attack_payload = attacked.get_json()
    after_attack = attack_payload["state"]

    assert attacked.status_code == 200
    assert after_attack["phase"] in {"result", "finished"}
    assert after_attack["last_clash"]["player_card"]["id"] == "card_009"
    assert after_attack["last_clash"]["bot_card"]["id"] == bot_decisions[0]["decision_card_id"]
    assert attack_payload["match_reward"]["persisted"] is True
    assert repo.progression(user_id)["clashes"] >= 1

    live_match = ambition_app.MATCH_STORE.get(state["match_id"])
    live_match["bot"]["hp"] = 1
    live_match["bot"]["hand"] = []
    live_match["bot"]["deck"] = []
    live_match["bot"]["battlefield"] = []
    live_match["bot"]["field"] = [None]
    attacker = live_match["player"]["battlefield"][0]
    attacker["exhausted"] = False
    attacker["has_attacked"] = False
    field_slots(live_match["player"])
    live_match["phase"] = "choose"
    set_turn_phase(live_match, TurnPhase.MAIN_PHASE)

    finished = client.post(
        "/api/rebirth/attack",
        json={"match_id": state["match_id"], "attacker_instance_id": attacker["instance_id"]},
    )
    finished_payload = finished.get_json()
    final_state = finished_payload["state"]

    assert finished.status_code == 200
    assert final_state["is_finished"] is True
    assert final_state["winner"] == "player"
    assert finished_payload["match_reward"]["persisted"] is True

    final_progress = repo.progression(user_id)
    match_history = repo.match_history(user_id, limit=1)[0]
    match_events = repo.match_events(user_id, state["match_id"], limit=50)
    audit_ledger = repo.economy_ledger(user_id, limit=100)
    transactions = _rows(
        repo,
        """
        SELECT transaction_type, amount, currency, reference_id
        FROM economy_transactions
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (user_id,),
    )

    assert final_progress["xp"] >= 40 + 25 + 100
    assert final_progress["level"] == 1
    assert match_history["match_id"] == state["match_id"]
    assert match_history["status"] == "finished"
    assert match_history["winner"] == "player"
    assert {"BOT_DECISION", "CLASH_RESOLVED", "MATCH_FINISHED"}.issubset({event["type"] for event in match_events})
    assert any(entry["reason"] == "match_clash" and entry["reference_id"] == state["match_id"] for entry in audit_ledger)
    assert any(row["transaction_type"] == "MATCH_CLASH" and row["reference_id"] == state["match_id"] for row in transactions)
