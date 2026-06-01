from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_rebirth_template_matches_premium_clash_contract():
    template = read("templates/rebirth.html")

    assert "filename='css/rebirth.css'" in template
    assert "filename='js/rebirth.js'" in template
    assert "filename='js/rebirth_audio.js'" in template
    assert "rebirth_3d_adapter.js" not in template
    assert "Socket.IO" not in template

    for token in [
        'data-rebirth-app',
        'class="rb-game-viewport"',
        'id="rebirth-board"',
        'class="rb-hud"',
        'class="rb-hero-portrait rb-hero-player"',
        'id="player-hero-name"',
        'id="player-hp"',
        'id="player-hp-fill"',
        'id="player-energy"',
        'id="player-max-energy"',
        'id="player-mana-coins"',
        'id="player-deck-count"',
        'id="player-discard-count"',
        'id="turn-number"',
        'id="phase-label"',
        'class="rb-hero-portrait rb-hero-bot"',
        'id="bot-hero-name"',
        'id="bot-hp"',
        'id="bot-hp-fill"',
        'id="bot-energy"',
        'id="bot-max-energy"',
        'id="bot-mana-coins"',
        'id="bot-deck-count"',
        'id="bot-discard-count"',
        'id="bot-card"',
        'id="bot-battlefield"',
        'id="player-battlefield"',
        'id="focus-card"',
        'id="evolution-panel"',
        'id="evolution-status"',
        'id="evolution-card-thumbnail"',
        'id="player-hand"',
        'id="play-button"',
        'id="next-turn-button"',
        'id="result-panel"',
        'id="tactics-strip"',
        'id="ability-events"',
        'id="reward-panel"',
        'id="guide-rule-title"',
        'id="guide-combine-title"',
        'id="bot-profile-label"',
        'id="turn-log"',
        "Invocar",
        "Encerrar turno",
        "Carregando",
        "Nova partida",
        "REBIRTH_ASSETS",
    ]:
        assert token in template


def test_rebirth_css_locks_reference_classes_and_assets():
    css = read("static/css/rebirth.css")

    for token in [
        ".rb-game-viewport",
        ".rb-game-board",
        ".rb-hud",
        ".rb-hud-player",
        ".rb-hud-bot",
        ".rb-turn-core",
        ".rb-battle-zone",
        ".rb-field-card",
        ".rb-card-back",
        ".rb-main-card",
        ".rb-monster-card-main",
        ".rb-duplicate-panel",
        ".rb-evolution-panel",
        ".rb-mini-card",
        ".rb-actions-row",
        ".rb-panel-hero",
        ".rb-panel-base",
        ".rb-panel-surface",
        "--rb-board-width",
        "--rb-board-height",
        "--rb-scale",
        "safe-area-inset-top",
        "rb-turn-phase-pill",
        ".rb-monster-card.is-burn",
        ".rb-log-toggle",
        "rb-screen-shake",
        "rb-spark-float",
        "rb-mist-drift",
        "rb-foil-sweep",
        'data-bot-profile="aggressive"',
        "--rb-gold",
        "--rb-cyan",
        "--rb-faction-fire",
        "--rb-faction-water",
        "--rb-faction-earth",
        "--rb-faction-shadow",
        "v93 FATES_FIX",
        "v97 MOBILE_WEB_FIX",
        ".rb-hero-portrait",
        ".rb-mana-coin",
        "object-fit: contain",
        "background-size: contain",
        ".rb-card-image-layer img",
        ".rb-card-titlebar",
        ".rb-card-textbox",
        "background: rgba(0, 0, 0, 0.6)",
        "perspective: 1200px",
        "0 18px 34px rgba(0, 0, 0, 0.56)",
        ".rb-field-card.is-attacking",
        ".rb-field-card.is-targetable",
        ".rb-field-card.is-attack-lunging",
        ".rb-field-card.is-taking-hit",
        ".rb-result-panel.is-result-reading",
        ".is-cta-pulse:not(:disabled)",
        ".rb-mobile-native .rb-game-board",
        "touch-action: pan-y",
        "min-height: 52px",
        "rb-target-line-pulse",
        "rb-result-copy-fade",
        ".rb-hand .rb-mini-card.is-locked",
        "cursor: not-allowed",
        "bot-card-back.png",
        "bot-emblem.png",
        "overflow: hidden",
    ]:
        assert token in css
    assert "filter: brightness(1.18)" in css
    assert "backdrop-filter" not in css
    assert "drop-shadow" not in css
    assert ".is-cta-pulse:not(:disabled)," in css
    assert ".vfx-finale-overlay.is-active {\n    display: flex;\n    pointer-events: none;" in css
    assert ".vfx-finale-overlay .vfx-finale-curtain,\n    .vfx-finale-overlay .vfx-finale-text {" in css
    assert "#player-hand:has(" in css
    assert ".rb-hand:has(" not in css
    assert "overflow: hidden !important;" in css
    assert "--rb-mobile-nav-height: 196px;" in css
    assert "width: min(calc(100% - 20px), 1320px);" in css
    assert ".rb-mobile-native .rb-global-tabs {" in css
    assert "grid-template-columns: repeat(auto-fit, minmax(56px, 1fr));" in css
    assert ".rb-mobile-native .rb-global-player {" in css
    assert "flex: 1 0 auto;" in css
    assert ".is-parallaxing" not in css
    assert "v59 performance hardening: waiting states stay visually rich but static." in css
    assert ".battlefield-ember,\n.rb-field-card.is-element-fire::before" in css


