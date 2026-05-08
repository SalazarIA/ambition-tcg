import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = PROJECT_ROOT / "reports" / "qa"
SCREENSHOT_ROOT = REPORT_ROOT / "screenshots"

QA_EMAIL = "qa_browser_tester@ambitionz.local"
QA_PASSWORD = "QaBrowser123!"
QA_USERNAME = "qa_browser_tester"


def log_line(logs, text):
    logs.append(str(text))


def shot(page, shot_dir, name, logs):
    path = shot_dir / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    log_line(logs, f"screenshot: {path}")


def fill_any(page, selectors, value, label, logs):
    for selector in selectors:
        try:
            page.locator(selector).first.fill(value, timeout=2500)
            log_line(logs, f"fill_ok: {label}: {selector}")
            return True
        except Exception as exc:
            log_line(logs, f"fill_fail: {label}: {selector}: {type(exc).__name__}")
    return False


def click_any(page, selectors, label, logs, timeout=5000):
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=timeout)
            log_line(logs, f"click_ok: {label}: {selector}")
            return True
        except Exception as exc:
            log_line(logs, f"click_fail: {label}: {selector}: {type(exc).__name__}")
    raise AssertionError(f"Could not click {label}")


def login(page, base_url, logs):
    page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password", logs)
    click_any(page, ["button:has-text('Login')", "input[type=submit]"], "login", logs)
    page.wait_for_timeout(1600)

    if "/login" not in page.url:
        return

    log_line(logs, "login_still_on_login_page_try_register")
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
    click_any(page, ["button:has-text('Create account')", "input[type=submit]"], "register_submit", logs)
    page.wait_for_timeout(1800)

    page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email_after_register", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password_after_register", logs)
    click_any(page, ["button:has-text('Login')", "input[type=submit]"], "login_after_register", logs)
    page.wait_for_timeout(1800)


def body_preview(page, limit=1200):
    return page.locator("body").inner_text(timeout=3000)[:limit]


def parse_coin_count(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line.upper() == "COINS" and index + 1 < len(lines):
            try:
                return int(lines[index + 1].replace(",", "").replace(".", ""))
            except Exception:
                pass

    for line in lines:
        if line.lower().startswith("coins:"):
            raw = line.split(":", 1)[1].strip()
            try:
                return int(raw.replace(",", "").replace(".", ""))
            except Exception:
                pass

    return None


def run(base_url):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    shot_dir = SCREENSHOT_ROOT / f"production_booster_collection_deck_{timestamp}"
    shot_dir.mkdir(parents=True, exist_ok=True)

    logs = []
    failures = []
    console = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda msg: console.append(f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        try:
            login(page, base_url, logs)
            shot(page, shot_dir, "01_after_login", logs)

            page.goto(base_url.rstrip("/") + "/shop", wait_until="networkidle")
            page.wait_for_timeout(1200)
            shop_before = body_preview(page, 2000)
            coin_before = parse_coin_count(shop_before)
            log_line(logs, f"shop_before_coin={coin_before}")
            log_line(logs, "shop_before_preview=" + shop_before)
            shot(page, shot_dir, "02_shop_before", logs)

            if "Booster Shop" not in shop_before:
                raise AssertionError("Shop did not load Booster Shop page.")

            if "Not Enough Coins" in shop_before and (coin_before is None or coin_before < 300):
                log_line(logs, "not_enough_coins_for_open_booster_skipping_purchase_validation")
            else:
                click_any(
                    page,
                    [
                        "form[data-booster-open-form] button[type=submit]",
                        "button:has-text('Open Booster')",
                    ],
                    "open_booster",
                    logs,
                    timeout=6000,
                )
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1500)

                shop_after = body_preview(page, 3000)
                coin_after = parse_coin_count(shop_after)
                log_line(logs, f"shop_after_coin={coin_after}")
                log_line(logs, "shop_after_preview=" + shop_after)
                shot(page, shot_dir, "03_shop_after_open", logs)

                if "Cards Pulled" not in shop_after and "opened" not in shop_after.lower():
                    raise AssertionError("Booster open did not show pulled cards/result feedback.")

                if coin_before is not None and coin_after is not None and coin_after >= coin_before:
                    raise AssertionError(f"Coins did not decrease after booster. before={coin_before} after={coin_after}")

            page.goto(base_url.rstrip("/") + "/collection", wait_until="networkidle")
            page.wait_for_timeout(1200)
            collection = body_preview(page, 2500)
            log_line(logs, "collection_preview=" + collection)
            shot(page, shot_dir, "04_collection", logs)

            if "Collection" not in collection:
                raise AssertionError("Collection page did not load.")

            page.goto(base_url.rstrip("/") + "/deck-builder", wait_until="networkidle")
            page.wait_for_timeout(1200)
            deck = body_preview(page, 2500)
            log_line(logs, "deck_builder_preview=" + deck)
            shot(page, shot_dir, "05_deck_builder", logs)

            if "Deck Builder" not in deck:
                raise AssertionError("Deck Builder page did not load.")

            has_ownership_errors = "You do not own enough copies" in deck
            shows_deck_valid = "DECK VALID" in deck or "Deck Valid" in deck

            if has_ownership_errors and shows_deck_valid:
                raise AssertionError("Deck Builder shows DECK VALID while ownership validation errors are visible.")

            if "30/30" not in deck:
                raise AssertionError("Deck Builder did not show 30-card deck count.")

            if not has_ownership_errors and not shows_deck_valid:
                raise AssertionError("Deck Builder did not show a valid deck state for an error-free deck.")

            page.goto(base_url.rstrip("/") + "/booster-history", wait_until="networkidle")
            page.wait_for_timeout(1200)
            history = body_preview(page, 2500)
            log_line(logs, "booster_history_preview=" + history)
            shot(page, shot_dir, "06_booster_history", logs)

            if "Booster History" not in history:
                raise AssertionError("Booster History page did not load.")

            fatal_console = [item for item in console if item.startswith("error:")]
            if fatal_console:
                failures.append("console_errors=" + " | ".join(fatal_console[:8]))

            if page_errors:
                failures.append("page_errors=" + " | ".join(page_errors[:8]))

        except Exception as exc:
            failures.append(f"{type(exc).__name__}: {exc}")
            try:
                shot(page, shot_dir, "FAIL_last_state", logs)
                logs.append("fail_body=" + body_preview(page, 3000))
            except Exception:
                pass
        finally:
            browser.close()

    logs.append("console_tail=" + str(console[-30:]))
    logs.append("page_errors=" + str(page_errors[-20:]))
    logs.append(f"screenshots={shot_dir}")

    print("RESULT:", "FAIL" if failures else "PASS")
    for item in failures:
        print("ERROR:", item)
    print("\n".join(logs))

    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://ambitionzgame.com")
    args = parser.parse_args()
    raise SystemExit(run(args.base_url))


if __name__ == "__main__":
    main()
