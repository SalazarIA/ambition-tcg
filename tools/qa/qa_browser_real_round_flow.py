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


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def shot(page, shot_dir, name, logs):
    path = shot_dir / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    logs.append(f"screenshot: {path}")


def body_text(page):
    try:
        return page.locator("body").inner_text(timeout=3000)
    except Exception:
        return ""


def fill_any(page, selectors, value, label, logs):
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.fill(value, timeout=2500)
            logs.append(f"fill_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"fill_fail: {label}: {selector}: {type(exc).__name__}")
    return False


def click_any(page, selectors, label, logs, timeout=5000):
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.click(timeout=timeout)
            logs.append(f"click_ok: {label}: {selector}")
            return True
        except Exception as exc:
            logs.append(f"click_fail: {label}: {selector}: {type(exc).__name__}: {exc}")
    return False


def snapshot(page, label, logs):
    state = page.evaluate(
        """(label) => {
            const s = window.__ambitionzArena48State || null;
            const text = document.body ? document.body.innerText : "";
            const hand = document.querySelectorAll("#az48-hand .az48-card[data-card-id]").length;
            const playable = document.querySelectorAll("#az48-hand .az48-card.playable[data-card-id], #az48-hand .az48-card.is-playable[data-card-id], #az48-hand .az48-card.az48-playable[data-card-id]").length;
            const myField = document.querySelectorAll("#az48-me-field .az48-card[data-card-id]").length;
            const enemyField = document.querySelectorAll("#az48-enemy-field .az48-card[data-card-id]").length;
            return {
                label,
                has_state: !!s,
                schema: s && s.schema,
                phase: s && s.phase,
                round: s && s.round,
                message: s && s.message,
                hand_cards: hand,
                playable_cards: playable,
                my_field_cards: myField,
                enemy_field_cards: enemyField,
                body_preview: text.slice(0, 900),
            };
        }""",
        label,
    )
    logs.append(f"snapshot_{label}: {state}")
    return state


def login_or_register(page, base_url, shot_dir, logs):
    page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password", logs)
    click_any(page, ['button:has-text("Login")', "input[type=submit]"], "login", logs)
    page.wait_for_timeout(1800)
    shot(page, shot_dir, "01_after_login", logs)

    if "/login" not in page.url:
        return

    logs.append("login_still_on_login_page_try_register")
    page.goto(base_url.rstrip("/") + "/register", wait_until="networkidle")
    fill_any(page, ["input[name=username]", "input[name=name]"], QA_USERNAME, "register_username", logs)
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "register_email", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "register_password", logs)
    fill_any(
        page,
        ["input[name=confirm_password]", "input[name=password_confirm]", "input[name=confirm]"],
        QA_PASSWORD,
        "register_confirm_password",
        logs,
    )
    click_any(page, ['button:has-text("Create account")', 'button:has-text("Register")', "input[type=submit]"], "register_submit", logs)
    page.wait_for_timeout(1800)
    shot(page, shot_dir, "01b_after_register", logs)

    page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email_after_register", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password_after_register", logs)
    click_any(page, ['button:has-text("Login")', "input[type=submit]"], "login_after_register", logs)
    page.wait_for_timeout(1800)
    shot(page, shot_dir, "01c_after_login_retry", logs)


