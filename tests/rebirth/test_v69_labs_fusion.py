from copy import deepcopy

import app as ambition_app
from services.rebirth_cards import create_card_instance
from services.rebirth_dispatcher import FuseFieldPairCommand, SummonCardCommand, dispatch_command
from services.rebirth_domain import canonical_state_hash
from services.rebirth_engine import resolve_labs_fusion, start_match
from services.rebirth_persistence import RebirthRepository
from services.rebirth_reducers import reduce_events
from services.rebirth_replay import verify_replay
from services.rebirth_state import compact_battlefield


def _place_pair(match):
    first = create_card_instance("card_001", "player", 101)
    second = create_card_instance("card_001", "player", 102)
    for slot, card in enumerate((first, second)):
        card["field_slot"] = slot
        card["slot"] = slot + 1
        card["current_guard"] = int(card.get("guard", 0) or 0)
        card["max_guard"] = int(card.get("guard", 0) or 0)
        card["exhausted"] = False
        card["has_attacked"] = False
        card["has_acted"] = False
    match["player"]["field"] = [first, second, None]
    match["player"]["battlefield"] = [first, second]
    compact_battlefield(match["player"])
    return first, second


def _fuse(match, first, second):
    return resolve_labs_fusion(
        match,
        player_id="player",
        source_instance_a=first["instance_id"],
        source_instance_b=second["instance_id"],
    )


def test_labs_fusion_consumes_both_materials():
    match = start_match(seed="labs-fusion-consumes")
    first, second = _place_pair(match)

    _fuse(match, first, second)

    material_ids = {first["instance_id"], second["instance_id"]}
    field_ids = {card["instance_id"] for card in match["player"]["battlefield"]}
    discard_ids = {card["instance_id"] for card in match["player"]["discard"]}
    assert not material_ids.intersection(field_ids)
    assert material_ids.issubset(discard_ids)


def test_labs_fusion_spawns_evolved_creature_in_center_slot():
    match = start_match(seed="labs-fusion-spawns")
    first, second = _place_pair(match)

    fusion = _fuse(match, first, second)

    fused = match["player"]["field"][1]
    assert fused["id"] == "card_011"
    assert fused["instance_id"] == fusion["resulting_card"]["instance_id"]
    assert fused["field_slot"] == 1
    assert match["player"]["battlefield"] == [fused]


def test_labs_fusion_combines_attack_and_grants_breakthrough():
    match = start_match(seed="labs-fusion-breakthrough")
    first, second = _place_pair(match)

    _fuse(match, first, second)

    fused = match["player"]["battlefield"][0]
    assert fused["attack"] == first["attack"] + second["attack"]
    assert fused["power"] == fused["attack"]
    assert fused["breakthrough"] is True
    assert "BREAKTHROUGH" in fused["passives"]


def test_labs_fusion_emits_canonical_monsters_fused_event_safely():
    match = start_match(seed="labs-fusion-event")
    first, second = _place_pair(match)
    base = deepcopy(match)
    start_index = len(match["events"])

    _fuse(match, first, second)

    event = match["events"][-1]
    payload = event["payload"]
    assert event["type"] == "MONSTERS_FUSED"
    assert payload["material_instance_ids"] == [first["instance_id"], second["instance_id"]]
    assert payload["material_catalog_ids"] == ["card_001", "card_001"]
    assert payload["resulting_catalog_id"] == "card_011"
    assert payload["resulting_slot"] == 1
    assert payload["resulting_stats"]["attack"] == first["attack"] + second["attack"]
    assert event["canonical_state_hash"]

    replayed = reduce_events(base, match["events"][start_index:])
    assert canonical_state_hash(replayed) == canonical_state_hash(match)


def test_labs_fusion_dispatch_command_is_deterministically_replayable():
    match = start_match(seed="labs-fusion-replay", player_card_ids=["card_001"] * 30)
    first, second = match["player"]["hand"][:2]

    dispatch_command(match, SummonCardCommand(card_instance_id=first["instance_id"], field_slot=0))
    dispatch_command(match, SummonCardCommand(card_instance_id=second["instance_id"], field_slot=1))
    dispatch_command(
        match,
        FuseFieldPairCommand(
            player_id="player",
            source_instance_a=first["instance_id"],
            source_instance_b=second["instance_id"],
        ),
    )

    assert match["commands"][-1]["type"] == "FUSE_FIELD_PAIR"
    assert verify_replay(match)["ok"] is True


def test_labs_fusion_api_persists_authenticated_runtime_state(client, flask_app):
    flask_app.config["REBIRTH_LABS_ENABLED"] = True
    registered = client.post(
        "/api/rebirth/auth/register",
        json={"username": "fusion_owner", "email": "fusion-owner@example.com", "password": "password123"},
    ).get_json()
    user_id = registered["account"]["user"]["id"]
    state = client.post("/api/rebirth/start", json={"seed": "labs-fusion-persist"}).get_json()["state"]
    match = ambition_app.MATCH_STORE.get(state["match_id"])
    first, second = _place_pair(match)
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.upsert_match_history(user_id, match)

    fused = client.post(
        "/api/labs/fusion",
        json={
            "match_id": state["match_id"],
            "player_id": "player",
            "source_instance_a": first["instance_id"],
            "source_instance_b": second["instance_id"],
        },
    )
    assert fused.status_code == 200
    assert len(fused.get_json()["state"]["player"]["battlefield"]) == 1

    ambition_app.MATCH_STORE.clear()
    restored = repo.runtime_match_state(user_id, state["match_id"])
    assert restored["commands"][-1]["type"] == "FUSE_FIELD_PAIR"
    assert restored["events"][-1]["type"] == "MONSTERS_FUSED"
    assert len(restored["player"]["battlefield"]) == 1
