from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_deck_builder_uses_data_actions_instead_of_inline_click_handlers():
    template = (PROJECT_ROOT / "templates" / "deck_builder.html").read_text()

    assert "onclick=" not in template
    assert "onchange=" not in template
    assert "oninput=" not in template
    assert 'data-deck-action="add"' in template
    assert 'data-deck-action="remove"' in template
    assert "data-quick-filter-kind" in template


def test_support_page_uses_scoped_css_module():
    template = (PROJECT_ROOT / "templates" / "support.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "support.css").read_text()

    assert "css/support.css" in template
    assert "support-page" in template
    assert ".support-page" in css


def test_arena_keeps_socket_critical_ids_after_ux_polish():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    required_ids = [
        "join-queue-btn",
        "ready-btn",
        "join-private-room-btn",
        "join-bot-match-btn",
        "private-room-code",
        "queue-status",
        "battle-log",
        "hand",
        "my-name",
        "enemy-name",
        "my-hp",
        "enemy-hp",
        "my-deck",
        "enemy-deck",
        "my-ready",
        "enemy-ready",
        "my-monster-slot",
        "enemy-monster-slot",
        "my-st-slot",
        "enemy-st-slot",
        "phase-label",
        "round-label",
    ]

    for element_id in required_ids:
        assert f'id="{element_id}"' in template


def test_arena_uses_single_screen_layout_module():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "arena-page-v154" in template
    assert "css/arena_clean_v48.css" in template
    assert "css/arena3d.css" in template
    assert "js/arena_renderer_adapter.js" in template
    assert "js/arena_clean_v48.js" in template
    assert "dist/arena3d/arena3d.js" in template
    assert "data-arena-renderer" in template
    assert ".az48-arena" in css
    assert ".az48-card-v2" in css


def test_pwa_install_assets_are_declared():
    manifest = (PROJECT_ROOT / "static" / "manifest.webmanifest").read_text()
    pwa_js = (PROJECT_ROOT / "static" / "js" / "pwa.js").read_text()
    service_worker = (PROJECT_ROOT / "static" / "js" / "service-worker.js").read_text()
    homepage = (PROJECT_ROOT / "templates" / "index.html").read_text()

    assert '"/static/icons/icon-192.png"' in manifest
    assert '"/static/icons/icon-512.png"' in manifest
    assert '"/static/icons/maskable-icon-512.png"' in manifest
    assert '"display": "standalone"' in manifest
    assert 'navigator.serviceWorker.register("/service-worker.js", { scope: "/" })' in pwa_js
    assert 'CACHE_NAME = "ambitionz-web-app-v156"' in service_worker
    assert '"/static/js/arena_clean_v48.js"' in service_worker
    assert '"/static/dist/arena3d/arena3d.js"' in service_worker
    assert '"/static/assets/arena3d/manifest.json"' in service_worker
    assert "apple-touch-icon.png" in homepage
