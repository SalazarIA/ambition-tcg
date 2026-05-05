import os
import re
import sys
import tempfile
import uuid
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"ambition_tests_{uuid.uuid4().hex}.db")

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key-for-ambition"
os.environ["WTF_CSRF_ENABLED"] = "true"
os.environ["BETA_AUTO_VERIFY"] = "true"
os.environ["PASSWORD_MIN_LENGTH"] = "10"
os.environ["PASSWORD_REQUIRE_COMPLEXITY"] = "true"
os.environ["LOGIN_ATTEMPT_LIMIT"] = "8"
os.environ["LOGIN_ATTEMPT_WINDOW_MINUTES"] = "15"
os.environ["MATCHMAKING_BOT_FALLBACK_SECONDS"] = "10"
os.environ["ENVIRONMENT"] = "testing"


import app as ambition_app  # noqa: E402
from models import User, db  # noqa: E402


@pytest.fixture()
def flask_app():
    ambition_app.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=True,
        SERVER_NAME="localhost",
    )

    with ambition_app.app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        ambition_app.active_matches.clear()
        ambition_app.player_rooms.clear()
        ambition_app.private_waiting_rooms.clear()
        ambition_app.socket_state["waiting_player"] = None
        ambition_app.socket_state["waiting_since"] = None
        ambition_app.socket_state["waiting_deck_json"] = None
        ambition_app.socket_state["queue_generation"] = 0
        ambition_app.socket_state.setdefault("online_players", {}).clear()
        ambition_app.socket_event_hits.clear()
        ambition_app.login_attempts.clear()
        yield ambition_app.app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(flask_app):
    with flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def socketio_server():
    return ambition_app.socketio


def csrf_token_from_response(response):
    html = response.get_data(as_text=True)
    match = re.search(r'name="_csrf_token" value="([^"]+)"', html)
    assert match, "CSRF token not found in response"
    return match.group(1)


def create_user(
    username="tester",
    email="tester@example.com",
    password="StrongPass1",
    *,
    is_admin=False,
    is_verified=True,
):
    user = User(
        username=username,
        email=email,
        account_status="active" if is_verified else "unverified",
        is_verified=is_verified,
        is_admin=is_admin,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login_session(client, user, csrf_token="test-csrf-token"):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["_csrf_token"] = csrf_token
    return csrf_token