def test_mobile_web_arena_reclaims_hidden_nav_space_after_fates_rewrite():
    css = read("static/css/rebirth.css")

    assert "v97 MOBILE_WEB_FIX: mobile web repair" in css
    assert "body.rb-game-page.rb-mobile-native .rb-global-nav" in css
    assert "display: grid !important;" in css
    assert "grid-template-rows: 130px 52px !important;" in css
    assert ".rb-mobile-native .rb-hand::-webkit-scrollbar" in css
    assert ".rb-mobile-native .rb-result-panel > div::-webkit-scrollbar" in css
    assert "scrollbar-width: none;" in css
    assert "grid-auto-columns: clamp(96px, 27vw, 112px) !important;" in css
    assert "height: 100px !important;" in css
    assert "transform: translateY(-12px) scale(1.08) !important;" in css


def test_rebirth_service_worker_caches_active_reference_assets():
    service_worker = read("static/js/service-worker.js")
    asset_manifest = read("static/assets/rebirth/manifest.json")
    art_contract = read("services/rebirth_art.py")

    assert 'const CACHE_NAME = "v97_MOBILE_WEB_FIX";' in service_worker
    assert '"version": "v97_MOBILE_WEB_FIX"' in asset_manifest
    assert 'REBIRTH_ART_VERSION = "v97_MOBILE_WEB_FIX"' in art_contract
    assert "REBIRTH_CACHE_RE" in service_worker
    assert "MOBILE_WEB_FIX" in service_worker
    assert "RELEASE_POLISH" in service_worker
    assert "EMAIL_VERIFY" in service_worker
    assert r"rebirth(?:[-_].*)?" in service_worker
    assert "key !== CACHE_NAME && REBIRTH_CACHE_RE.test(key)" in service_worker
    assert 'stableAsset("/static/css/rebirth.css")' in service_worker
    assert 'stableAsset("/static/js/rebirth.js")' in service_worker
    assert 'stableAsset("/static/js/rebirth_audio.js")' in service_worker
    assert "/static/assets/rebirth/audio/impact_heavy.wav" in service_worker
    assert "/static/assets/rebirth/audio/shield_shatter.wav" in service_worker
    assert "/static/assets/rebirth/audio/evolution_burst.wav" in service_worker
    assert "/static/assets/rebirth/audio/click_metallic.wav" in service_worker
    assert "CORE_ASSET_SET.has(`${url.pathname}${url.search}`)" in service_worker
    assert "function pruneActiveCache()" in service_worker
    assert "pruneActiveCache()" in service_worker
    assert "/rebirth/collection" not in service_worker
    assert "/rebirth/profile" not in service_worker
    assert "/rebirth/lab" not in service_worker
    assert "/rebirth/history" not in service_worker
    assert "/rebirth/support" not in service_worker
    assert "/rebirth/onboarding" not in service_worker
    assert "/rebirth/release" not in service_worker
    assert "/static/js/rebirth_product.js" in service_worker
    assert "/static/js/rebirth_global.js" in service_worker
    assert "PLAYER_STATE_API_DENY_RE" in service_worker
    # v59: expanded deny list — auth and loadout were sliding through the
    # generic /api/ fallback. Pinning the wider regex keeps intent explicit.
    assert "(?:wallet|profile|market|auth|loadout)" in service_worker
    assert "tutorial" in service_worker  # tutorial endpoints are network-only too
    assert "isCacheableAppShellRequest" in service_worker
    assert "dreadclaw-art.webp" in service_worker
    assert "dreadmaw-art" not in service_worker
    assert "bot-card-back.png" in service_worker
    assert "bot-emblem.png" in service_worker
    assert "dreadclaw.svg" not in service_worker
    assert 'self.addEventListener("activate"' in service_worker
    assert "self.skipWaiting();" in service_worker


