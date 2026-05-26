#!/usr/bin/env python3
"""Exercise authenticated product surfaces on the active Rebirth runtime."""

import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = Path(tempfile.gettempdir()) / f"ambition_rebirth_productization_{os.getpid()}.db"
DB_PATH.unlink(missing_ok=True)
os.environ.pop("DATABASE_URL", None)
os.environ["REBIRTH_ALLOW_SQLITE_TESTING"] = "true"
os.environ["REBIRTH_DB_PATH"] = str(DB_PATH)
os.environ["REBIRTH_REQUIRE_CSRF"] = "false"
os.environ.setdefault("SECRET_KEY", "qa-secret-key")

from app import app  # noqa: E402


def ok(response):
    assert response.status_code == 200 and response.is_json, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["ok"] is True, payload
    return payload


def main():
    app.config.update(
        TESTING=True,
        REBIRTH_ALLOW_SQLITE_TESTING=True,
        REBIRTH_DB_PATH=str(DB_PATH),
        REBIRTH_REQUIRE_CSRF=False,
        REBIRTH_BALANCE_INTERACTIVE_MATCH_LIMIT=24,
    )
    client = app.test_client()
    try:
        assert "Ambitionz Rebirth" in client.get("/").get_data(as_text=True)
        account = ok(
            client.post(
                "/api/rebirth/auth/register",
                json={"username": "ProductPilot", "email": "product-pilot@example.com", "password": "password123"},
            )
        )["account"]
        assert account["authenticated"] is True

        state = ok(client.post("/api/rebirth/start", json={"seed": "qa-product"}))["state"]
        evolution = state["available_evolutions"][0]
        state = ok(
            client.post(
                "/api/rebirth/evolve",
                json={"match_id": state["match_id"], "card_id": evolution["card_id"]},
            )
        )["state"]
        history = ok(client.get("/api/rebirth/match-history"))["history"]
        balance = ok(client.get("/api/rebirth/balance/simulate?matches=200"))["balance"]

        assert state["player"]["hand"]
        assert history
        assert balance["matches"] == 24
        assert "average_turns" in balance["summary"]
        print("PASS qa_rebirth_productization auth persistence balance_cap")
    finally:
        DB_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
