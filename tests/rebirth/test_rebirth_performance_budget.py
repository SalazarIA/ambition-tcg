from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREMIUM_ART = PROJECT_ROOT / "static/assets/rebirth/cards"
DECK_ART = PROJECT_ROOT / "static/img/cards/baralho"


def test_card_art_delivery_uses_webp_with_bounded_weight():
    premium = sorted(PREMIUM_ART.glob("*-art.webp"))
    deck = sorted(DECK_ART.glob("*.webp"))

    assert len(premium) == 13
    assert len(deck) == 100
    assert not list(PREMIUM_ART.glob("*-art.png"))
    assert not list(DECK_ART.glob("*.png"))
    assert sum(asset.stat().st_size for asset in premium) <= 2 * 1024 * 1024
    assert sum(asset.stat().st_size for asset in deck) <= 4 * 1024 * 1024


def test_first_load_does_not_eagerly_download_the_card_library():
    arena_template = (PROJECT_ROOT / "templates/rebirth.html").read_text(encoding="utf-8")
    service_worker = (PROJECT_ROOT / "static/js/service-worker.js").read_text(encoding="utf-8")
    arena_js = (PROJECT_ROOT / "static/js/rebirth.js").read_text(encoding="utf-8")

    assert arena_template.count('rel="preload" as="image"') == 1
    assert service_worker.count("/static/assets/rebirth/cards/") == 1
    assert "Object.values((manifest && manifest.cards) || {}).forEach" not in arena_js
    assert 'loading="lazy" decoding="async"' in arena_js


def test_touch_layout_has_an_explicit_mobile_budget():
    css = (PROJECT_ROOT / "static/css/rebirth.css").read_text(encoding="utf-8")
    js = (PROJECT_ROOT / "static/js/rebirth.js").read_text(encoding="utf-8")

    assert ".rb-mobile-native .rb-game-board" in css
    assert ".rb-mobile-native #play-button.rb-button-primary" in css
    assert "min-height: 52px" in css
    assert "touch-action: pan-y" in css
    assert 'document.body.classList.toggle("rb-mobile-native", nativeMobile)' in js