def test_rebirth_combat_guidance_stays_in_pt_br():
    ui = read("static/js/rebirth_ui.js")
    arena = read("static/js/rebirth.js")
    combined = ui + arena

    for expected in (
        "Vantagem forte",
        "Troca provável",
        "Ataque direto bloqueado até o bot responder.",
        "Jogue ",
    ):
        assert expected in combined

    for forbidden in (
        "Strong advantage",
        "Trade likely",
        "High chance to lose unit",
        "Direct attack locked until bot responds.",
        "Choose a card first.",
        "Attack enemy unit.",
    ):
        assert forbidden not in combined


def test_rebirth_js_uses_json_api_and_card_art_contract():
    js = read("static/js/rebirth.js")

    assert "fetch(" in js
    assert "Socket.IO" not in js
    assert "Rebirth3D" not in js
    for token in [
        "RebirthApi",
        "RebirthStore",
        "RebirthRenderer",
        "RebirthInput",
        "RebirthBoardScaler",
        "RebirthAssets",
        "RebirthErrors",
        "RebirthFeel",
        "RebirthCombatMotion",
        "RebirthTactics",
        "player_field",
        "bot_field",
        "data-summon-action",
        "attackTarget",
        "is-locked",
        "rb-card-titlebar",
        "renderTurnPhase",
        "triggerScreenShake",
        "refreshAfterAuth",
        "initiateMobilePurchase",
        "turn_phase",
        "botProfile",
        "turn-log-toggle",
        "guide-rule-title",
        "X-Rebirth-CSRF",
        "match_reward",
        "navigator.vibrate",
        "player-hp-fill",
        "bot-hp-fill",
        "player-energy",
        "bot-energy",
        "player-deck-count",
        "tactics-strip",
        "evolution-card-thumbnail",
        "rb-mini-card",
        "card.art",
        "attack",
        "guard",
        "Invocar",
        "Duelo ocupado",
        "Próximo turno",
        "Troca de Guarda.",
        "Encerre o turno para o bot agir e recarregar sua mana.",
        "scrollRestoration",
        "switchActivePage",
        "RebirthArenaLifecycle",
        'removeEventListener("mousemove"',
        "cancelAnimationFrame(parallaxRaf)",
        'addEventListener("animationend", removeDestroyedCard',
    ]:
        assert token in js
    assert "RebirthParallax" not in js
    assert "const FIELD_SLOT_COUNT = 3;" in js
    assert 'switchActivePage("arena");' in js
    assert "Array.isArray(side.field)" not in js
    assert "(side.battlefield || [])" not in js
    assert "(state.player && state.player.field)" not in js
    assert "(state.bot && state.bot.field)" not in js
    assert "card.has_attacked || card.has_acted" in js
    assert "const cardImage = this.cardImageUrl(card);" in js
    assert 'const temporary = cardImage ? "" : this.temporaryArtUrl(card);' in js
    assert 'loading="lazy" decoding="async"' in js
    assert "Object.values((manifest && manifest.cards) || {}).forEach" not in js
    assert "simulated" not in js

    product_js = read("static/js/rebirth_product.js")
    global_js = read("static/js/rebirth_global.js")
    assert "X-Rebirth-CSRF" in product_js
    assert "syncAfterAuth" in global_js
    assert "rebirth:auth-synced" in global_js
    assert "refreshCollection" in global_js
    assert '.rb-global-tabs' not in product_js
    assert "history.pushState" not in product_js
    assert 'fetch(url, { credentials: "same-origin" })' in product_js
    assert "initiateMobilePurchase" in product_js


