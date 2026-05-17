#!/usr/bin/env python3
from pathlib import Path
import os
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'ambition_ascension_routes_qa.db'}")
os.environ.setdefault("SECRET_KEY", "qa-secret-key")
os.environ.setdefault("WTF_CSRF_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "testing")

from app import app  # noqa: E402


def main():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    training = client.get("/training")
    legacy = client.get("/training-legacy")
    start = client.post("/api/ascension/start", json={"seed": "qa-routes"})
    state = client.get("/api/ascension/state")

    assert training.status_code == 200
    assert b"ax-duel-altar" in training.data
    assert legacy.status_code == 200
    assert b"az48-training-panel" in legacy.data
    assert start.status_code == 200 and start.is_json
    assert state.status_code == 200 and state.is_json
    assert start.get_json()["match"]["version"] == "ascension_duel_v1"
    print("PASS ascension_routes")


if __name__ == "__main__":
    main()
