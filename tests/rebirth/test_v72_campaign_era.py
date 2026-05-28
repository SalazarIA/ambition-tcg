import json

import app as ambition_app

from services.rebirth_campaign import CAMPAIGN_VERSION, campaign_payload, get_node
from services.rebirth_domain import canonical_state_hash
from services.rebirth_engine import start_match
from services.rebirth_parity import DeterministicParityRunner
from services.rebirth_persistence import RebirthRepository
from services.rebirth_replay import build_replay_envelope, replay_match
from services.rebirth_serializers import public_state


def _register(client, username="era_user", email="era@example.com"):
    response = client.post(
        "/api/rebirth/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.get_json()["account"]["user"]["id"]


def test_v72_campaign_has_ten_bosses_with_visible_deterministic_rules():
    payload = campaign_payload()
    nodes = payload["nodes"]

    assert len(nodes) == 10
    assert nodes[-1]["id"] == "node_10_gray_king"
    assert nodes[-1]["presentation"]["intensity"] == "heavy"
    # audit #3: the boss now carries sustained tempo pressure (energy_ramp),
    # not just a longer HP bar. Accents fixed too (Mão).
    assert nodes[-1]["modifier_labels"] == [
        "Escudo inicial +4",
        "Mão inicial +2",
        "Mana inicial +1",
        "Tempo sustentado +2 mana/turno",
    ]


def test_v72_boss_modifiers_survive_replay_hash_and_parity():
    node = get_node("node_10_gray_king")
    match = start_match(
        seed="v72-gray-king",
        bot_profile_id=node["bot_profile_id"],
        bot_card_ids=node["bot_deck_override"],
        player_hp=node["player_hp"],
        bot_hp=node["bot_hp"],
        campaign_version=CAMPAIGN_VERSION,
        campaign_node=node["id"],
        campaign_attempt=1,
        campaign_modifiers=node["modifiers"],
        campaign_presentation=node["presentation"],
    )
    replayed = replay_match(build_replay_envelope(match))

    assert match["bot"]["statuses"]["shield"] == {"potency": 4, "turns": 2}
    assert len(match["bot"]["hand"]) == 7
    # audit #3: base 2 + opening_mana 1 + energy_ramp 2 = 5 (sustained tempo).
    assert match["bot"]["energy"] == 5
    assert match["bot"]["energy_ramp_bonus"] == 2
    assert canonical_state_hash(replayed) == canonical_state_hash(match)
    assert DeterministicParityRunner().verify(match)["ok"] is True


def test_v74_energy_ramp_is_sustained_across_turns():
    # audit #3: energy_ramp must add tempo EVERY turn, not just the opener,
    # so late bosses keep out-curving a competent player instead of merely
    # carrying a longer HP bar.
    from services.rebirth_engine import next_turn
    node = get_node("node_10_gray_king")
    match = start_match(
        seed="v74-ramp",
        bot_profile_id=node["bot_profile_id"],
        bot_card_ids=node["bot_deck_override"],
        player_hp=node["player_hp"],
        bot_hp=node["bot_hp"],
        campaign_version=CAMPAIGN_VERSION,
        campaign_node=node["id"],
        campaign_attempt=1,
        campaign_modifiers=node["modifiers"],
    )
    for _ in range(6):
        next_turn(match)
    # Bot keeps a +2 tempo edge mid-match (capped at 12).
    assert match["bot"]["max_energy"] > match["player"]["max_energy"]
    assert match["bot"]["max_energy"] - match["player"]["max_energy"] == 2


def test_v72_defeat_advice_is_only_public_after_campaign_loss():
    node = get_node("node_03_pyrelord")
    match = start_match(
        seed="v72-loss-advice",
        campaign_version=CAMPAIGN_VERSION,
        campaign_node=node["id"],
        campaign_advice={"tip": node["loss_tip"], "key_card": node["key_card"]},
    )

    assert "defeat_advice" not in public_state(match)["campaign"]
    match.update({"is_finished": True, "winner": "bot", "phase": "finished"})
    advice = public_state(match)["campaign"]["defeat_advice"]
    assert advice["tip"] == node["loss_tip"]
    assert advice["key_card"]["name"] == node["key_card"]["name"]


def test_v72_campaign_achievements_require_real_victory_state(client, flask_app):
    user_id = _register(client, username="boss_clearer", email="boss_clearer@example.com")
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    node = get_node("node_10_gray_king")
    repo.start_campaign_attempt(user_id, node["id"], CAMPAIGN_VERSION)

    unverified = repo.record_campaign_victory(user_id, node["id"], node["reward"], CAMPAIGN_VERSION)
    locked = {item["key"]: item["unlocked"] for item in unverified["achievements"]}
    assert locked["first_campaign_clear"] is False
    assert locked["no_damage_win"] is False

    second_user = _register(client, username="boss_clearer_two", email="boss_clearer_two@example.com")
    repo.start_campaign_attempt(second_user, node["id"], CAMPAIGN_VERSION)
    victory = start_match(seed="v72-achievements", campaign_node=node["id"], campaign_version=CAMPAIGN_VERSION)
    victory.update({"is_finished": True, "winner": "player", "phase": "finished"})
    rewarded = repo.record_campaign_victory(second_user, node["id"], node["reward"], CAMPAIGN_VERSION, match_state=victory)
    unlocked = {item["key"]: item["unlocked"] for item in rewarded["achievements"]}
    assert unlocked["first_campaign_clear"] is True
    assert unlocked["no_damage_win"] is True


def test_v72_campaign_telemetry_reports_retry_duration_turns_and_first_loss(client, flask_app):
    _register(client, username="metrics_win", email="metrics_win@example.com")
    client.post("/api/rebirth/campaign/start", json={"node_id": "node_01_acolyte"})
    started = client.post("/api/rebirth/campaign/start", json={"node_id": "node_01_acolyte"}).get_json()
    winning_match = ambition_app.MATCH_STORE.get(started["state"]["match_id"])
    winning_match["bot"]["statuses"] = {"burn": {"potency": 99, "turns": 1}}
    client.post("/api/rebirth/next-turn", json={"match_id": winning_match["match_id"]})

    client.post("/api/rebirth/auth/logout", json={})
    _register(client, username="metrics_loss", email="metrics_loss@example.com")
    losing = client.post("/api/rebirth/campaign/start", json={"node_id": "node_01_acolyte"}).get_json()
    losing_match = ambition_app.MATCH_STORE.get(losing["state"]["match_id"])
    losing_match["player"]["statuses"] = {"burn": {"potency": 99, "turns": 1}}
    loss_response = client.post("/api/rebirth/next-turn", json={"match_id": losing_match["match_id"]}).get_json()

    assert loss_response["state"]["campaign"]["defeat_advice"]["tip"]
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    with repo.connect() as db:
        rows = db.execute(
            "SELECT event_json FROM telemetry_events WHERE event_type = 'match_finished' ORDER BY id"
        ).fetchall()
    events = [json.loads(row["event_json"]) for row in rows]
    victory = next(event for event in events if event["winner"] == "player")
    defeat = next(event for event in events if event["winner"] == "bot")
    assert victory["node_retry_count"] == 1
    assert victory["victory_duration"] is not None
    assert victory["average_turns"] >= 1
    assert defeat["first_loss_node"] == "node_01_acolyte"
