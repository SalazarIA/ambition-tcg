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
