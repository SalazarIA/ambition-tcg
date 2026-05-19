#!/usr/bin/env python3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def main():
    arena = read("templates/arena_ascension.html")
    home = read("templates/index.html")
    css = read("static/css/ambitionz_ascension.css")
    service_worker = read("static/js/service-worker.js")

    for token in [
        "data-ax-viewport-contract",
        "ax-arena-shell",
        "ax-arena-viewport",
        "ax-duel-altar-compact",
        "data-ax-compact-duel",
    ]:
        assert token in arena, f"Missing Arena viewport token: {token}"

    for token in [
        "--ax-viewport-shell",
        "--ax-viewport-hand",
        "--ax-viewport-actions",
        ".ax-action-compact",
        ".ax-chronicle-compact",
        ".ax-internal-scroll",
    ]:
        assert token in css, f"Missing viewport CSS token: {token}"

    assert 'class="ax-internal-scroll"' in arena
    assert "data-ax-reachable-actions" in arena
    assert "ax-home-page" in home
    assert "ax-home-hero" in home
    assert "Ambitionz Rebirth" in home
    assert "rebirth-home-hero" in home
    assert "url_for('rebirth')" in home
    assert 'CACHE_NAME = "ambitionz-web-app-v197"' in service_worker
    print("PASS ascension_viewport_contract")


if __name__ == "__main__":
    main()
