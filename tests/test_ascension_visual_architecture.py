from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_home_uses_rebirth_shell_and_primary_ctas():
    home = read("templates/index.html")

    assert "ax-home-page" in home
    assert "ax-product-shell" in home
    assert "Ambitionz Rebirth" in home
    assert "url_for('rebirth')" in home
    assert "rebirth-home-hero" in home
    assert "Legacy Access" in home


def test_training_template_declares_viewport_contract():
    arena = read("templates/arena_ascension.html")
    css = read("static/css/ambitionz_ascension.css")

    assert "data-ax-viewport-contract" in arena
    assert "ax-arena-viewport" in arena
    assert "ax-duel-altar-compact" in arena
    assert "ax-action-compact" in arena
    assert "ax-internal-scroll" in arena
    assert "--ax-viewport-shell" in css
    assert ".ax-arena-shell" in css
    assert ".ax-action-compact" in css


def test_public_ascension_pages_share_shell():
    for template_name in [
        "collection_ascension.html",
        "deck_builder_ascension.html",
        "ascension_history.html",
        "roadmap.html",
        "tutorial.html",
    ]:
        template = read(f"templates/{template_name}")
        assert "ax-body" in template
        assert "ax-shell" in template
        assert "ax-product-shell" in template
        assert "ambitionz_ascension.css" in template


def test_public_ascension_templates_do_not_link_legacy_as_primary_surface():
    combined = "\n".join(
        read(f"templates/{name}")
        for name in [
            "arena_ascension.html",
            "collection_ascension.html",
            "deck_builder_ascension.html",
            "ascension_history.html",
            "tutorial.html",
        ]
    )

    assert "training_legacy" not in combined
    assert "/training-legacy" not in combined
    assert "Legacy Arena" not in combined


def test_home_and_public_routes_render_new_product_language(client):
    for path in ["/", "/roadmap", "/tutorial"]:
        response = client.get(path)
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Ambitionz Rebirth" in body if path == "/" else "Ascension Duel" in body
        if path == "/":
            assert "Legacy Access" in body
            assert 'href="/rebirth"' in body
        else:
            assert "/training-legacy" not in body
        assert "monster" not in body.lower()
        assert "spell" not in body.lower()
        assert "trap" not in body.lower()
        assert "lane" not in body.lower()
