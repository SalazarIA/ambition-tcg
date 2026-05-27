from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_low_hp_state_class_activation():
    js = read("static/js/rebirth.js")
    css = read("static/css/rebirth.css")

    assert "lifeOrb(sideName, hp, maxHp, ratio)" in js
    assert "ratio < 0.3" in js
    assert 'classList.toggle("is-low-hp", low)' in js
    assert 'element.dataset.healthState = stateName' in js
    assert ".rb-hud-side.is-low-hp .rb-life-orb" in css
    assert "rb-low-hp-orb-pulse" in css
    assert "rb-low-hp-rune-smoke" in css


def test_rarity_frame_utility_classes():
    css = read("static/css/rebirth.css")
    js = read("static/js/rebirth.js")

    for token in [
        ".rb-tcg-card.is-rarity-common",
        ".rb-tcg-card.is-rarity-rare",
        ".rb-tcg-card.is-rarity-uncommon",
        ".rb-tcg-card.is-rarity-legendary",
        "--rarity-metal-edge",
        "--rarity-ring",
        "rb-legendary-rune-pulse",
    ]:
        assert token in css
    assert "is-rarity-${safeRarity}" in js


def test_life_orb_rendering_state_integrity():
    template = read("templates/rebirth.html")
    js = read("static/js/rebirth.js")
    css = read("static/css/rebirth.css")

    for token in [
        'class="rb-hp-meter rb-life-orb"',
        'id="player-hp-fill"',
        'id="bot-hp-fill"',
        'class="rb-life-orb__glass"',
        'class="rb-life-orb__runes"',
        'data-health-state="stable"',
    ]:
        assert token in template
    assert 'meter.dataset.hpCurrent = String(Math.max(0, hp));' in js
    assert 'meter.dataset.hpMax = String(Math.max(1, maxHp));' in js
    assert "scaleY(var(--hp-ratio))" in css
    assert "contain: layout paint;" in css


def test_combat_impact_class_toggling_stays_short_and_transform_only():
    js = read("static/js/rebirth.js")
    fx = read("static/js/rebirth_fx.js")
    audio = read("static/js/rebirth_audio.js")
    css = read("static/css/rebirth.css")

    hit_pause = re.search(r"hitPauseMs:\s*(\d+)", js)
    assert hit_pause and int(hit_pause.group(1)) <= 60
    assert 'restartClass(target, "is-taking-hit")' in js
    assert "await nextFrame();" in js
    assert "void " not in js
    assert "offsetWidth" not in js
    assert "offsetWidth" not in fx
    assert "rb-vfx-shake-heavy 180ms" in css
    assert "translate3d(-5px, 3px, 0)" in css
    assert 'soundKey === "heavy") return 0' in audio
    assert "eventPriority(event, soundKey)" in audio


def test_v73_chain_label_intensity_signals_long_resolutions():
    css = read("static/css/rebirth.css")
    js = read("static/js/rebirth.js")

    for token in [
        '#chain-label[data-intensity="rising"]',
        '#chain-label[data-intensity="heavy"]',
        "rb-chain-heavy-pulse",
    ]:
        assert token in css, f"missing CSS token: {token}"
    assert "prefers-reduced-motion" in css
    assert 'context.chain_state !== "resolvida" || context.current_phase === "COMBAT_PHASE"' in js
    assert "chainLabel.dataset.intensity = intensity" in js
    assert "chainEventCount >= 8" in js
    assert "chainEventCount >= 4" in js


def test_visual_pass_does_not_touch_authoritative_replay_or_heavy_css():
    combined_frontend = "\n".join(
        [
            read("templates/rebirth.html"),
            read("static/css/rebirth.css"),
            read("static/js/rebirth.js"),
            read("static/js/rebirth_audio.js"),
        ]
    )

    for forbidden in [
        "canonical_state_hash",
        "upgrade_schema",
        "CREATE TABLE",
        "ALTER TABLE",
        "requestAnimationFrame(requestAnimationFrame",
        "filter:",
        "backdrop-filter",
        "drop-shadow",
    ]:
        assert forbidden not in combined_frontend
