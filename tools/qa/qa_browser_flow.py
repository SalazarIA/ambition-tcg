from pathlib import Path
import sys
import time
import urllib.request
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from passlib.hash import pbkdf2_sha256

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
                password_hash=pbkdf2_sha256.hash(QA_PASSWORD),
            )
            db.session.add(user)
            logs.append("qa_user_created")
        else:
            user.username = QA_USERNAME
            user.password_hash = pbkdf2_sha256.hash(QA_PASSWORD)
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




def _count_field_cards(page):
    try:
        return page.locator("#az48-me-field .az48-card[data-card-id], #az48-me-field [data-card-id]").count()
    except Exception:
        return 0


def _assert_not_stuck(text, stage):
    forbidden = [
        "Playing card...",
        "Starting training...",
        "Ready sent.",
        "Socket connection error",
        "Action failed",
        "Card not found in hand",
        "Card is no longer in hand",
    ]

    for phrase in forbidden:
        if phrase in text:
            raise AssertionError(f"{stage}: UI stuck/error phrase visible: {phrase}")


def _visible_text_contains(page, text):
    try:
        return page.locator(f"text={text}").first.is_visible(timeout=1500)
    except Exception:
        return False




def _safe_int_text(page, selector, default=0):
    try:
        raw = page.locator(selector).first.inner_text(timeout=1500)
        digits = "".join(ch for ch in raw if ch.isdigit() or ch == "-")
        return int(digits) if digits not in ("", "-") else default
    except Exception:
        return default


def _visible_count(page, selector):
    try:
        return page.locator(selector).count()
    except Exception:
        return 0


def _arena_snapshot(page, label, logs):
    body = _body_text(page)
    snapshot = {
        "label": label,
        "round": _safe_int_text(page, "#az48-round", 0),
        "phase": page.locator("#az48-phase").first.inner_text(timeout=1500) if _visible_count(page, "#az48-phase") else "",
        "message": page.locator("#az48-message").first.inner_text(timeout=1500) if _visible_count(page, "#az48-message") else "",
        "me_hp": _safe_int_text(page, "#az48-me-hp", 0),
        "enemy_hp": _safe_int_text(page, "#az48-enemy-hp", 0),
        "me_energy": _safe_int_text(page, "#az48-me-energy", 0),
        "enemy_energy": _safe_int_text(page, "#az48-enemy-energy", 0),
        "hand_cards": _count_cards(page),
        "field_cards": _count_field_cards(page) if "def _count_field_cards" in globals() else _visible_count(page, "#az48-me-field [data-card-id]"),
        "body_has_playing_card": "Playing card..." in body,
        "body_has_card_not_found": "Card not found in hand" in body,
        "body_has_socket_error": "Socket connection error" in body,
        "body_has_action_failed": "Action failed" in body,
    }
    logs.append(f"arena_snapshot_{label}: {snapshot}")
    return snapshot


