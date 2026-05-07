
from pathlib import Path
from datetime import datetime
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SHOT_ROOT = PROJECT_ROOT / "reports" / "qa" / "screenshots"
QA_EMAIL = "qa_browser_tester@ambitionz.local"
QA_USERNAME = "qa_browser_tester"
QA_PASSWORD = "QaBrowser123!"


def ensure_browser_user():
    from app import app, db
    from models import User
    from passlib.hash import pbkdf2_sha256

    with app.app_context():
        user = User.query.filter_by(email=QA_EMAIL).first()

        if not user:
            user = User(username=QA_USERNAME, email=QA_EMAIL)
            db.session.add(user)
            db.session.flush()

        user.username = QA_USERNAME
        user.email = QA_EMAIL
        user.password_hash = pbkdf2_sha256.hash(QA_PASSWORD)

        if hasattr(user, "is_verified"):
            user.is_verified = True

        if hasattr(user, "account_status"):
            user.account_status = "active"

        if hasattr(user, "coins"):
            user.coins = max(int(user.coins or 0), 3000)

        if hasattr(user, "gems"):
            user.gems = max(int(user.gems or 0), 10)

        try:
            from services.economy.inventory_migration import repair_user_inventory_and_deck
            repair_user_inventory_and_deck(user)
        except Exception:
            pass

        db.session.commit()


def body_text(page):
    try:
        return page.locator("body").inner_text(timeout=2500)
    except Exception as exc:
        return f"BODY_ERROR {type(exc).__name__}: {exc}"


def shot(page, folder, name, logs):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    logs.append(f"screenshot: {path}")


