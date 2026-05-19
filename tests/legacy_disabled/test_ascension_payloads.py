from services.ascension_cards import get_card_by_id
from services.ascension_engine import create_match, play_card
from services.ascension_payloads import action_response, public_match_state, public_side_state


def test_payload_hides_enemy_hidden_schemes():
    match = create_match(
        seed="payload-hidden",
        opponent_deck=[
            get_card_by_id("sunken_oath"),
            get_card_by_id("crownless_warden"),
            get_card_by_id("debt_of_the_starless"),
            get_card_by_id("saint_engine"),
            get_card_by_id("mirror_break"),
        ],
    )
    play_card(match, "opponent", "sunken_oath", mode="set")

    payload = public_match_state(match, perspective="player")

    assert payload["opponent"]["schemes_count"] == 1
    assert payload["opponent"]["schemes"][0]["name"] == "Prepared Scheme"
    assert "Sunken Oath" not in str(payload["opponent"]["schemes"])
    assert payload["opponent"]["hand"] == []


def test_public_side_state_exposes_own_safe_data():
    match = create_match(seed="payload-own")
    side = public_side_state(match["player"], hide_hidden=False)

    assert "hand" in side
    assert side["echo_count"] == 0
    assert side["hp"] == 30


def test_action_response_includes_legal_actions():
    match = create_match(seed="payload-action")
    payload = action_response(match)

    assert payload["ok"] is True
    assert payload["match"]["version"] == "ascension_duel_v1"
    assert payload["match"]["bot_profile"]["label"] == "Controller"
    assert "actions" in payload
    assert payload["actions"]["cards"]
