from services.rebirth_balance import simulate_balance
from services.rebirth_bot import BOT_PERSONALITIES, choose_response, personality_payload
from services.rebirth_engine import start_match
from services.rebirth_state import public_state


def test_bot_personality_payloads_are_explicit():
    assert set(BOT_PERSONALITIES) == {"defensive", "aggressive", "opportunist"}
    assert personality_payload("aggressive")["policy"].startswith("play the highest attack")
    assert personality_payload("missing")["id"] == "defensive"


def test_bot_personalities_choose_distinct_answers():
    hand = [
        {"id": "guarded", "name": "Guarded", "attack": 6, "guard": 6, "ability_key": "brace"},
        {"id": "fang", "name": "Fang", "attack": 8, "guard": 1, "ability_key": "brace"},
        {"id": "ember", "name": "Ember", "attack": 7, "guard": 2, "ability_key": "inferno_bite"},
        {"id": "wall", "name": "Wall", "attack": 3, "guard": 9, "ability_key": "bulwark"},
    ]
    player = {"id": "player", "name": "Player", "attack": 5, "guard": 2}

    defensive = choose_response(hand, player, profile_id="defensive")
    aggressive = choose_response(hand, player, profile_id="aggressive")
    opportunist = choose_response(hand, player, profile_id="opportunist")

    assert defensive["id"] == "guarded"
    assert aggressive["id"] == "fang"
    assert opportunist["id"] == "ember"


def test_public_state_exposes_bot_profile_contract():
    match = start_match(seed="profile-contract", bot_profile_id="opportunist")
    state = public_state(match)

    assert state["bot_profile"]["id"] == "opportunist"
    assert state["bot_profile"]["name"] == "Opportunist Bot"


def test_balance_lab_reports_profiles_cards_and_abilities():
    payload = simulate_balance(matches=9)

    assert payload["matches"] == 9
    assert len(payload["profile_results"]) == 3
    assert payload["card_stats"]
    assert payload["ability_stats"]
    assert payload["samples"][0]["bot_profile"]["id"] in BOT_PERSONALITIES
