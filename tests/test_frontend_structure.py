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
    css = (PROJECT_ROOT / "static" / "css" / "arena_hud_v2.css").read_text()

    assert "arena-page-v154" in template
    assert "AMBITIONZ V1.54" in css
    assert ".arena-page-v154 .arena-board-v103" in css
