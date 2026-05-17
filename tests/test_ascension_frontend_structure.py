from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_new_template_contains_required_ascension_regions():
    template = (PROJECT_ROOT / "templates" / "arena_ascension.html").read_text()

    for token in [
        "ax-shell",
        "ax-duel-altar",
        "ax-enemy-champion",
        "ax-clash-axis",
        "ax-player-champion",
        "ax-ambition-core",
        "ax-bound-souls",
        "ax-relic",
        "ax-schemes",
        "ax-hand",
        "ax-card",
        "ax-mode-picker",
        "ax-chronicle",
        "ax-commit-button",
        "ax-intent-ring",
        "ax-reward-panel",
        "ax-onboarding",
    ]:
        assert token in template


def test_new_frontend_does_not_depend_on_old_arena_runtime_markers():
    template = (PROJECT_ROOT / "templates" / "arena_ascension.html").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "ambitionz_ascension.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "ambitionz_ascension.css").read_text()

    combined = "\n".join([template, js, css]).lower()

    assert "az48" not in combined
    assert "arena_clean_v48" not in combined
    assert "data-az48-lane" not in combined
    assert "my-monster-slot" not in combined
    assert "enemy-monster-slot" not in combined
    assert "lane" not in combined


def test_service_worker_caches_ascension_assets():
    service_worker = (PROJECT_ROOT / "static" / "js" / "service-worker.js").read_text()

    assert 'CACHE_NAME = "ambitionz-web-app-v193"' in service_worker
    assert '"/static/css/ambitionz_ascension.css"' in service_worker
    assert '"/static/js/ambitionz_ascension.js"' in service_worker
    assert '"/static/js/ambitionz_ascension_library.js"' in service_worker


def test_ascension_library_frontend_contract():
    collection = (PROJECT_ROOT / "templates" / "collection_ascension.html").read_text()
    builder = (PROJECT_ROOT / "templates" / "deck_builder_ascension.html").read_text()
    library_js = (PROJECT_ROOT / "static" / "js" / "ambitionz_ascension_library.js").read_text()

    assert "data-ax-filter-type" in collection
    assert "ax-card-detail" in collection
    assert "Ascension Deck" in builder
    assert "bindFilters" in library_js
    assert "bindDetails" in library_js
