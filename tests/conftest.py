import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import app as ambition_app  # noqa: E402


@pytest.fixture()
def flask_app():
    ambition_app.app.config.update(TESTING=True)
    ambition_app.REBIRTH_MATCHES.clear()
    yield ambition_app.app
    ambition_app.REBIRTH_MATCHES.clear()


@pytest.fixture()
def client(flask_app):
    with flask_app.test_client() as test_client:
        yield test_client
