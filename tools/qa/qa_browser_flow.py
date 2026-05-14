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
RAW_JSON_MARKERS = ['{"schema"', '"schema":', '"combat_log"', '"round_summary"', "combat_log:"]


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


def _complete_pending_selection(page, logs, timeout=4000):
    selectors = [
        ("lane", "#az48-me-field [data-az48-lane].is-legal-lane"),
        ("target", "[data-az48-target].is-legal-target"),
    ]

    for label, selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() <= 0:
                continue
            loc.click(timeout=timeout)
            logs.append(f"selection_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"selection_skip: {label}: {selector}: {type(exc).__name__}")

    return False


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


def _has_raw_json_marker(text):
    return any(marker in (text or "") for marker in RAW_JSON_MARKERS)


def _visible_text_contains(page, text):
    try:
        return page.locator(f"text={text}").first.is_visible(timeout=1500)
    except Exception:
        return False


def _result_panel_visible(page):
    try:
        return bool(page.evaluate("""() => {
            const el = document.querySelector("#az48-training-result");
            if (!el || el.hidden) return false;
            const style = window.getComputedStyle(el);
            return style.display !== "none" && style.visibility !== "hidden";
        }"""))
    except Exception:
        return False


def _visible_finished_text(page):
    return _result_panel_visible(page)




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


def _body_has_class(page, class_name):
    try:
        return page.evaluate("(className) => document.body.classList.contains(className)", class_name)
    except Exception:
        return False


def _round_summary_text(page):
    try:
        return page.locator("#az48-round-summary").first.inner_text(timeout=1500)
    except Exception:
        return ""


def _safe_text(page, selector, default=""):
    try:
        return page.locator(selector).first.inner_text(timeout=1500)
    except Exception:
        return default


def _arena_snapshot(page, label, logs):
    body = _body_text(page)
    summary_text = _round_summary_text(page)
    step_text = _safe_text(page, "#az48-step-list", "")
    next_action = _safe_text(page, "#az48-next-action", "")
    turn_hint = _safe_text(page, "#az48-turn-hint", "")
    card_detail_text = " ".join([
        _safe_text(page, "#az48-card-preview-name", ""),
        _safe_text(page, "#az48-card-detail-stats", ""),
        _safe_text(page, "#az48-card-preview-text", ""),
        _safe_text(page, "#az48-card-keyword-lines", ""),
    ]).strip()
    training_result_text = " ".join([
        _safe_text(page, "#az48-result-title", ""),
        _safe_text(page, "#az48-result-text", ""),
        _safe_text(page, "#az48-result-rewards", ""),
    ]).strip()
    snapshot = {
        "label": label,
        "round": _safe_int_text(page, "#az48-round", 0),
        "phase": _safe_text(page, "#az48-phase", "") if _visible_count(page, "#az48-phase") else "",
        "message": _safe_text(page, "#az48-message", "") if _visible_count(page, "#az48-message") else "",
        "me_hp": _safe_int_text(page, "#az48-me-hp", 0),
        "enemy_hp": _safe_int_text(page, "#az48-enemy-hp", 0),
        "me_energy": _safe_int_text(page, "#az48-me-energy", 0),
        "enemy_energy": _safe_int_text(page, "#az48-enemy-energy", 0),
        "me_ambition": _safe_int_text(page, "#az48-me-ambition", 0),
        "me_intent": _safe_text(page, "#az48-me-intent", ""),
        "enemy_status": _safe_text(page, "#az48-enemy-status", ""),
        "hud_visible": all([
            _visible_count(page, "#az48-me-hp") > 0,
            _visible_count(page, "#az48-enemy-hp") > 0,
            _visible_count(page, "#az48-me-ambition") > 0,
            _visible_count(page, "#az48-round") > 0,
            _visible_count(page, "#az48-me-intent") > 0,
            _visible_count(page, "#az48-enemy-status") > 0,
        ]),
        "hand_cards": _count_cards(page),
        "field_cards": _count_field_cards(page) if "def _count_field_cards" in globals() else _visible_count(page, "#az48-me-field [data-card-id]"),
        "body_has_playing_card": "Playing card..." in body,
        "body_has_card_not_found": "Card not found in hand" in body,
        "body_has_socket_error": "Socket connection error" in body,
        "body_has_action_failed": "Action failed" in body,
        "body_has_raw_json": _has_raw_json_marker(body),
        "finished_text_visible": _visible_finished_text(page),
        "training_result_visible": _result_panel_visible(page),
        "training_result_text": training_result_text,
        "round_summary_visible": _visible_count(page, "#az48-round-summary") > 0,
        "round_summary_text": summary_text,
        "round_summary_has_raw_json": "{" in summary_text or "}" in summary_text,
        "turn_guidance_visible": _visible_count(page, "#az48-step-list") > 0 and _visible_count(page, "#az48-next-action") > 0,
        "turn_guidance_text": " ".join([next_action, turn_hint, step_text]).strip(),
        "active_step_count": _visible_count(page, "#az48-step-list .az48-step-active"),
        "server_error_visible": _visible_count(page, "#az48-server-error") > 0,
        "card_detail_visible": _visible_count(page, "#az48-card-detail-stats span") > 0,
        "card_detail_text": card_detail_text,
        "combat_feedback_visible": (
            _visible_count(page, ".az48-lane-resolved, .az48-card-damaged, .az48-card-defeated") > 0
            or _body_has_class(page, "az48-me-hero-hit")
            or _body_has_class(page, "az48-enemy-hero-hit")
        ),
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
    if snapshot.get("body_has_raw_json"):
        raise AssertionError(f"{stage}: raw JSON is visible in arena body")
    if not snapshot.get("round_summary_visible"):
        raise AssertionError(f"{stage}: Round Summary panel is missing")
    if snapshot.get("round_summary_has_raw_json"):
        raise AssertionError(f"{stage}: Round Summary rendered raw JSON")
    if not snapshot.get("turn_guidance_visible"):
        raise AssertionError(f"{stage}: turn guidance panel is missing")
    if snapshot.get("active_step_count", 0) <= 0:
        raise AssertionError(f"{stage}: no active turn step visible")
    if not snapshot.get("card_detail_visible"):
        raise AssertionError(f"{stage}: card detail panel is missing")
    if not snapshot.get("hud_visible"):
        raise AssertionError(f"{stage}: premium HUD is missing")
    if not snapshot.get("me_intent"):
        raise AssertionError(f"{stage}: player intent is not visible")
    if not snapshot.get("enemy_status"):
        raise AssertionError(f"{stage}: enemy status is not visible")
    if snapshot.get("me_hp", 0) <= 0 and snapshot.get("enemy_hp", 0) <= 0:
        raise AssertionError(f"{stage}: both players appear dead/invalid HP")
    if str(snapshot.get("phase") or "").lower() == "finished" and not snapshot.get("finished_text_visible"):
        raise AssertionError(f"{stage}: finished phase reached without visible end state")
    if str(snapshot.get("phase") or "").lower() == "finished" and not snapshot.get("training_result_visible"):
        raise AssertionError(f"{stage}: finished training match did not show result panel")


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
            console_errors = []
            page_errors = []

            def on_console(msg):
                line = f"console_{msg.type}: {msg.text}"
                logs.append(line)
                if msg.type == "error" and "Failed to load resource" not in msg.text:
                    console_errors.append(line)

            def on_page_error(exc):
                line = f"pageerror: {exc}"
                logs.append(line)
                page_errors.append(line)

            page.on("console", on_console)
            page.on("pageerror", on_page_error)
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
            page.goto(training_url, wait_until="domcontentloaded", timeout=30000)
            page.locator(".az48-arena").first.wait_for(state="visible", timeout=15000)
            time.sleep(2)
            _shot(page, shot_dir, "03_training_before_start", logs)
            logs.append("body_training_before_start:\n" + _body_text(page)[:2200])

            if "LOGIN" in _body_text(page).upper() and "Start" not in _body_text(page):
                raise AssertionError("Training redirected to login. Auth/session failed.")

            ok_start = _click_first(page, ["#az48-floating-start", "#az48-start", "button:has-text('Start')", "text=Start"], "start", logs, timeout=7000)
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

            time.sleep(0.8)
            _complete_pending_selection(page, logs)
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
            if _has_raw_json_marker(after_card_text):
                raise AssertionError("Raw JSON visible after clicking card")

            ok_ready = _click_first(page, ["#az48-ready", "button:has-text('Ready')", "text=Ready"], "ready", logs, timeout=7000)
            assert ok_ready, "Could not click Ready"

            time.sleep(4)
            _shot(page, shot_dir, "07_after_ready", logs)
            after_ready_text = _body_text(page)
            logs.append("body_after_ready:\n" + after_ready_text[:2600])

            _assert_not_stuck(after_ready_text, "after_ready")
            if _has_raw_json_marker(after_ready_text):
                raise AssertionError("Raw JSON visible after Ready")

            cards_after_ready = _count_cards(page)
            logs.append(f"cards_after_ready: {cards_after_ready}")

            assert cards_after_ready >= 1, "No cards visible after Ready/new round"

            first_round_snapshot = _arena_snapshot(page, "after_ready_round_1", logs)
            _assert_arena_healthy(first_round_snapshot, "after_ready_round_1")
            summary_text = first_round_snapshot.get("round_summary_text") or ""
            assert "Round Summary" in summary_text, "Round Summary title is not visible after Ready"
            assert "{" not in summary_text and "}" not in summary_text, "Round Summary rendered raw JSON"
            assert any(
                phrase in summary_text
                for phrase in ["Rodada", "atacou", "dano", "derrotado", "Guarded", "Focused"]
            ), f"Round Summary did not render readable events: {summary_text!r}"
            assert first_round_snapshot.get("combat_feedback_visible"), "Combat feedback did not appear after first resolved round"

            # Eagle-eye full match loop.
            # Plays until an end state appears or a safe round limit is reached.
            max_cycles = 10
            target_round = int(first_round_snapshot.get("round") or 2) + 4
            completed_cycles = 0

            for cycle in range(2, max_cycles + 1):
                snapshot_before = _arena_snapshot(page, f"cycle_{cycle}_before", logs)
                _assert_arena_healthy(snapshot_before, f"cycle_{cycle}_before")

                if (
                    str(snapshot_before.get("phase") or "").lower() == "finished"
                    or snapshot_before.get("training_result_visible")
                ):
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
                attempted_card = False
                playable_selector = (
                    "#az48-hand .az48-card.is-playable[data-card-id], "
                    "#az48-hand .az48-card.playable[data-card-id], "
                    "#az48-hand .az48-card.az48-playable[data-card-id]"
                )

                if hand_count_before > 0 and _visible_count(page, playable_selector) > 0:
                    try:
                        page.locator(playable_selector).first.click(timeout=4000)
                        attempted_card = True
                        logs.append(f"cycle_{cycle}: clicked first playable card")
                        time.sleep(0.8)
                        _complete_pending_selection(page, logs)
                        time.sleep(2.5)
                    except Exception as exc:
                        logs.append(f"cycle_{cycle}: card click skipped {type(exc).__name__}")
                else:
                    logs.append(f"cycle_{cycle}: no playable card to click")

                snapshot_after_card = _arena_snapshot(page, f"cycle_{cycle}_after_card", logs)
                _assert_arena_healthy(snapshot_after_card, f"cycle_{cycle}_after_card")

                # If a card click happened, the UI cannot remain identical and stuck.
                hand_count_after = _count_cards(page)
                field_count_after = _count_field_cards(page)

                logs.append(
                    f"cycle_{cycle}: hand_after={hand_count_after} field_after={field_count_after}"
                )

                if attempted_card and field_count_before == 0:
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

                if snapshot_after_ready_loop.get("round", 0) >= target_round:
                    logs.append(
                        "full_match_safe_limit_reached: "
                        f"target_round={target_round} current_round={snapshot_after_ready_loop.get('round')}"
                    )
                    break

            assert completed_cycles >= 1, "Full match loop did not complete any post-round cycle"

            final_snapshot = _arena_snapshot(page, "final", logs)
            _assert_arena_healthy(final_snapshot, "final")
            if page_errors:
                raise AssertionError("Page errors detected: " + " | ".join(page_errors[:6]))
            if console_errors:
                raise AssertionError("Console errors detected: " + " | ".join(console_errors[:6]))

            logs.append("browser_full_match_flow_completed")

            browser.close()

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result