def _assert_arena_healthy(snapshot, stage):
    if snapshot.get("body_has_playing_card"):
        raise AssertionError(f"{stage}: UI stuck on Playing card...")
    if snapshot.get("body_has_card_not_found"):
        raise AssertionError(f"{stage}: Card not found in hand visible")
    if snapshot.get("body_has_socket_error"):
        raise AssertionError(f"{stage}: Socket connection error visible")
    if snapshot.get("body_has_action_failed"):
        raise AssertionError(f"{stage}: Action failed visible")
    if snapshot.get("me_hp", 0) <= 0 and snapshot.get("enemy_hp", 0) <= 0:
        raise AssertionError(f"{stage}: both players appear dead/invalid HP")


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
            assert cards_after_start == 5, f"Expected exactly 5 cards after Start, got {cards_after_start}"

            _assert_not_stuck(after_start_text, "after_start")

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

            # A carta precisa sair da mão. Se continuar com o mesmo número,
            # o frontend travou ou o backend não confirmou o play_card.
            assert cards_after_card == cards_after_start - 1, (
                f"Card was not removed from hand after play. "
                f"Before={cards_after_start}, after={cards_after_card}"
            )

            # O campo precisa receber uma carta renderizada.
            field_cards = page.locator("#az48-me-field .az48-card[data-card-id], #az48-me-field [data-card-id]").count()
            logs.append(f"field_cards_after_card: {field_cards}")
            assert field_cards >= 1, "No card appeared on player field after play"

            if "Playing card..." in after_card_text:
                raise AssertionError("UI got stuck on Playing card... after clicking card")

            if "Card not found in hand" in after_card_text:
                raise AssertionError("UI shows Card not found in hand after clicking card")

            if "Action failed" in after_card_text:
                raise AssertionError("UI shows Action failed after clicking card")

            ok_ready = _click_first(page, ["#az48-ready", "button:has-text('Ready')", "text=Ready"], "ready", logs, timeout=7000)
            assert ok_ready, "Could not click Ready"

            time.sleep(4)
            _shot(page, shot_dir, "07_after_ready", logs)
            after_ready_text = _body_text(page)
            logs.append("body_after_ready:\n" + after_ready_text[:2600])

            _assert_not_stuck(after_ready_text, "after_ready")

            cards_after_ready = _count_cards(page)
            logs.append(f"cards_after_ready: {cards_after_ready}")

            assert cards_after_ready >= 1, "No cards visible after Ready/new round"

            first_round_snapshot = _arena_snapshot(page, "after_ready_round_1", logs)
            _assert_arena_healthy(first_round_snapshot, "after_ready_round_1")

            # Eagle-eye full match loop.
            # Plays up to 12 cycles or until victory/defeat/finished state appears.
            max_cycles = 12
            completed_cycles = 0

            for cycle in range(2, max_cycles + 1):
                snapshot_before = _arena_snapshot(page, f"cycle_{cycle}_before", logs)
                _assert_arena_healthy(snapshot_before, f"cycle_{cycle}_before")

                body_now = _body_text(page)
                lower = body_now.lower()

                if any(word in lower for word in ["victory", "defeat", "winner", "match finished", "rewards"]):
                    logs.append(f"full_match_stop: finished text detected at cycle {cycle}")
                    break

                # Choose intent if buttons are visible.
                if _visible_count(page, "#az48-strike") > 0:
                    try:
                        page.locator("#az48-strike").click(timeout=3000)
                        logs.append(f"cycle_{cycle}: clicked Strike")
                        time.sleep(1.2)
                    except Exception as exc:
                        logs.append(f"cycle_{cycle}: strike click skipped {type(exc).__name__}")

                hand_count_before = _count_cards(page)
                field_count_before = _count_field_cards(page)
                logs.append(f"cycle_{cycle}: hand_before={hand_count_before} field_before={field_count_before}")

                # Play first available card if possible.
                if hand_count_before > 0:
                    try:
                        page.locator("#az48-hand .az48-card[data-card-id]").first.click(timeout=4000)
                        logs.append(f"cycle_{cycle}: clicked first card")
                        time.sleep(2.5)
                    except Exception as exc:
                        logs.append(f"cycle_{cycle}: card click skipped {type(exc).__name__}")

                snapshot_after_card = _arena_snapshot(page, f"cycle_{cycle}_after_card", logs)
                _assert_arena_healthy(snapshot_after_card, f"cycle_{cycle}_after_card")

                # If a card click happened, the UI cannot remain identical and stuck.
                hand_count_after = _count_cards(page)
                field_count_after = _count_field_cards(page)

                logs.append(
                    f"cycle_{cycle}: hand_after={hand_count_after} field_after={field_count_after}"
                )

                if hand_count_before > 0 and field_count_before == 0:
                    assert (
                        hand_count_after == hand_count_before - 1 or field_count_after > field_count_before
                    ), (
                        f"cycle_{cycle}: card click did not change hand/field. "
                        f"hand_before={hand_count_before}, hand_after={hand_count_after}, "
                        f"field_before={field_count_before}, field_after={field_count_after}"
                    )

                # Ready should advance or resolve.
                if _visible_count(page, "#az48-ready") > 0:
                    page.locator("#az48-ready").click(timeout=4000)
                    logs.append(f"cycle_{cycle}: clicked Ready")
                    time.sleep(3.0)

                snapshot_after_ready_loop = _arena_snapshot(page, f"cycle_{cycle}_after_ready", logs)
                _assert_arena_healthy(snapshot_after_ready_loop, f"cycle_{cycle}_after_ready")

                completed_cycles += 1

                if snapshot_after_ready_loop.get("round", 0) >= 3:
                    logs.append(f"full_match_progress_confirmed: reached round {snapshot_after_ready_loop.get('round')}")
                    break

            assert completed_cycles >= 1, "Full match loop did not complete any post-round cycle"

            final_snapshot = _arena_snapshot(page, "final", logs)
            _assert_arena_healthy(final_snapshot, "final")

            logs.append("browser_full_match_flow_completed")

            browser.close()

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result
