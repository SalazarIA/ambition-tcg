"""Item 7: rate limit on mutating game routes + pre-migration backup guard."""
import os
import subprocess
import sys
from pathlib import Path

import app as ambition_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_game_route_rate_limit_blocks_flood(client, monkeypatch):
    # Tighten the /start bucket for the test; the limiter is reset per-test by
    # the conftest fixture.
    monkeypatch.setitem(ambition_app.GAME_RATE_LIMITS, "api_rebirth_start", 3)
    ambition_app.GAME_RATE_LIMITER.reset()

    codes = [
        client.post("/api/rebirth/start", json={"seed": f"flood-{i}"}).status_code
        for i in range(5)
    ]
    assert codes[:3] == [200, 200, 200], codes
    assert codes[3] == 429 and codes[4] == 429, codes

    body = client.post("/api/rebirth/start", json={"seed": "again"}).get_json()
    assert body["error"]["code"] == "rate_limited"


def test_normal_play_is_not_rate_limited(client):
    # Default limits are generous; a single match's worth of actions must pass.
    ambition_app.GAME_RATE_LIMITER.reset()
    for i in range(8):
        assert client.post("/api/rebirth/start", json={"seed": f"ok-{i}"}).status_code == 200


def _run_backup(env_overrides):
    env = dict(os.environ)
    env.pop("DATABASE_URL", None)
    env.pop("REBIRTH_DATABASE_URL", None)
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "tools/ops/backup_before_migrate.py"],
        cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True,
    )


def test_backup_skips_without_database_url():
    result = _run_backup({})
    assert result.returncode == 0
    assert "skipping" in result.stdout.lower()


def test_backup_skips_sqlite():
    result = _run_backup({"DATABASE_URL": "sqlite:////tmp/rebirth-x.db"})
    assert result.returncode == 0
    assert "skipping" in result.stdout.lower()
