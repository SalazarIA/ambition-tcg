"""End-to-end checks for navigation, authenticated setup, and arena rules.

What's covered:
    - Arena (/rebirth) and Loja (/rebirth/shop) load successfully on both
      desktop (1280x720) and mobile (390x844) viewports.
    - The Loja response carries the `Cache-Control: no-store` header so a
      stale cached shop page never lingers across logins.
    - The "Arena → Loja → Arena" navigation flow keeps the global nav and
      its wallet widgets in the DOM (the brittle case where a layout
      template gets dropped on one of the routes).
    - The auth modal opens and an account can be created through the visible
      form, synchronizing its 30-card loadout.
    - An authenticated first-turn summon cannot damage the bot directly:
      both the visible target state and the API reject the attempt until
      the bot receives its turn.
    - Signature overlays remain dismissible through normal game actions,
      honor reduced-motion settings, and failed booster opens keep their seal.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from services.rebirth_state import FIRST_DUEL_BOT_HP

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


def test_mobile_arena_is_native_and_keeps_touch_targets_readable(page, live_server):
    """The phone layout must not scale down desktop controls below touch size."""
    if page.viewport_size["width"] > 760:
        pytest.skip("mobile viewport assertion")

    page.goto(f"{live_server}/rebirth")
    page.locator("#player-battlefield .rb-field-slot-empty").first.wait_for(state="visible", timeout=10_000)
    measurements = page.evaluate(
        """() => {
            const body = getComputedStyle(document.body);
            const board = getComputedStyle(document.getElementById("rebirth-board"));
            const play = document.getElementById("play-button").getBoundingClientRect();
            const nextTurn = document.getElementById("next-turn-button").getBoundingClientRect();
            const slot = document.querySelector("#player-battlefield .rb-field-slot-empty").getBoundingClientRect();
            return {
                mobile: document.body.classList.contains("rb-mobile-native"),
                transform: board.transform,
                overflowY: body.overflowY,
                touchAction: body.touchAction,
                playHeight: play.height,
                nextHeight: nextTurn.height,
                slotHeight: slot.height
            };
        }"""
    )

    assert measurements["mobile"] is True
    assert measurements["transform"] == "none"
    assert measurements["overflowY"] == "auto"
    assert "pan-y" in measurements["touchAction"]
    assert measurements["playHeight"] >= 48
    assert measurements["nextHeight"] >= 48
    assert measurements["slotHeight"] >= 112


# --- signature / shop regression guards -----------------------------------


def test_finale_overlay_does_not_block_new_match_action(page, live_server):
    """The fullscreen finale may decorate the result, but not trap the player."""
    page.goto(f"{live_server}/rebirth")
    page.locator("#rebirth-finale-overlay").wait_for(state="attached", timeout=10_000)
    page.evaluate(
        """() => {
            const overlay = document.getElementById("rebirth-finale-overlay");
            overlay.innerHTML = '<div class="vfx-finale-curtain"></div><div class="vfx-finale-text">Vitoria</div>';
            overlay.classList.add("is-active", "is-victory");
            overlay.setAttribute("aria-hidden", "false");
        }"""
    )

    with page.expect_response(lambda response: "/api/rebirth/start" in response.url):
        page.locator("[data-new-match]:visible").first.click(timeout=5_000)

    assert page.locator("#rebirth-finale-overlay").get_attribute("aria-hidden") == "true"


def test_finale_reduced_motion_removes_entry_transitions(page, live_server):
    page.emulate_media(reduced_motion="reduce")
    page.goto(f"{live_server}/rebirth")
    styles = page.evaluate(
        """() => {
            const overlay = document.getElementById("rebirth-finale-overlay");
            overlay.innerHTML = '<div class="vfx-finale-curtain"></div><div class="vfx-finale-text">Vitoria</div>';
            overlay.classList.add("is-active", "is-victory");
            return {
                curtain: getComputedStyle(overlay.querySelector(".vfx-finale-curtain")).transitionDuration,
                text: getComputedStyle(overlay.querySelector(".vfx-finale-text")).transitionDuration,
            };
        }"""
    )

    assert styles == {"curtain": "0s", "text": "0s"}


def test_failed_guest_booster_open_keeps_seal_intact(page, live_server):
    page.goto(f"{live_server}/rebirth/shop")
    page.wait_for_load_state("networkidle")
    button = page.locator("[data-rebirth-booster]").first
    pack = button.locator("xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' rb-shop-pack ')][1]")

    with page.expect_response(lambda response: "/api/rebirth/booster/open" in response.url) as response_info:
        button.click()

    assert response_info.value.status in {401, 403}
    assert "is-seal-broken" not in (pack.get_attribute("class") or "")


# --- authenticated combat rule ---------------------------------------------


def test_authenticated_first_turn_blocks_direct_damage_until_bot_responds(page, live_server):
    """Register through the UI and prove the turn-one direct-hit rule end to end."""
    suffix = uuid4().hex[:10]
    username = f"e2e_{suffix}"
    email = f"{username}@example.com"

    page.goto(f"{live_server}/rebirth")
    page.wait_for_load_state("networkidle")
    page.locator("[data-rebirth-global-nav] [data-rebirth-auth-open]").click()
    register = page.locator("[data-rebirth-register]").first
    register.locator('input[name="username"]').fill(username)
    register.locator('input[name="email"]').fill(email)
    register.locator('input[name="password"]').fill("password123")

    with page.expect_response(lambda response: "/api/rebirth/auth/register" in response.url) as register_info:
        register.locator('button[type="submit"]').click()
    registered = register_info.value
    registered_payload = registered.json()
    assert registered.status == 200
    assert registered_payload["account"]["authenticated"] is True
    assert registered_payload["collection"]["summary"]["loadout_size"] == 30

    page.wait_for_url("**/rebirth?firstRun=1", timeout=10_000)
    page.locator("[data-rebirth-username]").wait_for(state="visible", timeout=10_000)
    assert page.locator("[data-rebirth-username]").inner_text() == username
    page.locator("#player-hand [data-card-instance]:not([disabled])").first.wait_for(
        state="visible",
        timeout=10_000,
    )
    page.locator("#player-hand [data-card-instance]:not([disabled])").first.click()

    play_button = page.locator("#play-button")
    assert "invocar" in play_button.inner_text().lower()
    with page.expect_response(lambda response: "/api/rebirth/play-card" in response.url) as play_info:
        play_button.click()
    after_summon = play_info.value.json()["state"]
    assert after_summon["turn"] == 1
    assert after_summon["bot"]["battlefield"] == []

    assert "atacar" in play_button.inner_text().lower()
    assert play_button.is_disabled()
    assert "Dano direto bloqueado no primeiro turno" in play_button.get_attribute("title")
    assert page.locator("#bot-battlefield [data-direct-attack]").count() == 0
    assert "protegido no turno 1" in page.locator("#bot-battlefield").inner_text().lower()

    blocked = page.request.post(
        f"{live_server}/api/rebirth/attack",
        data={
            "match_id": after_summon["match_id"],
            "attacker_instance_id": after_summon["player"]["battlefield"][0]["instance_id"],
        },
    )
    assert blocked.status == 409
    assert blocked.json()["error"]["code"] == "first_turn_direct_attack_blocked"

    with page.expect_response(lambda response: "/api/rebirth/next-turn" in response.url) as turn_info:
        page.locator("#next-turn-button").click()
    after_bot = turn_info.value.json()["state"]
    assert after_bot["turn"] == 2
    assert after_bot["bot"]["hp"] == FIRST_DUEL_BOT_HP
    assert after_bot["bot"]["battlefield"]
    page.locator("#bot-battlefield [data-target-instance]").first.wait_for(state="visible", timeout=10_000)
