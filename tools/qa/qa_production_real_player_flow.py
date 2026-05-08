import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright


QA_EMAIL = "qa_browser_tester@ambitionz.local"
QA_PASSWORD = "QaBrowser123!"
QA_USERNAME = "qa_browser_tester"


def mkdir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def shot(page, shot_dir, name, logs):
    path = Path(shot_dir) / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    logs.append(f"screenshot: {path}")


def fill_any(page, selectors, value, label, logs, timeout=2500):
    for selector in selectors:
        try:
            page.locator(selector).first.fill(value, timeout=timeout)
            logs.append(f"fill_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"fill_fail: {label}: {selector}: {type(exc).__name__}")
    return False


def click_any(page, selectors, label, logs, timeout=6000):
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=timeout)
            logs.append(f"click_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"click_fail: {label}: {selector}: {type(exc).__name__}: {exc}")
    raise AssertionError(f"Could not click {label}")


def snapshot(page, label):
    return page.evaluate(
        """(label) => {
            const state = window.__ambitionzArena48State || null;
            const cards = document.querySelectorAll("#az48-hand .az48-card").length;
            const playable = document.querySelectorAll("#az48-hand .az48-card.playable, #az48-hand .az48-card.is-playable, #az48-hand .az48-card.az48-playable").length;
            const myField = document.querySelectorAll("#az48-me-field .az48-card").length;
            const body = document.body ? document.body.innerText : "";
            return {
                label,
                has_state: !!state,
                schema: state && state.schema,
                phase: state && state.phase,
                round: state && state.round,
                message: state && state.message,
                hand_cards: cards,
                playable_cards: playable,
                my_field_cards: myField,
                body_preview: body.slice(0, 1200)
            };
        }""",
        label,
    )


def login_or_register(page, base_url, logs):
    page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password", logs)
    click_any(page, ["button:has-text('Login')", "input[type=submit]"], "login", logs)
    page.wait_for_timeout(1500)

    if "/login" not in page.url:
        return

    logs.append("login_still_on_login_page_try_register")
    page.goto(base_url.rstrip("/") + "/register", wait_until="networkidle")
    fill_any(page, ["input[name=username]"], QA_USERNAME, "register_username", logs)
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "register_email", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "register_password", logs)
    fill_any(
        page,
        ["input[name=confirm_password]", "input[name=password_confirm]", "input[name=confirm]"],
        QA_PASSWORD,
        "register_confirm_password",
        logs,
        timeout=1200,
    )
    click_any(page, ["button:has-text('Create account')", "input[type=submit]"], "register_submit", logs)
    page.wait_for_timeout(1800)

    page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email_after_register", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password_after_register", logs)
    click_any(page, ["button:has-text('Login')", "input[type=submit]"], "login_after_register", logs)
    page.wait_for_timeout(1800)


def assert_page_not_login(page, label):
    body = page.locator("body").inner_text(timeout=5000)
    if "AMBITIONZ LOGIN" in body and "ACCESS" in body:
        raise AssertionError(f"{label} redirected to login")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://ambitionzgame.com")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    shot_dir = PROJECT_ROOT / "reports" / "qa" / "screenshots" / f"production_real_player_flow_{stamp}"
    mkdir(shot_dir)

    logs = []
    failures = []
    console = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)

        page.on("console", lambda msg: console.append(f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        try:
            login_or_register(page, base_url, logs)
            shot(page, shot_dir, "01_after_login", logs)

            page.goto(base_url + "/training", wait_until="networkidle")
            page.wait_for_timeout(1200)
            assert_page_not_login(page, "training")
            shot(page, shot_dir, "02_training_loaded", logs)

            click_any(page, ["#az48-floating-start"], "floating_start", logs)
            page.wait_for_function(
                "() => window.__ambitionzArena48State && window.__ambitionzArena48State.me && Array.isArray(window.__ambitionzArena48State.me.hand) && window.__ambitionzArena48State.me.hand.length > 0",
                timeout=12000,
            )
            page.wait_for_timeout(600)
            start = snapshot(page, "after_start")
            logs.append(f"snapshot_after_start: {start}")
            shot(page, shot_dir, "03_after_start", logs)

            if start["hand_cards"] <= 0:
                raise AssertionError("No cards after real start click")

            click_any(page, ["#az48-strike"], "strike", logs)
            page.wait_for_timeout(900)
            after_strike = snapshot(page, "after_strike")
            logs.append(f"snapshot_after_strike: {after_strike}")
            shot(page, shot_dir, "04_after_strike", logs)

            if after_strike["playable_cards"] <= 0:
                raise AssertionError("No playable cards after Strike")

            click_any(
                page,
                [
                    "#az48-hand .az48-card.playable[data-card-id]",
                    "#az48-hand .az48-card.is-playable[data-card-id]",
                    "#az48-hand .az48-card.az48-playable[data-card-id]",
                ],
                "playable_card",
                logs,
            )
            page.wait_for_timeout(1300)
            after_card = snapshot(page, "after_card")
            logs.append(f"snapshot_after_card: {after_card}")
            shot(page, shot_dir, "05_after_card", logs)

            if after_card["my_field_cards"] <= 0:
                raise AssertionError("Playable card click did not place card on field")

            click_any(page, ["#az48-ready"], "ready", logs)
            page.wait_for_timeout(2200)
            after_ready = snapshot(page, "after_ready")
            logs.append(f"snapshot_after_ready: {after_ready}")
            shot(page, shot_dir, "06_after_ready", logs)

            if int(after_ready["round"] or 0) < 2:
                raise AssertionError("Ready did not advance to round 2")

            for path, name in [
                ("/deck-builder", "07_deck_builder"),
                ("/shop", "08_shop"),
                ("/collection", "09_collection"),
                ("/training", "10_training_return"),
            ]:
                page.goto(base_url + path, wait_until="networkidle")
                page.wait_for_timeout(1000)
                assert_page_not_login(page, name)
                shot(page, shot_dir, name, logs)
                body = page.locator("body").inner_text(timeout=5000)
                logs.append(f"{name}_body_preview={body[:500]}")

            logs.append("console_tail=" + str(console[-30:]))
            logs.append("page_errors=" + str(page_errors[-10:]))
            logs.append(f"screenshots={shot_dir}")

        except Exception as exc:
            failures.append(f"{type(exc).__name__}: {exc}")
            try:
                shot(page, shot_dir, "FAIL_last_state", logs)
                logs.append("fail_body=" + page.locator("body").inner_text(timeout=3000)[:2000])
            except Exception:
                pass

        finally:
            browser.close()

    print("RESULT:", "FAIL" if failures else "PASS")
    if failures:
        print("ERROR:", failures[0])

    print("\n".join(logs))

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
