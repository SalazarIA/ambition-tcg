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
        'id="turn-number"',
        'id="bot-hp"',
        'id="bot-hp-fill"',
        'id="bot-card"',
        'id="focus-card"',
        'id="evolution-panel"',
        'id="evolution-card-thumbnail"',
        'id="player-hand"',
        'id="play-button"',
        'id="next-turn-button"',
        'id="result-panel"',
        'id="turn-log"',
        "One card.",
        "One decision.",
        "One clash.",
        "Combine duplicates.",
        "Evolve monsters.",
        "Win the duel.",
        "Play Rebirth Prototype",
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
        "--rb-gold",
        "--rb-cyan",
        "bot-card-back.png",
        "bot-emblem.png",
        "overflow: hidden",
    ]:
        assert token in css


def test_rebirth_service_worker_caches_active_reference_assets():
    service_worker = read("static/js/service-worker.js")

    assert "ambitionz-rebirth-release-hygiene-v6" in service_worker
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
        "player-hp-fill",
        "bot-hp-fill",
        "evolution-card-thumbnail",
        "rb-mini-card",
        "card.art",
        "attack",
        "guard",
        "Combine",
        "Next Turn",
        "scrollRestoration",
    ]:
        assert token in js


def test_active_home_and_rebirth_do_not_load_legacy_assets():
    home = read("templates/index.html")
    rebirth = read("templates/rebirth.html")
    combined = home + rebirth

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
