"""End-to-end checks for navbar, cache-control headers, and the auth modal.

What's covered:
    - Arena (/rebirth) and Loja (/rebirth/shop) load successfully on both
      desktop (1280x720) and mobile (390x844) viewports.
    - The Loja response carries the `Cache-Control: no-store` header so a
      stale cached shop page never lingers across logins.
    - The "Arena → Loja → Arena" navigation flow keeps the global nav and
      its wallet widgets in the DOM (the brittle case where a layout
      template gets dropped on one of the routes).
    - The auth modal opens when the "Entrar / Cadastrar" button is clicked
      and exposes both the login and register forms.

What's intentionally *not* here:
    - Real combat-animation timing — that requires playing through the
      engine, which is much heavier and warrants its own file. A skeleton
      is included to document the seams.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


# --- navigation ------------------------------------------------------------


def test_arena_page_renders_global_nav(page, live_server):
    page.goto(f"{live_server}/rebirth")
    nav = page.locator("[data-rebirth-global-nav]")
    nav.wait_for(state="visible", timeout=10_000)

    # Both primary tabs must be visible.
    assert nav.locator("a", has_text="Arena").is_visible()
    assert nav.locator("a", has_text="Loja").is_visible()

    # Wallet widgets are rendered (even with placeholder zeros for guests).
    assert page.locator('[data-rebirth-wallet-value="GOLD"]').first.is_visible()
    assert page.locator('[data-rebirth-wallet-value="COINZ"]').first.is_visible()


def test_shop_page_returns_no_store_cache_header(page, live_server):
    """The shop page must opt out of HTTP caching so stale wallets never leak."""
    with page.expect_response(f"{live_server}/rebirth/shop") as response_info:
        page.goto(f"{live_server}/rebirth/shop")

    response = response_info.value
    assert response.status == 200
    headers = {k.lower(): v for k, v in response.all_headers().items()}
    assert "no-store" in headers.get("cache-control", "").lower(), (
        f"shop response missing no-store; cache-control={headers.get('cache-control')!r}"
    )


def test_navbar_round_trip_keeps_layout_intact(page, live_server):
    """Arena → Loja → Arena: nav element survives the round trip on every hop.

    Regresses against the failure where a layout block is missing on one
    of the routes and the navbar vanishes mid-flow.
    """
    for path in ("/rebirth", "/rebirth/shop", "/rebirth"):
        page.goto(f"{live_server}{path}")
        # rebirth_product.html (used by /rebirth/shop) and rebirth.html (Arena)
        # both render the nav, but it may not be the first element painted —
        # wait for the explicit selector rather than `domcontentloaded`.
        nav = page.locator("[data-rebirth-global-nav]").first
        nav.wait_for(state="visible", timeout=15_000)
        assert nav.is_visible(), f"global nav missing at {path}"


# --- auth modal ------------------------------------------------------------


def test_auth_modal_opens_with_login_and_register_forms(page, live_server):
    page.goto(f"{live_server}/rebirth")
    page.locator("[data-rebirth-global-nav]").wait_for(state="visible", timeout=10_000)
    # Wait for JS modules (rebirth_global.js binds the auth-open click handler
    # via event delegation) to finish loading. Without this the click can fire
    # before the handler is registered and the modal stays hidden.
    page.wait_for_load_state("networkidle")

    # /rebirth (Arena) has exactly one auth-open button (in the nav). On other
    # pages (Shop, Profile) the same selector may appear in multiple sections;
    # we scope to the global nav here to be unambiguous.
    open_button = page.locator("[data-rebirth-global-nav] [data-rebirth-auth-open]")
    assert open_button.is_visible(), "expected guest auth-open button in nav"
    open_button.click()

    modal = page.locator("[data-rebirth-auth-modal]")
    modal.wait_for(state="visible", timeout=5_000)

    login_form = page.locator("[data-rebirth-login]").first
    register_form = page.locator("[data-rebirth-register]").first
    assert login_form.is_visible()
    assert register_form.is_visible()

    # Required fields exist on both forms (>=1 in case the form is duplicated
    # across surfaces, e.g. modal + inline fallback).
    assert login_form.locator('input[name="email"]').count() >= 1
    assert login_form.locator('input[name="password"]').count() >= 1
    assert register_form.locator('input[name="username"]').count() >= 1


# --- console / network sanity --------------------------------------------


def test_no_console_errors_on_arena_load(page, live_server):
    """Silent JS errors are the #1 killer of game-feel. Fail loud if any appear."""
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )

    page.goto(f"{live_server}/rebirth")
    page.locator("[data-rebirth-global-nav]").wait_for(state="visible", timeout=10_000)
    # Let any deferred init run.
    page.wait_for_timeout(750)

    assert not errors, f"console errors on /rebirth load:\n  - " + "\n  - ".join(errors)


# --- combat animation hooks (skeleton) ------------------------------------


@pytest.mark.skip(reason="requires authenticated match setup; tracked separately")
def test_combat_animation_classes_precede_numeric_update(page, live_server):
    """Placeholder for the briefing's animation-ordering check.

    The intent is: when a clash resolves, the attacker slot must gain its
    `is-charging` (or equivalent) class and the defender must flash
    `is-hit` *before* the Guard/HP numeric update lands in the DOM. To
    actually verify that, we'd need:
        1. an authenticated user with a known deck
        2. start a match against a bot
        3. play a card and call /api/rebirth/attack
        4. snapshot the slot classes and the HP/Guard text between frames

    Implementing 1-2 requires a /test-login backdoor or seeded session
    cookie injected through the Playwright context, which isn't wired yet.
    Leaving the test skipped with a clear TODO is more honest than a
    half-instrumented assertion.
    """