def run(base_url):
    logs = []
    failures = []
    shot_dir = PROJECT_ROOT / "reports" / "qa" / "screenshots" / f"browser_real_round_{timestamp()}"
    shot_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)

        console_errors = []
        page_errors = []

        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        try:
            login_or_register(page, base_url, shot_dir, logs)

            page.goto(base_url.rstrip("/") + "/training", wait_until="networkidle")
            page.wait_for_timeout(1800)
            shot(page, shot_dir, "02_training_loaded", logs)
            logs.append("body_before_start_preview=" + body_text(page)[:1000])

            start_count = page.locator("#az48-floating-start").count()
            start_visible = page.locator("#az48-floating-start").is_visible() if start_count else False
            start_text = page.locator("#az48-floating-start").inner_text(timeout=1000) if start_count else ""
            logs.append(f"floating_start_count={start_count} visible={start_visible} text={start_text!r}")

            if not start_count or not start_visible:
                raise AssertionError("Floating Start button is not visible/clickable.")

            page.locator("#az48-floating-start").click(timeout=5000)
            logs.append("real_click_start_done")

            page.wait_for_function(
                "() => window.__ambitionzArena48State && window.__ambitionzArena48State.me && Array.isArray(window.__ambitionzArena48State.me.hand) && window.__ambitionzArena48State.me.hand.length > 0",
                timeout=12000,
            )
            page.wait_for_timeout(800)
            shot(page, shot_dir, "03_after_start", logs)

            start_state = snapshot(page, "after_start", logs)
            if start_state["hand_cards"] <= 0:
                raise AssertionError("Start clicked but no hand appeared.")

            click_any(page, ["#az48-strike"], "strike", logs)
            page.wait_for_timeout(900)
            shot(page, shot_dir, "04_after_strike", logs)

            after_intent = snapshot(page, "after_strike", logs)
            if str(after_intent["phase"]).lower() != "main":
                raise AssertionError(f"Expected phase MAIN after Strike. Got {after_intent['phase']}")

            playable_selector = "#az48-hand .az48-card.playable[data-card-id], #az48-hand .az48-card.is-playable[data-card-id], #az48-hand .az48-card.az48-playable[data-card-id]"
            playable_count = page.locator(playable_selector).count()
            logs.append(f"playable_count_before_card={playable_count}")

            if playable_count <= 0:
                raise AssertionError("No playable card available after Strike.")

            before_card = snapshot(page, "before_card_click", logs)
            page.locator(playable_selector).first.click(timeout=5000)
            logs.append("real_click_playable_card_done")
            page.wait_for_timeout(1500)
            shot(page, shot_dir, "05_after_card", logs)

            after_card = snapshot(page, "after_card", logs)
            if after_card["hand_cards"] >= before_card["hand_cards"] and after_card["my_field_cards"] <= before_card["my_field_cards"]:
                raise AssertionError(
                    "Playable card click did not mutate hand/field. "
                    f"hand_before={before_card['hand_cards']} hand_after={after_card['hand_cards']} "
                    f"field_before={before_card['my_field_cards']} field_after={after_card['my_field_cards']}"
                )

            click_any(page, ["#az48-ready"], "ready", logs)
            page.wait_for_timeout(3200)
            shot(page, shot_dir, "06_after_ready", logs)

            after_ready = snapshot(page, "after_ready", logs)
            if int(after_ready["round"] or 0) <= int(start_state["round"] or 0):
                raise AssertionError(f"Ready did not advance round. start={start_state['round']} after={after_ready['round']}")

            if page_errors:
                failures.append("page_errors=" + " | ".join(page_errors[:6]))

            fatal_console = [
                item for item in console_errors
                if item.startswith("error:")
                and "Failed to load resource" not in item
            ]
            if fatal_console:
                failures.append("console_errors=" + " | ".join(fatal_console[:6]))

            logs.append("console_tail=" + str(console_errors[-30:]))
            logs.append("page_errors=" + str(page_errors[-20:]))
            logs.append(f"screenshots={shot_dir}")

        except Exception as exc:
            failures.append(f"{type(exc).__name__}: {exc}")
            try:
                shot(page, shot_dir, "FAIL_last_state", logs)
                logs.append("fail_body=" + body_text(page)[:4000])
                logs.append("console=" + str(console_errors[-40:]))
                logs.append("page_errors=" + str(page_errors[-20:]))
                logs.append(f"screenshots={shot_dir}")
            except Exception:
                pass

        finally:
            browser.close()

    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print("ERROR:", failure)
        print("")
        print("\n".join(logs))
        raise SystemExit(1)

    print("RESULT: PASS")
    print("\n".join(logs))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    run(args.base_url)


if __name__ == "__main__":
    main()
