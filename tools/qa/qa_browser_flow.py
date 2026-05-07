from pathlib import Path
import sys
import time
import urllib.request
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.security import generate_password_hash

from app import app, db
from models import User
from tools.qa.qa_config import SCREENSHOT_ROOT, QA_TIMESTAMP

QA_USERNAME = "qa_browser_tester"
QA_EMAIL = "qa_browser_tester@ambitionz.local"
QA_PASSWORD = "Audit12345"


def _ensure_local_server(base_url, logs):
    health_url = base_url.rstrip("/") + "/health"

    try:
        with urllib.request.urlopen(health_url, timeout=5) as response:
            body = response.read().decode("utf-8", errors="ignore")
            logs.append(f"health_check: status={response.status} body={body[:180]}")
            return True
    except Exception as exc:
        logs.append(f"health_check_failed: {type(exc).__name__}: {exc}")
        return False


def _ensure_qa_user(logs):
    with app.app_context():
        user = User.query.filter_by(email=QA_EMAIL).first()

        if not user:
            user = User(
                username=QA_USERNAME,
                email=QA_EMAIL,
                password_hash=generate_password_hash(QA_PASSWORD, method="pbkdf2:sha256"),
            )
            db.session.add(user)
            logs.append("qa_user_created")
        else:
            user.username = QA_USERNAME
            user.password_hash = generate_password_hash(QA_PASSWORD, method="pbkdf2:sha256")
            logs.append("qa_user_updated")

        if hasattr(user, "is_verified"):
            user.is_verified = True

        if hasattr(user, "account_status"):
            user.account_status = "active"

        db.session.commit()
        logs.append(f"qa_user_ready: id={user.id} username={user.username} email={user.email}")


def _shot(page, shot_dir, name, logs):
    path = shot_dir / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    logs.append(f"screenshot: {path}")


def _body_text(page):
    try:
        return page.locator("body").inner_text(timeout=3000)
    except Exception as exc:
        return f"[body_text_error {type(exc).__name__}: {exc}]"


def _click_first(page, selectors, label, logs, timeout=5000):
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.click(timeout=timeout)
            logs.append(f"click_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"click_fail: {label}: {selector}: {type(exc).__name__}")
    return False


def _fill_first(page, selectors, value, label, logs, timeout=5000):
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.fill(value)
            logs.append(f"fill_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"fill_fail: {label}: {selector}: {type(exc).__name__}")
    return False


def _count_cards(page):
    try:
        return page.locator("#az48-hand .az48-card[data-card-id]").count()
    except Exception:
        return 0


def _visible_text_contains(page, text):
    try:
        return page.locator(f"text={text}").first.is_visible(timeout=1500)
    except Exception:
        return False


def run_browser_flow(base_url="http://127.0.0.1:8080", headed=False):
    logs = []
    result = {
        "name": "browser_local_training_flow",
        "status": "PASS",
        "logs": logs,
        "error": None,
        "screenshots": None,
    }

    shot_dir = SCREENSHOT_ROOT / f"browser_local_{QA_TIMESTAMP}"
    shot_dir.mkdir(parents=True, exist_ok=True)
    result["screenshots"] = str(shot_dir)

    try:
        if not _ensure_local_server(base_url, logs):
            raise AssertionError(
                f"Local server is not running at {base_url}. Start it first with: python3 app.py"
            )

        _ensure_qa_user(logs)

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not headed, slow_mo=160 if headed else 0)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            page.on("console", lambda msg: logs.append(f"console_{msg.type}: {msg.text}"))
            page.on("pageerror", lambda exc: logs.append(f"pageerror: {exc}"))
            page.on("requestfailed", lambda req: logs.append(f"requestfailed: {req.url} {req.failure}"))

            login_url = base_url.rstrip("/") + "/login"
            training_url = base_url.rstrip("/") + "/training"

            logs.append(f"goto_login: {login_url}")
            page.goto(login_url, wait_until="networkidle", timeout=30000)
            _shot(page, shot_dir, "01_login", logs)

            ok_email = _fill_first(page, ["input[name='email']", "input[type='email']"], QA_EMAIL, "email", logs)
            ok_password = _fill_first(page, ["input[name='password']", "input[type='password']"], QA_PASSWORD, "password", logs)
            assert ok_email, "Could not fill login email"
            assert ok_password, "Could not fill login password"

            ok_login = _click_first(page, ["button:has-text('Login')", "button[type='submit']", "input[type='submit']"], "login", logs)
            assert ok_login, "Could not click Login"

            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(1)
            _shot(page, shot_dir, "02_after_login", logs)
            logs.append(f"url_after_login: {page.url}")
            logs.append("body_after_login:\n" + _body_text(page)[:1800])

            logs.append(f"goto_training: {training_url}")
            page.goto(training_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            _shot(page, shot_dir, "03_training_before_start", logs)
            logs.append("body_training_before_start:\n" + _body_text(page)[:2200])

            if "LOGIN" in _body_text(page).upper() and "Start" not in _body_text(page):
                raise AssertionError("Training redirected to login. Auth/session failed.")

            ok_start = _click_first(page, ["#az48-start", "button:has-text('Start')", "text=Start"], "start", logs, timeout=7000)
            assert ok_start, "Could not click Start"

            time.sleep(4)
            _shot(page, shot_dir, "04_after_start", logs)
            after_start_text = _body_text(page)
            logs.append("body_after_start:\n" + after_start_text[:2600])

            cards_after_start = _count_cards(page)
            logs.append(f"cards_after_start: {cards_after_start}")
            assert cards_after_start > 0, "No cards appeared after Start"

            ok_strike = _click_first(page, ["#az48-strike", "button:has-text('Strike')", "text=Strike"], "strike", logs, timeout=7000)
            assert ok_strike, "Could not click Strike"

            time.sleep(2)
            _shot(page, shot_dir, "05_after_strike", logs)
            logs.append("body_after_strike:\n" + _body_text(page)[:2600])

            ok_card = _click_first(page, ["#az48-hand .az48-card[data-card-id]", ".az48-card[data-card-id]"], "first_card", logs, timeout=7000)
            assert ok_card, "Could not click first card"

            time.sleep(3)
            _shot(page, shot_dir, "06_after_card", logs)
            after_card_text = _body_text(page)
            logs.append("body_after_card:\n" + after_card_text[:2600])

            cards_after_card = _count_cards(page)
            logs.append(f"cards_after_card: {cards_after_card}")
            assert cards_after_card <= cards_after_start, "Card count did not decrease/stabilize after card play"

            if "Card not found in hand" in after_card_text:
                raise AssertionError("UI shows Card not found in hand after clicking card")

            ok_ready = _click_first(page, ["#az48-ready", "button:has-text('Ready')", "text=Ready"], "ready", logs, timeout=7000)
            assert ok_ready, "Could not click Ready"

            time.sleep(4)
            _shot(page, shot_dir, "07_after_ready", logs)
            after_ready_text = _body_text(page)
            logs.append("body_after_ready:\n" + after_ready_text[:2600])

            if "Socket connection error" in after_ready_text:
                raise AssertionError("Socket connection error visible after Ready")

            if "Action failed" in after_ready_text:
                raise AssertionError("Action failed visible after Ready")

            browser.close()

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result
