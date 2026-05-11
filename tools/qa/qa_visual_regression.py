from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SHOT_ROOT = PROJECT_ROOT / "reports" / "qa" / "visual_regression"


def _ensure_user(logs):
    try:
        from tools.qa.qa_browser_full_match_flow import ensure_browser_user

        ensure_browser_user()
        logs.append("qa_user: ready")
    except Exception as exc:
        logs.append(f"qa_user: skipped: {type(exc).__name__}: {exc}")


def _login(page, base_url, logs):
    from tools.qa.qa_browser_full_match_flow import QA_EMAIL, QA_PASSWORD, fill_any, click_any, body_text

    page.goto(base_url.rstrip("/") + "/login", wait_until="domcontentloaded", timeout=20000)
    fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email", logs)
    fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password", logs)
    click_any(page, ["button:has-text(\"Login\")", "input[type=submit]"], "login", logs)
    page.wait_for_timeout(1200)

    if "/login" in page.url or "LOGIN" in body_text(page).upper():
        logs.append("login: still_on_login_page")
    else:
        logs.append("login: ok")


def _start_training(page, logs):
    selectors = [
        "#az48-floating-start",
        "#az48-start",
        "[data-az48-action='start-training']",
        "button:has-text(\"START TRAINING\")",
        "button:has-text(\"Start\")",
        "button:has-text(\"Training\")",
    ]
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=2500)
            logs.append(f"start_training: {selector}")
            page.wait_for_timeout(1600)
            return
        except Exception as exc:
            logs.append(f"start_training_miss: {selector}: {type(exc).__name__}")


def _capture_console(name, console_errors):
    def handler(msg):
        if msg.type in {"error", "warning"}:
            console_errors.append(f"{name}:{msg.type}:{msg.text}")

    return handler


def run_visual_regression(base_url: str, headed: bool = False, out_dir: Path | None = None) -> dict:
    logs = []
    console_errors = []
    page_errors = []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_dir = out_dir or (SHOT_ROOT / stamp)
    shot_dir.mkdir(parents=True, exist_ok=True)

    _ensure_user(logs)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {
            "status": "SKIP",
            "reason": f"Playwright unavailable: {type(exc).__name__}: {exc}",
            "screenshots": [],
            "logs": logs,
            "console_errors": [],
            "page_errors": [],
        }

    screenshots = []
    viewports = [
        ("desktop", {"width": 1440, "height": 980}),
        ("mobile", {"width": 390, "height": 844}),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        for name, viewport in viewports:
            context = browser.new_context(viewport=viewport)
            page = context.new_page()
            page.on("console", _capture_console(name, console_errors))
            page.on("pageerror", lambda exc: page_errors.append(f"{name}:{exc}"))

            _login(page, base_url, logs)
            page.goto(base_url.rstrip("/") + "/training", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(1000)
            _start_training(page, logs)

            cards = page.locator("#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id]").count()
            if cards <= 0:
                page.wait_for_timeout(1400)
                cards = page.locator("#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id]").count()
            logs.append(f"hand_cards:{name}:{cards}")
            if cards <= 0:
                page_errors.append(f"{name}: training did not render a playable hand")

            path = shot_dir / f"arena_{name}.png"
            page.screenshot(path=str(path), full_page=True)
            screenshots.append(str(path))
            logs.append(f"screenshot:{name}:{path}")
            context.close()

        browser.close()

    blocking_errors = [
        error for error in console_errors + page_errors
        if "favicon" not in error.lower() and "404" not in error.lower()
    ]

    return {
        "status": "PASS" if not blocking_errors else "FAIL",
        "screenshots": screenshots,
        "logs": logs,
        "console_errors": console_errors,
        "page_errors": page_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Visual regression screenshots for arena_state_v50.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    result = run_visual_regression(args.base_url, headed=args.headed, out_dir=args.out_dir)
    print(f"RESULT: {result['status']}")
    for path in result.get("screenshots") or []:
        print(f"SCREENSHOT: {path}")
    for error in result.get("console_errors") or []:
        print(f"CONSOLE: {error}")
    for error in result.get("page_errors") or []:
        print(f"PAGEERROR: {error}")

    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