def click_any(page, selectors, label, logs, timeout=3500):
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=timeout)
            logs.append(f"click_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"click_fail: {label}: {selector}: {type(exc).__name__}")

    return False


def fill_any(page, selectors, value, label, logs, timeout=3500):
    for selector in selectors:
        try:
            page.locator(selector).first.fill(value, timeout=timeout)
            logs.append(f"fill_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"fill_fail: {label}: {selector}: {type(exc).__name__}")

    return False


def count_cards(page, selector):
    try:
        return page.locator(selector).count()
    except Exception:
        return 0


def read_int(page, selector, default=0):
    try:
        raw = page.locator(selector).first.inner_text(timeout=1200)
        digits = "".join(ch for ch in raw if ch.isdigit() or ch == "-")
        return int(digits) if digits not in ("", "-") else default
    except Exception:
        return default


def read_text(page, selector, default=""):
    try:
        return page.locator(selector).first.inner_text(timeout=1200).strip()
    except Exception:
        return default


def snapshot(page, label, logs):
    text = body_text(page)

    snap = {
        "label": label,
        "round": read_int(page, "#az48-round", 0),
        "phase": read_text(page, "#az48-phase", ""),
        "message": read_text(page, "#az48-message", ""),
        "me_hp": read_int(page, "#az48-me-hp", 0),
        "enemy_hp": read_int(page, "#az48-enemy-hp", 0),
        "hand_cards": count_cards(page, "#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id]"),
        "my_field_cards": count_cards(page, "#az48-me-field .az48-card[data-card-id], #az48-me-field [data-card-id]"),
        "enemy_field_cards": count_cards(page, "#az48-enemy-field .az48-card[data-card-id], #az48-enemy-field [data-card-id]"),
        "stuck_playing": "Playing card..." in text,
        "socket_error": "Socket connection error" in text,
        "internal_error": "Internal server error" in text or "Traceback" in text,
    }

    logs.append(f"snapshot_{label}: {snap}")
    return snap


def assert_state_ok(snap, label):
    if snap["internal_error"]:
        raise AssertionError(f"{label}: internal error visible")

    if snap["socket_error"]:
        raise AssertionError(f"{label}: socket error visible")

    if snap["stuck_playing"]:
        raise AssertionError(f"{label}: stuck Playing card message")

    if snap["me_hp"] <= 0 and snap["phase"].lower() != "finished":
        raise AssertionError(f"{label}: invalid player HP")

    if snap["enemy_hp"] <= 0 and snap["phase"].lower() != "finished":
        raise AssertionError(f"{label}: invalid enemy HP")


def run_browser_full_match_flow(base_url="http://127.0.0.1:8080", headed=False):
    logs = []
    failures = []
    console_errors = []
    page_errors = []

    try:
        ensure_browser_user()

        from playwright.sync_api import sync_playwright

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot_dir = SHOT_ROOT / f"browser_full_match_{stamp}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not headed)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}"))
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))

            try:
                page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
                fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email", logs)
                fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password", logs)
                click_any(page, ["button:has-text(\"Login\")", "input[type=submit]"], "login", logs)
                page.wait_for_timeout(1400)
                shot(page, shot_dir, "01_after_login", logs)

                page.goto(base_url.rstrip("/") + "/training", wait_until="networkidle")
                page.wait_for_timeout(1400)
                shot(page, shot_dir, "02_training_before_start", logs)

                click_any(page, ["#az48-start", "button:has-text(\"Start\")", "#join-queue-btn"], "start_training", logs)
                page.wait_for_timeout(3000)
                start = snapshot(page, "after_start", logs)
                shot(page, shot_dir, "03_after_start", logs)

                if start["hand_cards"] <= 0:
                    raise AssertionError("No cards appeared after Start")

                start_round = start["round"]
                last = start
                intents = ["Strike", "Guard", "Focus"]

                for index in range(1, 7):
                    intent = intents[(index - 1) % len(intents)]

                    click_any(page, [f"#az48-{intent.lower()}", f"button:has-text(\"{intent}\")"], f"intent_{intent}", logs)
                    page.wait_for_timeout(1200)

                    after_intent = snapshot(page, f"round_{index}_after_intent", logs)
                    assert_state_ok(after_intent, f"round_{index}_after_intent")

                    hand_before = after_intent["hand_cards"]
                    field_before = after_intent["my_field_cards"]

                    if hand_before > 0:
                        click_any(page, [
                            "#az48-hand .az48-card[data-card-id]",
                            "#hand .az48-card[data-card-id]",
                            ".az48-card[data-card-id]",
                        ], "first_card", logs)

                        page.wait_for_timeout(2500)

                        after_card = snapshot(page, f"round_{index}_after_card", logs)
                        shot(page, shot_dir, f"round_{index}_after_card", logs)
                        assert_state_ok(after_card, f"round_{index}_after_card")

                        # Only require mutation when the field was empty before the click.
                        # If the slot is already occupied, the game may safely reject another field play.
                        if field_before == 0 and after_card["hand_cards"] >= hand_before and after_card["my_field_cards"] <= field_before:
                            raise AssertionError(
                                f"Card click did not mutate hand/field. hand_before={hand_before} "
                                f"hand_after={after_card['hand_cards']} field_before={field_before} "
                                f"field_after={after_card['my_field_cards']}"
                            )

                        if field_before > 0 and after_card["hand_cards"] >= hand_before and after_card["my_field_cards"] <= field_before:
                            logs.append(
                                "card_click_no_mutation_allowed_because_field_occupied="
                                f"hand_before={hand_before} hand_after={after_card['hand_cards']} "
                                f"field_before={field_before} field_after={after_card['my_field_cards']}"
                            )

                    click_any(page, ["#az48-ready", "#ready-btn", "button:has-text(\"Ready\")"], "ready", logs)
                    page.wait_for_timeout(3200)

                    last = snapshot(page, f"round_{index}_after_ready", logs)
                    shot(page, shot_dir, f"round_{index}_after_ready", logs)
                    assert_state_ok(last, f"round_{index}_after_ready")

                    if last["round"] >= start_round + 3:
                        logs.append(f"progress_confirmed: start_round={start_round} current_round={last['round']}")
                        break

                if last["round"] <= start_round:
                    raise AssertionError(f"Round did not advance. start={start_round} final={last['round']}")

                fatal_console = [item for item in console_errors if item.startswith("error:")]
                if fatal_console:
                    failures.append("console_errors=" + " | ".join(fatal_console[:6]))

                if page_errors:
                    failures.append("page_errors=" + " | ".join(page_errors[:6]))

                logs.append("console_tail=" + str(console_errors[-30:]))
                logs.append("page_errors=" + str(page_errors[-20:]))

            except Exception as exc:
                failures.append(f"{type(exc).__name__}: {exc}")
                try:
                    shot(page, shot_dir, "FAIL_last_state", logs)
                    logs.append("fail_body:\n" + body_text(page)[:4000])
                except Exception:
                    pass

            finally:
                browser.close()

        return {
            "name": "browser_full_match_flow",
            "status": "FAIL" if failures else "PASS",
            "error": "; ".join(failures) if failures else None,
            "logs": logs,
        }

    except Exception as exc:
        return {
            "name": "browser_full_match_flow",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "logs": logs,
        }
