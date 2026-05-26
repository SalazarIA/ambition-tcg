#!/usr/bin/env python3
"""Smoke the active Rebirth turn flow with the local Flask test client."""

import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = Path(tempfile.gettempdir()) / f"ambition_rebirth_smoke_{os.getpid()}.db"
DB_PATH.unlink(missing_ok=True)
os.environ.pop("DATABASE_URL", None)
os.environ["REBIRTH_ALLOW_SQLITE_TESTING"] = "true"
os.environ["REBIRTH_DB_PATH"] = str(DB_PATH)
os.environ["REBIRTH_REQUIRE_CSRF"] = "false"
os.environ.setdefault("SECRET_KEY", "qa-secret-key")

from app import app  # noqa: E402


def post(client, path, body):
    response = client.post(path, json=body)
    assert response.status_code == 200 and response.is_json, (path, response.status_code, response.get_data(as_text=True))
    payload = response.get_json()
    assert payload["ok"] is True
    return payload


def main():
    app.config.update(
        TESTING=True,
        REBIRTH_ALLOW_SQLITE_TESTING=True,
        REBIRTH_DB_PATH=str(DB_PATH),
        REBIRTH_REQUIRE_CSRF=False,
    )
    client = app.test_client()
    try:
        page = client.get("/rebirth")
        assert page.status_code == 200
        assert b"data-rebirth-app" in page.data
        assert b'phase-timeline' in page.data
        assert b'priority-label' in page.data

        state = post(client, "/api/rebirth/start", {"seed": "qa-active-flow"})["state"]
        assert state["player"]["hp"] == 30
        assert state["phase"] == "choose"
        playable = next(
            card for card in state["player"]["hand"]
            if card.get("type") == "MONSTER" and int(card.get("cost", 0)) <= int(state["player"]["energy"])
        )
        played = post(
            client,
            "/api/rebirth/play-card",
            {"match_id": state["match_id"], "card_instance_id": playable["instance_id"]},
        )
        state = played["state"]
        assert state["result"]["outcome"] == "Summon"
        assert state["is_finished"] is False
        assert played["match_reward"] is None

        abandoned = post(
            client,
            "/api/rebirth/telemetry",
            {"match_id": state["match_id"], "event_type": "match_abandoned", "reason": "smoke"},
        )
        assert abandoned["recorded"] is True

        state = post(client, "/api/rebirth/next-turn", {"match_id": state["match_id"]})["state"]
        assert state["turn"] == 2
        assert state["bot"]["battlefield"]
        resolved = post(
            client,
            "/api/rebirth/attack",
            {
                "match_id": state["match_id"],
                "attacker_instance_id": state["player"]["battlefield"][0]["instance_id"],
                "target_instance_id": state["bot"]["battlefield"][0]["instance_id"],
            },
        )
        assert resolved["state"]["result"]["outcome"] in {"Victory", "Defeat", "Clash"}
        print("PASS qa_rebirth_smoke active_turn_flow telemetry combat")
    finally:
        DB_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
