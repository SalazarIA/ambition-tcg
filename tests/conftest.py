import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import app as ambition_app  # noqa: E402


@pytest.fixture()
def flask_app(tmp_path):
    ambition_app.app.config.update(
        TESTING=True,
        REBIRTH_DB_PATH=str(tmp_path / "rebirth-test.db"),
        REBIRTH_REQUIRE_CSRF=False,
        REBIRTH_AUTH_RATE_LIMIT=20,
        REBIRTH_AUTH_RATE_LIMIT_SECONDS=300,
        REBIRTH_ENABLE_INTERNAL_LAB=True,
        REBIRTH_BALANCE_INTERACTIVE_MATCH_LIMIT=24,
        SECRET_KEY="rebirth-test-secret",
    )
    ambition_app.REBIRTH_MATCHES.clear()
    ambition_app.AUTH_RATE_LIMITER.reset()
    ambition_app.GAME_RATE_LIMITER.reset()
    ambition_app.MATCH_TELEMETRY_CLOCKS.clear()
    yield ambition_app.app
    ambition_app.REBIRTH_MATCHES.clear()
    ambition_app.AUTH_RATE_LIMITER.reset()
    ambition_app.GAME_RATE_LIMITER.reset()
    ambition_app.MATCH_TELEMETRY_CLOCKS.clear()


@pytest.fixture()
def client(flask_app):
    with flask_app.test_client() as test_client:
        yield test_client
