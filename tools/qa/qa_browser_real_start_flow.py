import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.qa.qa_browser_full_match_flow import (
    QA_EMAIL,
    QA_PASSWORD,
    body_text,
    click_any,
    fill_any,
    shot,
    snapshot,
)


def run_browser_real_start_flow(base_url="http://127.0.0.1:8080", headed=False):
    from playwright.sync_api import sync_playwright

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_dir = ROOT / "reports" / "qa" / "screenshots" / f"browser_real_start_{stamp}"
    shot_dir.mkdir(parents=True, exist_ok=True)

    logs = []
    console_errors = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = browser.new_page(viewport={"width": 1440, "height": 980})

        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        try:
            page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
            fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email", logs)
            fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password", logs)
            click_any(page, ["button:has-text(\"Login\")", "input[type=submit]"], "login", logs)
            page.wait_for_timeout(1800)
            shot(page, shot_dir, "01_after_login", logs)

            # Se produção/local ainda estiver na tela de login, registra usuário QA.
            if "AMBITIONZ LOGIN" in body_text(page).upper() or page.locator("input[name=email]").count() > 0:
                logs.append("still_login_after_login_try_register")
                page.goto(base_url.rstrip("/") + "/register", wait_until="networkidle")
                fill_any(page, ["input[name=username]"], "qa_browser_real_start", "register_username", logs)
                fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "register_email", logs)
                fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "register_password", logs)
                for selector in ["input[name=confirm_password]", "input[name=password_confirm]", "input[name=confirm]"]:
                    try:
                        page.fill(selector, QA_PASSWORD, timeout=800)
                        logs.append(f"fill_ok: register_confirm: {selector}")
                        break
                    except Exception:
                        pass
                click_any(page, ["button:has-text(\"Create account\")", "input[type=submit]"], "register_submit", logs)
                page.wait_for_timeout(1800)
                shot(page, shot_dir, "01b_after_register", logs)

                page.goto(base_url.rstrip("/") + "/login", wait_until="networkidle")
                fill_any(page, ["input[name=email]", "input[type=email]"], QA_EMAIL, "email_retry", logs)
                fill_any(page, ["input[name=password]", "input[type=password]"], QA_PASSWORD, "password_retry", logs)
                click_any(page, ["button:has-text(\"Login\")", "input[type=submit]"], "login_retry", logs)
                page.wait_for_timeout(1800)
                shot(page, shot_dir, "01c_after_login_retry", logs)

            page.goto(base_url.rstrip("/") + "/training", wait_until="networkidle")
            page.wait_for_timeout(2500)
            shot(page, shot_dir, "02_training_loaded", logs)

            html_before = body_text(page)
            logs.append("body_before_start_preview=" + html_before[:1500])

            # Diagnóstico do botão real
            start_count = page.locator("#az48-floating-start").count()
            start_visible = page.locator("#az48-floating-start").is_visible() if start_count else False
            start_text = page.locator("#az48-floating-start").inner_text(timeout=1000) if start_count else ""
            logs.append(f"start_count={start_count} start_visible={start_visible} start_text={start_text!r}")

            # Clique real, igual jogador.
            page.locator("#az48-floating-start").click(timeout=5000)
            logs.append("real_click_start_done")

            page.wait_for_timeout(6000)
            shot(page, shot_dir, "03_after_real_start_click", logs)

            state = page.evaluate("() => window.__ambitionzArena48State || null")
            logs.append("state_after_real_click=" + repr(state))

            snap = snapshot(page, "after_real_start_click", logs)

            if snap["hand_cards"] <= 0:
                raise AssertionError(
                    "REAL START CLICK FAILED: clicked #az48-start but no hand appeared. "
                    f"message={snap.get('message')} phase={snap.get('phase')}"
                )

            if page_errors:
                raise AssertionError("page_errors=" + " | ".join(page_errors[:5]))

            fatal_console = [
                item for item in console_errors
                if item.startswith("error:") and "Failed to load resource" not in item
            ]
            if fatal_console:
                raise AssertionError("console_errors=" + " | ".join(fatal_console[:8]))

            return {
                "name": "browser_real_start_flow",
                "status": "PASS",
                "error": None,
                "logs": logs + ["screenshots=" + str(shot_dir)],
            }

        except Exception as exc:
            try:
                shot(page, shot_dir, "FAIL_last_state", logs)
                logs.append("fail_body=" + body_text(page)[:4000])
            except Exception:
                pass

            return {
                "name": "browser_real_start_flow",
                "status": "FAIL",
                "error": f"{type(exc).__name__}: {exc}",
                "logs": logs + [
                    "console=" + repr(console_errors[-30:]),
                    "page_errors=" + repr(page_errors[-20:]),
                    "screenshots=" + str(shot_dir),
                ],
            }

        finally:
            browser.close()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    result = run_browser_real_start_flow(base_url=args.base_url, headed=args.headed)

    print("RESULT:", result["status"])
    if result.get("error"):
        print("ERROR:", result["error"])

    for line in result["logs"]:
        print(line)

    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
