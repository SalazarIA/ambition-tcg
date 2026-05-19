from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    ]:
        assert token in template


def test_rebirth_css_locks_reference_classes_and_assets():
    css = read("static/css/rebirth.css")

    for token in [
        ".rb-clash-shell",
        ".rb-hud",
        ".rb-hud-player",
        ".rb-hud-bot",
        ".rb-turn-core",
        ".rb-slogan-grid",
        ".rb-card-back",
        ".rb-monster-card-main",
        ".rb-evolution-panel",
        ".rb-mini-card",
        ".rb-actions-row",
        ".rb-prototype-actions",
        "--rb-gold",
        "--rb-cyan",
        "@media (max-width: 720px)",
        "@media (max-width: 520px)",
    ]:
        assert token in css


def test_rebirth_js_uses_json_api_and_card_art_contract():
    js = read("static/js/rebirth.js")

    assert "fetch(" in js
    assert "Socket.IO" not in js
    assert "Rebirth3D" not in js
    for token in [
        "player-hp-fill",
        "bot-hp-fill",
        "evolution-card-thumbnail",
        "rb-mini-card",
        "card.art",
        "attack",
        "guard",
        "Combine",
        "Next Turn",
    ]:
        assert token in js
