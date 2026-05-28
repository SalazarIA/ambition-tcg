#!/usr/bin/env python3
"""Validate HTML and API contracts consumed by the active arena client."""

import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = Path(tempfile.gettempdir()) / f"ambition_rebirth_browser_contract_{os.getpid()}.db"
DB_PATH.unlink(missing_ok=True)
os.environ.pop("DATABASE_URL", None)
os.environ["REBIRTH_ALLOW_SQLITE_TESTING"] = "true"
os.environ["REBIRTH_DB_PATH"] = str(DB_PATH)
os.environ["REBIRTH_REQUIRE_CSRF"] = "false"
os.environ.setdefault("SECRET_KEY", "qa-secret-key")

from app import REBIRTH_RELEASE_VERSION, app  # noqa: E402


def main():
    app.config.update(TESTING=True, REBIRTH_DB_PATH=str(DB_PATH), REBIRTH_REQUIRE_CSRF=False)
    client = app.test_client()
    try:
        page = client.get("/rebirth")
        body = page.get_data(as_text=True)
        assert page.status_code == 200
        for token in (
            'data-rebirth-app',
            'id="phase-timeline"',
            'id="priority-label"',
            'id="interrupt-label"',
            "static/css/rebirth.css",
            "static/js/rebirth.js",
            REBIRTH_RELEASE_VERSION,
            "telemetry:",
        ):
            assert token in body, f"Missing /rebirth browser contract token: {token}"

        response = client.post("/api/rebirth/start", json={"seed": "browser-contract"})
        assert response.status_code == 200 and response.is_json
        state = response.get_json()["state"]
        for key in (
            "match_id",
            "phase",
            "turn",
            "turn_phase",
            "player",
            "bot",
            "resolution_context",
            "available_evolutions",
            "is_finished",
        ):
            assert key in state, f"Missing Rebirth state key: {key}"
        print("PASS qa_rebirth_browser_contract arena_html authoritative_state")
    finally:
        DB_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
