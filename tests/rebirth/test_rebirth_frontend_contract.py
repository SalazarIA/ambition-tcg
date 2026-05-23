from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_rebirth_template_matches_premium_clash_contract():
    template = read("templates/rebirth.html")

    assert "filename='css/rebirth.css'" in template
    assert "filename='js/rebirth.js'" in template
    assert "rebirth_3d_adapter.js" not in template
    assert "Socket.IO" not in template

    for token in [
        'data-rebirth-app',
        'class="rb-game-viewport"',
        'id="rebirth-board"',
        'class="rb-hud"',
        'id="player-hp"',
        'id="player-hp-fill"',
        'id="player-energy"',
        'id="player-max-energy"',
        'id="player-deck-count"',
        'id="player-discard-count"',
        'id="turn-number"',
        'id="phase-label"',
        'id="bot-hp"',
        'id="bot-hp-fill"',
        'id="bot-energy"',
        'id="bot-max-energy"',
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
        "Zona do Bot",
        "Sua Zona",
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
        ".rb-slogans",
        ".rb-battle-zone",
        ".rb-field-card",
        ".rb-card-back",
        ".rb-main-card",
        ".rb-monster-card-main",
        ".rb-duplicate-panel",
        ".rb-evolution-panel",
        ".rb-mini-card",
        ".rb-actions-row",
        ".rb-prototype-actions",
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
        "object-fit: cover",
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
        "rb-target-line-pulse",
        "rb-result-copy-fade",
        ".rb-hand .rb-mini-card.is-locked",
        "cursor: not-allowed",
        "bot-card-back.png",
        "bot-emblem.png",
        "overflow: hidden",
    ]:
        assert token in css
    assert "filter:" not in css
    assert "backdrop-filter" not in css
    assert "drop-shadow" not in css


def test_rebirth_service_worker_caches_active_reference_assets():
    service_worker = read("static/js/service-worker.js")

    assert "ambitionz-rebirth-season0-v55" in service_worker
    assert "/rebirth/collection" in service_worker
    assert "/rebirth/profile" in service_worker
    assert "/rebirth/lab" in service_worker
    assert "/rebirth/history" not in service_worker
    assert "/rebirth/support" not in service_worker
    assert "/rebirth/onboarding" not in service_worker
    assert "/rebirth/release" not in service_worker
    assert "/static/js/rebirth_product.js" in service_worker
    assert "/static/js/rebirth_global.js" in service_worker
    assert "dreadclaw-art.png" in service_worker
    assert "bot-card-back.png" in service_worker
    assert "bot-emblem.png" in service_worker
    assert "dreadclaw.svg" not in service_worker


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
        "RebirthParallax",
        "player_field",
        "bot_field",
        "data-summon-action",
        "field_slot",
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
        "scrollRestoration",
    ]:
        assert token in js
    assert "const cardImage = this.cardImageUrl(card);" in js
    assert 'const temporary = cardImage ? "" : this.temporaryArtUrl(card);' in js

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
    assert "bindProgressionDashboard" in product_js
    assert "data-rebirth-ledger-list" in product_js
    assert "is-currency-" in product_js
    assert "applyWallet(payload.wallet)" in product_js
    assert "verifyReceipt" in read("templates/rebirth_product.html")
    assert 'progression: "{{ url_for(' in read("templates/rebirth_product.html")
    assert "data-rebirth-progression-dashboard" in read("templates/rebirth_product.html")
    assert "data-rebirth-xp-fill" in read("templates/rebirth_product.html")
    assert "data-rebirth-ledger-list" in read("templates/rebirth_product.html")
    assert "data-rebirth-card-option" in read("templates/rebirth_product.html")
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
    assert "v=rebirth-055" in combined
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


def test_rebirth_asset_manifest_lists_existing_active_assets():
    import json

    manifest = json.loads(read("static/assets/rebirth/manifest.json"))
    paths = list(manifest["cards"].values()) + list(manifest["ui"].values()) + list(manifest["fallbacks"].values())

    for asset_path in paths:
        assert (PROJECT_ROOT / asset_path.lstrip("/")).exists()
