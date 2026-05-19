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


def main():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    page = client.get("/rebirth")
    assert page.status_code == 200
    assert b"rb-shell" in page.data

    start = client.get("/api/rebirth/new?seed=qa-smoke")
    assert start.status_code == 200 and start.is_json
    state = start.get_json()["state"]
    assert state["player"]["hp"] == 30
    assert state["hand"]

    match_id = state["match_id"]
    card_id = state["hand"][0]["id"]

    intent = client.post("/api/rebirth/intent", json={"match_id": match_id, "intent": "STRIKE"})
    assert intent.status_code == 200 and intent.is_json

    play = client.post("/api/rebirth/play-card", json={"match_id": match_id, "card_id": card_id})
    assert play.status_code == 200 and play.is_json
    assert play.get_json()["state"]["player"]["active_card"]["id"] == card_id

    resolved = client.post("/api/rebirth/resolve", json={"match_id": match_id})
    assert resolved.status_code == 200 and resolved.is_json
    final_state = resolved.get_json()["state"]
    assert "hp" in final_state["player"]
    assert final_state["player"]["active_card"]
    assert final_state["combat_log"]

    print("REBIRTH_SMOKE_OK")


if __name__ == "__main__":
    main()
