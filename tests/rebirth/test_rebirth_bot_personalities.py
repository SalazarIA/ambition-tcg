from services.rebirth_balance import simulate_balance
from services.rebirth_bot import BOT_PERSONALITIES, choose_bot_attack, choose_response, personality_payload, tactical_utility_matrix
from services.rebirth_contracts import FIELD_SLOT_COUNT
from services.rebirth_engine import start_match
from services.rebirth_state import public_state


def test_bot_personality_payloads_are_explicit():
    assert set(BOT_PERSONALITIES) == {"defensive", "aggressive", "opportunist", "novice"}
    assert personality_payload("aggressive")["policy"].startswith("joga o maior ataque")
    assert personality_payload("novice")["policy"].startswith("invoca a carta mais leve")
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
    assert state["bot_profile"]["name"] == "Bot Oportunista"


def test_balance_lab_reports_profiles_cards_and_abilities():
    payload = simulate_balance(matches=9)

    assert payload["matches"] == 9
    assert len(payload["profile_results"]) == 3
    assert payload["card_stats"]
    assert payload["ability_stats"]
    assert payload["samples"][0]["bot_profile"]["id"] in BOT_PERSONALITIES


def test_bot_refuses_high_tier_symmetric_suicide_without_lethal_window():
    bot_card = {
        "id": "bot_tier_high",
        "instance_id": "bot-high",
        "name": "Bot High",
        "attack": 8,
        "guard": 8,
        "current_guard": 8,
        "tier": 2,
        "ability_key": "brace",
    }
    player_card = {
        "id": "player_equal",
        "instance_id": "player-equal",
        "name": "Player Equal",
        "attack": 8,
        "guard": 8,
        "current_guard": 8,
        "tier": 1,
    }

    matrix = tactical_utility_matrix([bot_card], [player_card], player_hp=30)
    decision = choose_bot_attack([bot_card], [player_card], player_hp=30)

    assert matrix[0]["allowed"] is False
    assert matrix[0]["reason"] == "refuse_high_tier_suicide"
    assert decision is None


def test_bot_accepts_high_tier_trade_when_remaining_board_has_lethal():
    bot_card = {
        "id": "bot_tier_high",
        "instance_id": "bot-high",
        "name": "Bot High",
        "attack": 8,
        "guard": 8,
        "current_guard": 8,
        "tier": 2,
    }
    finisher = {
        "id": "bot_finisher",
        "instance_id": "bot-finisher",
        "name": "Bot Finisher",
        "attack": 9,
        "guard": 4,
        "current_guard": 4,
        "tier": 1,
    }
    player_card = {
        "id": "player_equal",
        "instance_id": "player-equal",
        "name": "Player Equal",
        "attack": 8,
        "guard": 8,
        "current_guard": 8,
        "tier": 1,
    }

    decision = choose_bot_attack([bot_card, finisher], [player_card], player_hp=9)

    assert decision["allowed"] is True
    assert decision["reason"] == "lethal_window"
    assert decision["remaining_damage"]["total"] == 9


def test_bot_direct_attack_matrix_skips_acted_cards_and_marks_open_board_lethal():
    acted = {
        "id": "spent",
        "instance_id": "spent-1",
        "name": "Spent",
        "attack": 20,
        "guard": 2,
        "tier": 1,
        "has_acted": True,
    }
    active_cards = [
        {"id": "direct-a", "instance_id": "direct-a-1", "name": "A", "attack": 6, "guard": 2, "tier": 1},
        {"id": "direct-b", "instance_id": "direct-b-1", "name": "B", "attack": 5, "guard": 2, "tier": 1},
    ]

    matrix = tactical_utility_matrix([acted, *active_cards], [], player_hp=11)
    decision = choose_bot_attack([acted, *active_cards], [], player_hp=11)

    assert {row["attacker_id"] for row in matrix} == {"direct-a", "direct-b"}
    assert all(row["target_id"] is None and row["reason"] == "direct_lethal" for row in matrix)
    assert all(row["utility"] >= 5000 for row in matrix)
    assert decision["attacker_id"] in {"direct-a", "direct-b"}


def test_tactical_matrix_clamps_stale_oversized_boards_to_three_slots():
    stale_cards = [
        {"id": f"bot-{index}", "instance_id": f"bot-{index}-1", "attack": 1, "guard": 1, "tier": 1}
        for index in range(FIELD_SLOT_COUNT + 1)
    ]

    matrix = tactical_utility_matrix(stale_cards, [], player_hp=30)

    assert FIELD_SLOT_COUNT == 3
    assert {row["attacker_id"] for row in matrix} == {"bot-0", "bot-1", "bot-2"}
