from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_rebirth_template_references_isolated_assets_and_no_az48():
    template = read("templates/rebirth.html")

    assert "filename='css/rebirth.css'" in template
    assert "filename='js/rebirth.js'" in template
    assert "filename='js/rebirth_3d_adapter.js'" in template
    assert "az48" not in template


def test_rebirth_template_exposes_playable_contract_mounts():
    template = read("templates/rebirth.html")

    for token in [
        'id="rebirth-3d-stage"',
        'class="rb-shell"',
        "rb-game-layout",
        "rb-decision-panel",
        "rb-onboarding",
        "rb-winner-state",
        'id="rb-hand"',
        'id="rb-combat-log-list"',
        'id="rb-resolve-button"',
        "Start New Duel",
        "STRIKE",
        "GUARD",
        "FOCUS",
    ]:
        assert token in template


def test_rebirth_css_contains_cinematic_product_classes():
    css = read("static/css/rebirth.css")

    for token in [
        ".rb-page",
        ".rb-topbar",
        ".rb-alpha-badge",
        ".rb-hero",
        ".rb-game-layout",
        ".rb-stage-wrap",
        ".rb-arena-orbit",
        ".rb-energy-core",
        ".rb-avatar-node",
        ".rb-fx-ring",
        ".rb-intent-card.is-selected",
        ".rb-winner-state",
        "@media (min-width: 1100px)",
        "@media (max-width: 640px)",
    ]:
        assert token in css


def test_rebirth_js_uses_vanilla_fetch_and_3d_contract():
    js = read("static/js/rebirth.js")
    adapter = read("static/js/rebirth_3d_adapter.js")

    assert "fetch(" in js
    assert "Socket.IO" not in js
    assert "az48" not in js
    assert "ambitionz_rebirth_onboarding_seen" in js
    assert "rebirth:match_start" in js
    assert "rebirth:round_resolved" in js
    assert "window.Rebirth3D" in adapter
    for method in [
        "loadManifest()",
        "flash(type)",
        "spawnParticles(type, count)",
        "setActiveIntent(intent)",
        "setWinner(winner)",
    ]:
        assert method in adapter
