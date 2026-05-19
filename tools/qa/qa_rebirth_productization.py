#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'ambition_rebirth_productization.db'}")
os.environ.setdefault("SECRET_KEY", "qa-secret-key")
os.environ.setdefault("WTF_CSRF_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "testing")

from app import app  # noqa: E402


def assert_ok(response):
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.is_json
    payload = response.get_json()
    assert payload["ok"] is True, payload
    return payload


def play_round(client, state, intent="STRIKE"):
    match_id = state["match_id"]
    if not state["player"]["active_card"] and state["hand"]:
        state = assert_ok(client.post("/api/rebirth/play-card", json={"match_id": match_id, "card_id": state["hand"][0]["id"]}))["state"]
    state = assert_ok(client.post("/api/rebirth/intent", json={"match_id": match_id, "intent": intent}))["state"]
    state = assert_ok(client.post("/api/rebirth/resolve", json={"match_id": match_id}))["state"]
    return state


def main():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    home = client.get("/")
    assert home.status_code == 200
    assert "Ambitionz Rebirth" in home.get_data(as_text=True)
    assert 'href="/rebirth"' in home.get_data(as_text=True)

    rebirth = client.get("/rebirth")
    assert rebirth.status_code == 200
    assert "rb-deck-selector" in rebirth.get_data(as_text=True)

    decks_payload = assert_ok(client.get("/api/rebirth/decks"))
    deck_ids = [deck["id"] for deck in decks_payload["decks"]]
    assert deck_ids == ["ember_oath", "deepguard", "null_circuit"]

    for deck_id in deck_ids:
        state = assert_ok(client.get(f"/api/rebirth/new?seed=qa-{deck_id}&deck_id={deck_id}"))["state"]
        assert state["selected_deck_id"] == deck_id
        assert state["hand"]

    for difficulty in ["easy", "normal", "hard"]:
        state = assert_ok(client.get(f"/api/rebirth/new?seed=qa-{difficulty}&difficulty={difficulty}"))["state"]
        assert state["difficulty"] == difficulty
        assert state["opponent_profile"]

    state = assert_ok(client.get("/api/rebirth/new?seed=qa-finish&deck_id=ember_oath&difficulty=normal"))["state"]
    for index in range(20):
        if state["is_finished"]:
            break
        state = play_round(client, state, ["STRIKE", "FOCUS", "GUARD"][index % 3])

    assert state["is_finished"], "Rebirth match did not finish within 20 rounds"
    assert state["match_summary"], "Finished match missing summary"
    assert state["reward_preview"], "Finished match missing reward preview"

    print("REBIRTH_PRODUCTIZATION_OK")


if __name__ == "__main__":
    main()
