from services.rebirth.rebirth_engine import play_rebirth_card, start_rebirth_match
from services.rebirth.rebirth_payloads import available_actions, compact_card, public_rebirth_state


def test_public_rebirth_state_hides_decks_and_exposes_expected_keys():
    match = start_rebirth_match(seed="payload-a")
    payload = public_rebirth_state(match)

    for key in [
        "match_id",
        "phase",
        "round",
        "player",
        "opponent",
        "active_card",
        "hand",
        "available_actions",
        "selected_intent",
        "combat_log",
        "cinematic_event",
        "ui_flags",
        "winner",
        "is_finished",
    ]:
        assert key in payload

    assert "deck" not in payload
    assert "deck" not in payload["player"]
    assert "deck" not in payload["opponent"]
    assert "hand" not in payload["opponent"]


def test_available_actions_is_stable_list():
    match = start_rebirth_match(seed="payload-actions")
    actions = available_actions(match)

    assert isinstance(actions, list)
    assert {action["type"] for action in actions} >= {"intent", "play_card", "resolve", "restart"}


def test_active_card_uses_compact_card():
    match = start_rebirth_match(seed="payload-card")
    card_id = match["player"]["hand"][0]["id"]
    card = play_rebirth_card(match, "player", card_id)
    payload = public_rebirth_state(match)

    assert payload["player"]["active_card"] == compact_card(card)
    assert "model_key" in payload["player"]["active_card"]
    assert "fx_key" in payload["player"]["active_card"]

