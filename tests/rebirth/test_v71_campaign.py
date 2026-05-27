import app as ambition_app

from services.rebirth_campaign import CAMPAIGN_VERSION, campaign_payload, get_node, is_unlocked, next_available
from services.rebirth_domain import canonical_state_hash
from services.rebirth_engine import start_match
from services.rebirth_persistence import RebirthRepository
from services.rebirth_replay import build_replay_envelope, replay_match


def _register(client, username="campaign_user", email="campaign@example.com"):
    response = client.post(
        "/api/rebirth/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.get_json()


def test_campaign_payload_unlocks_nodes_in_sequence():
    initial = campaign_payload()

    assert initial["version"] == CAMPAIGN_VERSION
    assert len(initial["nodes"]) == 10
    assert initial["nodes"][0]["id"] == "node_01_acolyte"
    assert initial["nodes"][-1]["id"] == "node_10_gray_king"
    assert [node["status"] for node in initial["nodes"]] == ["available"] + ["locked"] * 9
    assert next_available()["id"] == "node_01_acolyte"

    progress = {
        "nodes": {
            "node_01_acolyte": {
                "attempts": 2,
                "completed_at": "2026-05-26T12:00:00+00:00",
            }
        }
    }
    unlocked = campaign_payload(progress)
    assert is_unlocked("node_02_guardian", progress) is True
    assert [node["status"] for node in unlocked["nodes"]] == ["completed", "available"] + ["locked"] * 8
    assert next_available(progress)["id"] == "node_02_guardian"


def test_campaign_initial_configuration_survives_replay_and_hashing():
    node = get_node("node_03_pyrelord")
    match = start_match(
        seed="campaign-replay",
        bot_profile_id=node["bot_profile_id"],
        bot_card_ids=node["bot_deck_override"],
        player_hp=node["player_hp"],
        bot_hp=node["bot_hp"],
        campaign_version=CAMPAIGN_VERSION,
        campaign_node=node["id"],
        campaign_attempt=4,
        campaign_modifiers=node["modifiers"],
        campaign_presentation=node["presentation"],
    )

    envelope = build_replay_envelope(match)
    replayed = replay_match(envelope)

    assert match["bot"]["hp"] == node["bot_hp"]
    assert match["campaign_node"] == node["id"]
    assert envelope["initial"]["campaign_node"] == node["id"]
    assert envelope["initial"]["bot_hp"] == node["bot_hp"]
    assert envelope["initial"]["campaign_modifiers"] == node["modifiers"]
    assert canonical_state_hash(replayed) == canonical_state_hash(match)


def test_campaign_api_validates_nodes_and_creates_distinct_attempts(client):
    _register(client)

    missing = client.post("/api/rebirth/campaign/start", json={"node_id": "missing"})
    invalid = client.post("/api/rebirth/campaign/start", json={})
    locked = client.post("/api/rebirth/campaign/start", json={"node_id": "node_02_guardian"})
    first = client.post("/api/rebirth/campaign/start", json={"node_id": "node_01_acolyte"}).get_json()
    second = client.post("/api/rebirth/campaign/start", json={"node_id": "node_01_acolyte"}).get_json()

    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "campaign_node_not_found"
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "invalid_campaign_payload"
    assert locked.status_code == 409
    assert locked.get_json()["error"]["code"] == "campaign_node_locked"
    assert first["state"]["campaign"]["attempt"] == 1
    assert second["state"]["campaign"]["attempt"] == 2
    assert first["state"]["match_id"] != second["state"]["match_id"]
    assert first["state"]["bot"]["hp"] == get_node("node_01_acolyte")["bot_hp"]
    assert first["state"]["first_duel"] is False


def test_campaign_sqlite_self_heal_is_idempotent_and_page_renders(client, flask_app):
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.ensure_schema()
    repo.ensure_schema()
    with repo.connect() as db:
        history_columns = {row["name"] for row in db.execute("PRAGMA table_info(match_history)").fetchall()}
        progress_table = db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'user_campaign_progress'"
        ).fetchone()

    page = client.get("/rebirth/campaign")
    assert {"campaign_version", "campaign_node", "campaign_attempt"} <= history_columns
    assert progress_table["name"] == "user_campaign_progress"
    assert page.status_code == 200
    assert "Campanha" in page.get_data(as_text=True)
    assert "node_01_acolyte" in page.get_data(as_text=True)


def test_campaign_victory_settles_once_unlocks_next_node_and_persists_after_login(client, flask_app):
    account = _register(client, username="campaign_winner", email="winner@example.com")
    user_id = account["account"]["user"]["id"]
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    before_xp = repo.progression(user_id)["xp"]

    started = client.post("/api/rebirth/campaign/start", json={"node_id": "node_01_acolyte"}).get_json()
    match = ambition_app.MATCH_STORE.get(started["state"]["match_id"])
    match["bot"]["statuses"] = {"burn": {"potency": 99, "turns": 1}}

    completed = client.post("/api/rebirth/next-turn", json={"match_id": match["match_id"]})
    payload = completed.get_json()
    progress = client.get("/api/rebirth/campaign").get_json()["campaign"]

    assert completed.status_code == 200
    assert payload["state"]["is_finished"] is True
    assert payload["state"]["winner"] == "player"
    assert payload["campaign_reward"]["applied"] is True
    assert payload["campaign_reward"]["xp"] == get_node("node_01_acolyte")["reward"]["xp"]
    assert [node["status"] for node in progress["nodes"]] == ["completed", "available"] + ["locked"] * 8
    assert repo.progression(user_id)["xp"] == before_xp + get_node("node_01_acolyte")["reward"]["xp"]

    repeated = repo.record_campaign_victory(
        user_id,
        "node_01_acolyte",
        get_node("node_01_acolyte")["reward"],
    )
    assert repeated["applied"] is False
    assert repo.progression(user_id)["xp"] == before_xp + get_node("node_01_acolyte")["reward"]["xp"]

    client.post("/api/rebirth/auth/logout", json={})
    logged_in = client.post(
        "/api/rebirth/auth/login",
        json={"email": "winner@example.com", "password": "password123"},
    )
    restored = client.get("/api/rebirth/campaign").get_json()["campaign"]
    assert logged_in.status_code == 200
    assert restored["nodes"][0]["status"] == "completed"
    assert restored["nodes"][1]["status"] == "available"
