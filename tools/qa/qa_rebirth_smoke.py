#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'ambition_rebirth_smoke.db'}")
os.environ.setdefault("SECRET_KEY", "qa-secret-key")
os.environ.setdefault("WTF_CSRF_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "testing")

from app import app  # noqa: E402


def post(client, path, body):
    response = client.post(path, json=body)
    assert response.status_code == 200 and response.is_json
    payload = response.get_json()
    assert payload["ok"] is True
    return payload["state"]


def play_round(client, state, intent):
    match_id = state["match_id"]
    if not state["player"]["active_card"] and state["hand"]:
        state = post(client, "/api/rebirth/play-card", {"match_id": match_id, "card_id": state["hand"][0]["id"]})
    state = post(client, "/api/rebirth/intent", {"match_id": match_id, "intent": intent})
    state = post(client, "/api/rebirth/resolve", {"match_id": match_id})
    return state


def main():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    page = client.get("/rebirth")
    assert page.status_code == 200
    assert b"rb-shell" in page.data
    assert b"rb-onboarding" in page.data

    start = client.get("/api/rebirth/new?seed=qa-smoke-v2")
    assert start.status_code == 200 and start.is_json
    state = start.get_json()["state"]
    assert state["player"]["hp"] == 32
    assert state["hand"]

    initial_opponent_hp = state["opponent"]["hp"]
    for intent in ["STRIKE", "FOCUS", "GUARD"]:
        if state["is_finished"]:
            break
        state = play_round(client, state, intent)
        assert state["player"]["active_card"]
        assert state["combat_log"]
        assert state["cinematic_event"]
        assert state["round"] >= 1

    assert "hp" in state["player"]
    assert "hp" in state["opponent"]
    assert state["opponent"]["hp"] <= initial_opponent_hp

    print("REBIRTH_SMOKE_V2_OK")


if __name__ == "__main__":
    main()
