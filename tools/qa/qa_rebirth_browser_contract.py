#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'ambition_rebirth_browser_contract.db'}")
os.environ.setdefault("SECRET_KEY", "qa-secret-key")
os.environ.setdefault("WTF_CSRF_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "testing")

from app import app  # noqa: E402


def main():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    page = client.get("/rebirth")
    body = page.get_data(as_text=True)
    assert page.status_code == 200
    for token in [
        'id="rebirth-3d-stage"',
        "static/css/rebirth.css",
        "static/js/rebirth.js",
        "static/js/rebirth_3d_adapter.js",
        "Ambitionz Rebirth",
        "STRIKE",
        "GUARD",
        "FOCUS",
        'id="rb-hand"',
        'id="rb-combat-log-list"',
    ]:
        assert token in body, f"Missing /rebirth browser contract token: {token}"

    start = client.get("/api/rebirth/new?seed=browser-contract")
    assert start.status_code == 200 and start.is_json
    payload = start.get_json()
    assert payload["ok"] is True
    state = payload["state"]
    for key in [
        "match_id",
        "phase",
        "round",
        "player",
        "opponent",
        "available_actions",
        "is_finished",
    ]:
        assert key in state, f"Missing Rebirth state key: {key}"

    print("REBIRTH_BROWSER_CONTRACT_OK")


if __name__ == "__main__":
    main()