def test_rebirth_audio_manager_observes_game_events_without_gameplay_side_effects():
    audio = read("static/js/rebirth_audio.js")
    rebirth_js = read("static/js/rebirth.js")

    for token in [
        "class RebirthAudioManager",
        "window.RebirthAudioManager = new RebirthAudioManager()",
        "AudioContext",
        "AudioBuffer",
        "decodeAudioData",
        "gainNode",
        'window.addEventListener("click", this.resumeOnGesture',
        'window.removeEventListener("click", this.resumeOnGesture',
        "impact_heavy.wav",
        "shield_shatter.wav",
        "evolution_burst.wav",
        "click_metallic.wav",
        "DAMAGE_RESOLVED",
        "SHIELD_BROKEN",
        "EVOLUTION_COMPLETED",
        "UI_CLICK_CONFIRMED",
        "replayAudioMutedMode",
        "observeEvents",
    ]:
        assert token in audio
    assert "<audio" not in audio.lower()
    assert "createOscillator" not in audio
    assert "createOscillator" not in rebirth_js
    assert "new AudioContext" not in rebirth_js
    assert "RebirthAudioManager.observeEvents(state.events || []" in rebirth_js

    product_js = read("static/js/rebirth_product.js")
    assert "monetization_disabled" in product_js
    assert "simulated" not in product_js
    assert "bindProgressionDashboard" in product_js
    assert "endpoints.ledger && endpoints.authenticated" in product_js
    assert "data-rebirth-ledger-list" in product_js
    assert "is-currency-" in product_js
    assert "applyWallet(payload.wallet)" in product_js
    assert 'pack.classList.remove("is-seal-broken")' in product_js
    assert 'pack.classList.add("is-seal-broken")' in product_js
    assert "window.clearTimeout(sealTimer)" in product_js
    assert "verifyReceipt" in read("templates/rebirth_product.html")
    assert "authenticated: {{ (page.account.authenticated if page.account is defined else false) | tojson }}" in read("templates/rebirth_product.html")
    assert 'progression: "{{ url_for(' in read("templates/rebirth_product.html")
    assert "data-rebirth-progression-dashboard" in read("templates/rebirth_product.html")
    assert "data-rebirth-xp-fill" in read("templates/rebirth_product.html")
    assert "data-rebirth-ledger-list" in read("templates/rebirth_product.html")
    assert "data-rebirth-card-option" in read("templates/rebirth_product.html")
    assert "rb-curated-collection" in read("templates/rebirth_product.html")
    assert "rb-catalog-drawer" in read("templates/rebirth_product.html")
    assert "data-rebirth-loadout-summary" in read("templates/rebirth_product.html")
    assert "data-rebirth-balance-details" in read("templates/rebirth_product.html")
    assert "data-rebirth-balance-title" in read("templates/rebirth_product.html")
    assert "data-rebirth-change-password" in read("templates/rebirth_product.html")


def test_active_home_and_rebirth_do_not_load_legacy_assets():
    home = read("templates/index.html")
    rebirth = read("templates/rebirth.html")
    product = read("templates/rebirth_product.html")
    nav = read("templates/_rebirth_global_nav.html")
    combined = home + rebirth + product

    assert 'href="/rebirth"' in nav
    assert 'href="/rebirth/shop"' in nav
    assert "rebirth_release_version" in combined
    assert "v=v71_PRODUCT_READINESS-6" not in combined
    assert "v=v74_COMBAT_REWORK-4" not in combined
    assert "v=v74_CAMPAIGN_V1-1" not in combined
    assert "v=v75_CAMPAIGN_ERA-1" not in combined
    assert "v=rebirth-058" not in combined
    assert "v=rebirth-057" not in combined
    assert "v=rebirth-056" not in combined
    assert "v=rebirth-055" not in combined
    assert "v=rebirth-054" not in combined
    assert "v=rebirth-053" not in combined
    assert "v=rebirth-051" not in combined
    assert "v=rebirth-050" not in combined
    assert "v=rebirth-047" not in combined

    for forbidden in [
        "style.css",
        "arena_clean",
        "arena3d",
        "ambitionz_theme",
        "ambitionz_progression",
        "ambitionz_ui",
        "card_system",
        "Socket.IO",
    ]:
        assert forbidden not in combined


def test_rebirth_visual_qa_captures_core_surfaces():
    visual_qa = read("tools/qa/qa_rebirth_visual_screenshots.py")
    master_report = read("tools/qa/qa_master_report.py")

    for token in [
        '"arena"',
        '"/rebirth/shop"',
        '"/rebirth/collection"',
        '"/rebirth/campaign"',
        '"mobile_arena"',
        "page.screenshot",
        "horizontal overflow",
        "RESULT=PASS rebirth_visual_screenshots",
    ]:
        assert token in visual_qa

    assert '"rebirth_visual": "tools/qa/qa_rebirth_visual_screenshots.py"' in master_report


def test_rebirth_asset_manifest_lists_existing_active_assets():
    import json

    manifest = json.loads(read("static/assets/rebirth/manifest.json"))
    paths = list(manifest["cards"].values()) + list(manifest["ui"].values()) + list(manifest["fallbacks"].values())

    for asset_path in paths:
        assert (PROJECT_ROOT / asset_path.lstrip("/")).exists()
