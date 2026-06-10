from services.rebirth_cards import get_card, validate_deck_distribution
from services.rebirth_persistence import RebirthRepository


def test_real_player_journey_register_start_play_and_next_turn(client, flask_app):
    register = client.post(
        "/api/rebirth/auth/register",
        json={
            "username": "player_test_aaa",
            "email": "player_test_aaa@example.com",
            "password": "password123",
        },
    )
    register_payload = register.get_json()

    assert register.status_code == 200
    assert register_payload["ok"] is True
    assert register_payload["account"]["authenticated"] is True
    assert register_payload["collection"]["summary"]["loadout_size"] == 30
    assert register_payload["wallet"]["COINZ"] >= 0
    user_id = register_payload["account"]["user"]["id"]

    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    collection_counts = repo.collection_counts(user_id)
    loadout_ids = repo.loadout_card_ids(user_id)

    assert sum(collection_counts.values()) == 30
    assert len(loadout_ids) == 30
    assert validate_deck_distribution(loadout_ids)
    assert {get_card(card_id)["rarity"] for card_id in collection_counts} <= {"COMMON", "UNCOMMON"}

    started = client.post("/api/rebirth/start", json={"seed": "player-test-aaa-e2e"})
    started_payload = started.get_json()

    assert started.status_code == 200
    assert started_payload["ok"] is True
    state = started_payload["state"]
    assert state["phase"] == "choose"
    assert state["turn_phase"] == "MAIN_PHASE"
    assert state["player"]["name"] == "player_test_aaa"
    assert len(state["player"]["hand"]) == 5
    assert state["bot"]["hand_count"] == 5

    energy = int(state["player"].get("energy", state["player"].get("max_energy", 1)) or 1)
    playable = next(
        card for card in state["player"]["hand"]
        if card["type"] == "MONSTER" and int(card.get("cost", 1) or 1) <= energy
    )
    played = client.post(
        "/api/rebirth/play-card",
        json={
            "match_id": state["match_id"],
            "card_instance_id": playable["instance_id"],
        },
    )
    played_payload = played.get_json()

    assert played.status_code == 200
    assert played_payload["ok"] is True
    after_play = played_payload["state"]
    assert after_play["phase"] == "choose"
    assert after_play["turn_phase"] == "MAIN_PHASE"
    assert after_play["result"]["outcome"] == "Summon"
    assert after_play["player"]["battlefield"][0]["id"] == playable["id"]
    assert {"CARD_PLAYED", "MONSTER_SUMMONED"}.issubset({event["type"] for event in after_play["events"]})
    assert played_payload["match_reward"] is None

    blocked = client.post(
        "/api/rebirth/attack",
        json={
            "match_id": after_play["match_id"],
            "attacker_instance_id": after_play["player"]["battlefield"][0]["instance_id"],
        },
    )
    # Sickness protege o turno 1 antes mesmo da regra de dano direto.
    assert blocked.status_code == 400
    assert blocked.get_json()["error"]["code"] == "summoning_sickness"

    bot_turn = client.post("/api/rebirth/next-turn", json={"match_id": after_play["match_id"]})
    after_bot_turn = bot_turn.get_json()["state"]
    assert bot_turn.status_code == 200
    assert after_bot_turn["turn"] == 2
    assert after_bot_turn["bot"]["hp"] == 30
    assert after_bot_turn["bot"]["battlefield"]

    attack_payload_json = {
        "match_id": after_bot_turn["match_id"],
        "attacker_instance_id": after_bot_turn["player"]["battlefield"][0]["instance_id"],
        "target_instance_id": after_bot_turn["bot"]["battlefield"][0]["instance_id"],
    }
    attacked = client.post("/api/rebirth/attack", json=attack_payload_json)
    attacked_payload = attacked.get_json()

    assert attacked.status_code == 200
    assert attacked_payload["ok"] is True
    after_attack = attacked_payload["state"]
    assert after_attack["phase"] in {"result", "finished"}
    assert after_attack["turn_phase"] in {"END_PHASE", "COMBAT_PHASE"}
    assert after_attack["last_clash"]["player_card"]["id"] == playable["id"]
    assert after_attack["result"]["outcome"] in {"Victory", "Defeat", "Clash"}
    assert any(event["type"] == "CLASH_RESOLVED" for event in after_attack["events"])
    assert attacked_payload["match_reward"]["persisted"] is True

    next_turn = client.post("/api/rebirth/next-turn", json={"match_id": after_attack["match_id"]})
    next_turn_payload = next_turn.get_json()

    assert next_turn.status_code == 200
    assert next_turn_payload["ok"] is True
    after_next = next_turn_payload["state"]
    assert after_next["turn"] == 3
    assert after_next["phase"] == "choose"
    assert after_next["turn_phase"] == "MAIN_PHASE"
    assert after_next["player"]["played_card"] is None
    assert after_next["player"]["max_energy"] == 3
    assert after_next["player"]["battlefield"] or after_next["player"]["discard_count"] >= 1
    assert len(after_next["player"]["hand"]) == 5
    assert after_next["bot"]["hand_count"] <= 5
    assert after_next["bot"]["battlefield"]
    assert any(event["type"] == "TURN_STARTED" for event in after_next["events"])
