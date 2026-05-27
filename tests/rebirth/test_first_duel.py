"""Contract tests for the scripted first-duel onboarding flow.

The first duel must:
- expose `first_duel=True` in the public state
- give the bot reduced HP for ultra-short pacing
- use the `novice` bot profile so the AI under-plays
- still pass when invoked without the flag (regression guard for prod flow)
"""

from services.rebirth_bot import (
    BOT_PERSONALITIES,
    choose_novice,
    choose_response,
    personality_payload,
)
from services.rebirth_engine import start_match
from services.rebirth_serializers import public_state
from services.rebirth_state import FIRST_DUEL_BOT_HP, STARTING_HP


def test_novice_personality_is_registered():
    assert "novice" in BOT_PERSONALITIES
    payload = personality_payload("novice")
    assert payload["id"] == "novice"
    assert payload["name"] == "Bot Iniciante"


def test_choose_novice_picks_weakest_card():
    hand = [
        {"id": "tank", "name": "Tank", "attack": 2, "guard": 9, "ability_key": "bulwark"},
        {"id": "fang", "name": "Fang", "attack": 8, "guard": 1, "ability_key": "brace"},
        {"id": "ember", "name": "Ember", "attack": 7, "guard": 2, "ability_key": "inferno_bite"},
    ]
    player = {"id": "player", "name": "Player", "attack": 5, "guard": 2}

    decision = choose_response(hand, player, profile_id="novice")
    direct_choice = choose_novice(hand, player)

    # novice prefers the lowest-attack body (Tank, atk 2) — the "mistake" play
    assert decision["id"] == "tank"
    assert direct_choice["id"] == "tank"


def test_start_match_first_duel_drops_bot_hp_and_marks_state():
    match = start_match(seed="first-duel-state", first_duel=True, bot_profile_id="novice")
    state = public_state(match)

    assert state["first_duel"] is True
    assert state["bot"]["hp"] == FIRST_DUEL_BOT_HP
    assert state["bot"]["max_hp"] == FIRST_DUEL_BOT_HP
    assert state["player"]["hp"] == STARTING_HP
    assert state["player"]["max_hp"] == STARTING_HP
    assert state["bot_profile"]["id"] == "novice"


def test_start_match_without_first_duel_keeps_full_hp():
    match = start_match(seed="normal-match-state")
    state = public_state(match)

    assert state["first_duel"] is False
    assert state["bot"]["hp"] == STARTING_HP
    assert state["player"]["hp"] == STARTING_HP


def test_api_start_with_tutorial_flag_activates_first_duel(client):
    response = client.post("/api/rebirth/start", json={"tutorial": True})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    state = payload["state"]
    assert state["first_duel"] is True
    assert state["bot"]["hp"] == FIRST_DUEL_BOT_HP
    assert state["bot_profile"]["id"] == "novice"
    # Player still has full HP — the asymmetry is the whole point.
    assert state["player"]["hp"] == STARTING_HP


def test_api_start_without_flag_keeps_standard_duel(client):
    response = client.post("/api/rebirth/start", json={"seed": "no-tutorial"})
    payload = response.get_json()

    assert response.status_code == 200
    state = payload["state"]
    assert state["first_duel"] is False
    assert state["bot"]["hp"] == STARTING_HP
    # Novice should NOT appear unless explicitly requested.
    assert state["bot_profile"]["id"] in {"defensive", "aggressive", "opportunist"}


def test_new_account_followup_duels_use_defensive_learning_curve(client):
    client.post(
        "/api/rebirth/auth/register",
        json={"username": "curve_user", "email": "curve-user@example.com", "password": "password123"},
    )

    state = client.post("/api/rebirth/start", json={"seed": "post-guide-curve"}).get_json()["state"]

    assert state["first_duel"] is False
    assert state["bot_profile"]["id"] == "defensive"
