
from pathlib import Path
from datetime import datetime
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.qa.qa_browser_full_match_flow import (
    ensure_browser_user,
    body_text,
    shot,
    click_any,
    fill_any,
    QA_EMAIL,
    QA_PASSWORD,
    SHOT_ROOT,
)


def run_browser_shop_deck_flow(base_url="http://127.0.0.1:8080", headed=False):
    logs = []
    failures = []
    console_errors = []
    page_errors = []

    try:
        ensure_browser_user()

        from playwright.sync_api import sync_playwright

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot_dir = SHOT_ROOT / f"browser_shop_deck_{stamp}"

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

                pages = [
                    ("/inventory", "inventory", ["inventory", "collection", "card", "owned", "cards"]),
                    ("/collection", "collection", ["collection", "card", "monster", "spell", "trap"]),
                    ("/deck-builder", "deck_builder", ["deck", "card", "monster", "spell", "trap"]),
                    ("/shop", "shop", ["shop", "booster", "pack", "coins", "gems"]),
                ]

                for route, label, expected_terms in pages:
                    page.goto(base_url.rstrip("/") + route, wait_until="networkidle")
                    page.wait_for_timeout(1600)

                    text = body_text(page)
                    lower = text.lower()
                    logs.append(f"{label}_url={page.url}")
                    logs.append(f"{label}_body:\n{text[:3000]}")
                    shot(page, shot_dir, label, logs)

                    if page.url.rstrip("/").endswith("/login"):
                        failures.append(f"{label}: redirected to login")

                    if "internal server error" in lower or "traceback" in lower:
                        failures.append(f"{label}: internal server error visible")

                    if len(text.strip()) < 120:
                        failures.append(f"{label}: body too small, possible blank page")

                    if not any(term in lower for term in expected_terms):
                        failures.append(f"{label}: expected terms not visible: {expected_terms}")

                # Deck builder deeper checks.
                page.goto(base_url.rstrip("/") + "/deck-builder", wait_until="networkidle")
                page.wait_for_timeout(1600)
                deck_body = body_text(page)
                deck_lower = deck_body.lower()

                deck_card_count = page.locator("[data-card-id], .card, .deck-card, .collection-card").count()
                logs.append(f"deck_builder_card_like_elements={deck_card_count}")

                if deck_card_count <= 0 and not any(term in deck_lower for term in ["30", "monster", "spell", "trap"]):
                    failures.append("deck_builder: no card-like elements or deck composition visible")

                # Shop deeper checks.
                page.goto(base_url.rstrip("/") + "/shop", wait_until="networkidle")
                page.wait_for_timeout(1600)
                shop_body = body_text(page)
                shop_lower = shop_body.lower()

                shop_button_count = page.locator("button, a").count()
                logs.append(f"shop_button_or_link_count={shop_button_count}")

                if shop_button_count <= 0:
                    failures.append("shop: no buttons/links visible")

                if not any(term in shop_lower for term in ["booster", "pack", "coins", "gems", "open", "buy"]):
                    failures.append("shop: no economy/purchase terms visible")

                fatal_console = [item for item in console_errors if item.startswith("error:")]
                if fatal_console:
                    failures.append("console_errors=" + " | ".join(fatal_console[:8]))

                if page_errors:
                    failures.append("page_errors=" + " | ".join(page_errors[:8]))

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
            "name": "browser_shop_deck_flow",
            "status": "FAIL" if failures else "PASS",
            "error": "; ".join(failures) if failures else None,
            "logs": logs,
        }

    except Exception as exc:
        return {
            "name": "browser_shop_deck_flow",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "logs": logs,
        }
