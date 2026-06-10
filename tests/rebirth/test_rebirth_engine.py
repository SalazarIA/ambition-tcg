from copy import deepcopy

import pytest

from services.rebirth_engine import (
    RebirthError,
    _bot_auto_summon,
    compare_clash,
    compare_power,
    declare_attack,
    evolve_duplicate,
    evolve_bot_if_ready,
    next_turn,
    play_card,
    start_match,
)
from services.rebirth_cards import create_card_instance
from services.rebirth_state import public_state


def test_start_match_creates_valid_state_with_hands():
    match = start_match(seed="start")

    assert match["match_id"].startswith("rebirth-")
    assert match["architecture"] == "Ambitionz Rebirth"
    assert match["turn"] == 1
    assert match["phase"] == "choose"
    assert match["player"]["hp"] == 30
    assert match["bot"]["hp"] == 30
    assert match["player"]["max_hp"] == 30
    assert match["player"]["energy"] == 2
    assert match["player"]["max_energy"] == 2
    assert match["player"]["battlefield"] == []
    assert match["bot"]["battlefield"] == []
    # O deck agora é embaralhado de verdade (por seed); o contrato da abertura
    # é "ao menos um monstro jogável de custo <= 2", não uma mão fixa.
    assert any(
        card.get("type") == "MONSTER" and int(card.get("cost", 99)) <= 2
        for card in match["player"]["hand"]
    )
    assert len(match["player"]["hand"]) == 5
    assert len(match["bot"]["hand"]) == 5
    assert len(match["player"]["deck"]) == 25


def test_start_match_shuffles_custom_deck_deterministically():
    from services.rebirth_cards import PLAYER_DECK

    first = start_match(seed="shuffle-proof", player_card_ids=list(PLAYER_DECK))
    second = start_match(seed="shuffle-proof", player_card_ids=list(PLAYER_DECK))
    other = start_match(seed="shuffle-proof-2", player_card_ids=list(PLAYER_DECK))

    draw_order = [card["id"] for card in first["player"]["hand"]] + [card["id"] for card in first["player"]["deck"]]
    assert draw_order != list(PLAYER_DECK), "deck custom não pode comprar na ordem do loadout"
    assert [c["instance_id"] for c in first["player"]["hand"]] == [c["instance_id"] for c in second["player"]["hand"]]
    assert [c["instance_id"] for c in first["player"]["hand"]] != [c["instance_id"] for c in other["player"]["hand"]]


def test_mulligan_swaps_hand_once_before_first_action():
    from services.rebirth_dispatcher import MulliganCommand, dispatch_command
    from services.rebirth_engine import mulligan_available

    match = start_match(seed="mulligan-test", apply_reducers_inline=False)
    assert mulligan_available(match) is True
    before = [card["instance_id"] for card in match["player"]["hand"]]

    dispatch_command(match, MulliganCommand())

    after = [card["instance_id"] for card in match["player"]["hand"]]
    assert after != before
    assert len(after) == 5
    assert match["mulligan_used"] is True
    assert mulligan_available(match) is False
    assert any(
        card.get("type") == "MONSTER" and int(card.get("cost", 99)) <= 2
        for card in match["player"]["hand"]
    )
    with pytest.raises(RebirthError) as error:
        dispatch_command(match, MulliganCommand())
    assert error.value.code == "mulligan_unavailable"


def test_summoning_sickness_blocks_attack_without_rush():
    match = start_match(seed="sickness")
    match["player"]["energy"] = 10
    card = next(card for card in match["player"]["hand"] if card.get("type") == "MONSTER")
    match["bot"]["hand"] = []

    play_card(match, card_instance_id=card["instance_id"])
    match["turn"] = 2

    with pytest.raises(RebirthError) as error:
        declare_attack(match, attacker_instance_id=card["instance_id"])
    assert error.value.code == "summoning_sickness"

    rusher = create_card_instance("legend_infernus_core", "player", 77)
    match["player"]["hand"] = [rusher]
    match["player"]["energy"] = 10
    play_card(match, card_instance_id=rusher["instance_id"])
    result = declare_attack(match, attacker_instance_id=rusher["instance_id"])
    assert result["winner"] == "player"


def test_compare_power_returns_expected_winner():
    player = {"attack": 5}
    bot = {"attack": 3}

    assert compare_power(player, bot) == "player"
    assert compare_power(bot, player) == "bot"
    assert compare_power({"attack": 4}, {"attack": 4}) == "clash"


def test_play_card_summons_monster_to_persistent_battlefield():
    match = start_match(seed="summon")
    card = create_card_instance("card_002", "player", 1)
    match["player"]["hand"] = [card]
    match["bot"]["hand"] = [create_card_instance("card_041", "bot", 1)]

    play_card(match, card_instance_id=card["instance_id"])

    assert match["phase"] == "choose"
    assert match["turn_phase"] == "MAIN_PHASE"
    assert match["result"]["outcome"] == "Summon"
    assert match["player"]["hp"] == 30
    assert match["bot"]["hp"] == 30
    # T1 começa com 2 mana (v55); card_002 custa 1 → resta 1.
    assert match["player"]["energy"] == 1
    assert match["player"]["played_card"]["id"] == "card_002"
    assert match["player"]["battlefield"][0]["instance_id"] == card["instance_id"]
    assert match["player"]["battlefield"][0]["current_guard"] == card["guard"]
    assert match["player"]["battlefield"][0]["has_acted"] is False
    # Bot no longer auto-summons in response to the player's play. Its hand
    # card stays put until next_turn moves the action to the bot phase.
    assert match["bot"]["battlefield"] == []
    assert match["bot"]["hand"][0]["id"] == "card_041"


def test_play_card_fills_slots_in_order_and_blocks_when_battlefield_full():
    """v54 restored 3 slots per side. Summoning fills 0,1,2; the 4th attempt
    raises battlefield_full and the hand keeps the card."""
    match = start_match(seed="summon-slot")
    match["bot"]["hand"] = []

    # Mão explícita: o shuffle real não garante 3 monstros na abertura.
    cards = [
        create_card_instance("card_001", "player", 1),
        create_card_instance("card_002", "player", 2),
        create_card_instance("card_021", "player", 3),
    ]
    match["player"]["hand"] = list(cards)
    match["player"]["energy"] = 9

    for index, card in enumerate(cards):
        play_card(match, card_instance_id=card["instance_id"])
        assert match["player"]["battlefield"][index]["field_slot"] == index

    assert len(match["player"]["field"]) == 3
    assert [c["instance_id"] for c in match["player"]["field"]] == [c["instance_id"] for c in cards]

    fourth = create_card_instance("card_004", "player", 99)
    match["player"]["hand"] = [fourth]
    match["player"]["energy"] = 2

    with pytest.raises(RebirthError) as error:
        play_card(match, card_instance_id=fourth["instance_id"])

    assert error.value.code == "battlefield_full"
    assert match["player"]["hand"][0]["instance_id"] == fourth["instance_id"]


def test_first_turn_direct_damage_is_blocked_until_bot_responds():
    match = start_match(seed="direct-turn-one")
    card = create_card_instance("card_001", "player", 1)
    match["player"]["hand"] = [card]
    match["bot"]["hand"] = []

    play_card(match, card_instance_id=card["instance_id"])
    # Isola a regra de turno 1: remove o bloqueio de sickness deste cenário.
    match["player"]["battlefield"][0]["just_summoned"] = False

    with pytest.raises(RebirthError) as error:
        declare_attack(match, attacker_instance_id=card["instance_id"])

    assert error.value.code == "first_turn_direct_attack_blocked"
    assert match["bot"]["hp"] == 30
    assert match["player"]["battlefield"][0]["exhausted"] is False
    assert match["player"]["battlefield"][0]["has_acted"] is False
    assert match["last_clash"] is None


def test_equal_power_field_clash_trades_guard_without_wounding_sides():
    match = start_match(seed="tie")
    player_card = create_card_instance("card_002", "player", 1)
    match["player"]["hand"] = [player_card]

    match["bot"]["hand"] = [
        {
            "id": "test_equal",
            "name": "Equal Test",
            "type": "MONSTER",
            "card_type": "MONSTER",
            "family": "TEST",
            "role": "Beast",
            "tier": 1,
            "cost": 0,
            "attack": 5,
            "guard": 5,
            "power": 5,
            "element": "Shadow",
            "evolution_id": None,
            "ability_key": "test_card",
            "ability_name": "Test",
            "ability_text": "Test card.",
            "flavor": "Test card.",
            "art": "/static/assets/rebirth/cards/nightfang.svg",
            "instance_id": "bot-test-mist",
        }
    ]

    play_card(match, card_instance_id=player_card["instance_id"])
    # Bot no longer auto-summons during play_card; trigger it explicitly here
    # so the attack has a defender. Tests that exercise combat (this one and
    # the trap / defeated-monster tests below) all need this nudge.
    _bot_auto_summon(match)
    # Cenário roteirizado: libera o atacante da sickness do turno de invocação.
    match["player"]["battlefield"][0]["just_summoned"] = False
    result = declare_attack(
        match,
        attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    assert result["outcome"] == "Clash"
    assert result["damage"] == {"player": 5, "bot": 5}
    assert match["player"]["hp"] == 30
    assert match["bot"]["hp"] == 30
    assert match["player"]["wounded"] is False
    assert match["bot"]["wounded"] is False
    assert match["player"]["battlefield"] == []
    assert match["bot"]["battlefield"] == []
    assert any(
        event["type"] == "DAMAGE_DEALT"
        and event["payload"]["player"] == 5
        and event["payload"]["bot"] == 5
        for event in match["events"]
    )


def test_guard_trade_does_not_unlock_wounded_tiebreak_for_later_clash():
    match = start_match(seed="guard-trade-does-not-wound")
    player_card = create_card_instance("card_002", "player", 1)
    match["player"]["hand"] = [player_card]
    match["bot"]["hand"] = [create_card_instance("card_022", "bot", 1)]

    play_card(match, card_instance_id=player_card["instance_id"])
    _bot_auto_summon(match)
    match["player"]["battlefield"][0]["just_summoned"] = False
    declare_attack(
        match,
        attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    later_player = create_card_instance("card_004", "player", 2)
    later_bot = create_card_instance("card_005", "bot", 2)
    winner, clash = compare_clash(match, later_player, later_bot)

    assert winner == "clash"
    assert not any("alvo ferido" in event for event in clash["events"])


def test_evolution_by_duplicate_creates_stronger_card():
    match = start_match(seed="evolve")
    match["player"]["hand"] = [
        create_card_instance("card_001", "player", 1),
        create_card_instance("card_001", "player", 2),
        create_card_instance("card_021", "player", 3),
    ]

    evolved = evolve_duplicate(match, "card_001")

    assert evolved["id"] == "card_011"
    assert evolved["attack"] > 4
    assert evolved["tier"] == 2
    assert match["player"]["hand"][0]["id"] == "card_011"
    assert len([card for card in match["player"]["discard"] if card["id"] == "card_001"]) == 2


def test_evolution_requires_duplicate():
    match = start_match(seed="no-duplicate")

    with pytest.raises(RebirthError) as error:
        evolve_duplicate(match, "card_002")

    assert error.value.code == "duplicate_not_available"

    match = start_match(seed="no-duplicate-2")
    match["player"]["hand"] = [create_card_instance("card_001", "player", 1)]

    with pytest.raises(RebirthError) as duplicate_error:
        evolve_duplicate(match, "card_001")

    assert duplicate_error.value.code == "duplicate_not_available"


def test_match_finishes_when_hp_reaches_zero():
    match = start_match(seed="finish")
    match["bot"]["hp"] = 3
    card = create_card_instance("card_002", "player", 1)
    match["player"]["hand"] = [card]
    match["bot"]["hand"] = []

    play_card(match, card_instance_id=card["instance_id"])
    match["turn"] = 2
    match["player"]["battlefield"][0]["just_summoned"] = False
    declare_attack(match, attacker_instance_id=card["instance_id"])

    assert match["is_finished"] is True
    assert match["phase"] == "finished"
    assert match["winner"] == "player"
    assert match["player"]["battlefield"][0]["has_acted"] is True


def test_empty_deck_applies_growing_fatigue_damage():
    """A exaustão de fim-súbito virou fadiga incremental por turno."""
    match = start_match(seed="fatigue", bot_profile_id="defensive")
    match["player"]["deck"] = []
    match["player"]["hand"] = []
    match["bot"]["deck"] = []
    match["bot"]["hand"] = []
    match["player"]["hp"] = 12
    match["bot"]["hp"] = 12

    next_turn(match)
    assert match["player"]["fatigue"] == 1
    assert match["player"]["hp"] == 11
    assert match["bot"]["hp"] == 11
    assert any((event.get("type") or event.get("event_type")) == "FATIGUE_DAMAGE" for event in match["events"])

    next_turn(match)
    assert match["player"]["fatigue"] == 2
    assert match["player"]["hp"] == 9, "fadiga deve crescer 1, 2, 3..."

    # A fadiga acumula até decidir a partida — sem fim-súbito artificial.
    while not match.get("is_finished"):
        next_turn(match)
    assert match["winner"] in {"player", "bot", "clash"}
    assert match["phase"] == "finished"


def test_bot_evolves_duplicate_before_answering():
    match = start_match(seed="bot-evolve", bot_profile_id="aggressive")
    match["bot"]["hand"] = [
        create_card_instance("card_001", "bot", 1),
        create_card_instance("card_001", "bot", 2),
        create_card_instance("card_041", "bot", 3),
    ]

    evolved = evolve_bot_if_ready(match)

    assert evolved["id"] == "card_011"
    assert match["bot"]["hand"][0]["id"] == "card_011"
    assert len([card for card in match["bot"]["discard"] if card["id"] == "card_001"]) == 2
    assert "Bot evoluiu" in match["log"][-1]


def test_spell_resolves_immediately_through_effect_bus_and_discards():
    match = start_match(seed="spell")
    match["player"]["energy"] = 2
    match["player"]["max_energy"] = 2
    match["player"]["hand"] = [create_card_instance("card_081", "player", 1)]
    match["player"]["deck"] = [
        create_card_instance("card_003", "player", 2),
        create_card_instance("card_004", "player", 3),
    ]

    play_card(match, card_instance_id=match["player"]["hand"][0]["instance_id"])

    assert match["phase"] == "choose"
    assert match["turn_phase"] == "MAIN_PHASE"
    assert match["result"]["outcome"] == "Spell"
    assert [card["id"] for card in match["player"]["hand"]] == ["card_003", "card_004"]
    assert match["player"]["discard"][0]["id"] == "card_081"


def test_trap_arms_face_down_and_triggers_only_when_owner_is_attacked():
    from services.rebirth_engine import _bot_auto_attack

    match = start_match(seed="trap", bot_profile_id="aggressive")
    match["player"]["energy"] = 2
    match["player"]["max_energy"] = 2
    match["player"]["hand"] = [create_card_instance("card_091", "player", 1)]
    play_card(match, card_instance_id=match["player"]["hand"][0]["instance_id"])

    assert match["phase"] == "choose"
    assert match["player"]["traps"][0]["face_down"] is True
    assert match["player"]["traps"][0]["armed"] is True

    match["player"]["hand"] = [create_card_instance("card_002", "player", 2)]
    match["bot"]["hand"] = [create_card_instance("card_041", "bot", 1)]
    match["player"]["energy"] = 1
    match["bot"]["energy"] = 1
    play_card(match, card_instance_id=match["player"]["hand"][0]["instance_id"])
    _bot_auto_summon(match)
    match["player"]["battlefield"][0]["just_summoned"] = False

    declare_attack(
        match,
        attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    # Contexto novo: a SUA trap não pune o SEU ataque — segue armada.
    assert match["player"]["traps"], "trap do atacante não deve disparar no próprio ataque"
    assert match["player"]["traps"][0]["armed"] is True

    # Quando o BOT ataca, a trap do defensor dispara (anula o ataque).
    bot_card = next(card for card in match["bot"]["battlefield"] if card)
    bot_card["just_summoned"] = False
    bot_card["exhausted"] = False
    bot_card["has_attacked"] = False
    bot_card["has_acted"] = False
    # Garante que a heurística do bot enxergue uma troca vencedora e ataque.
    bot_card["attack"] = 7
    bot_card["power"] = 7
    bot_card["current_guard"] = 4
    player_card = next(card for card in match["player"]["battlefield"] if card)
    player_card["current_guard"] = 5
    _bot_auto_attack(match)

    assert not match["player"]["traps"]
    assert any(card["id"] == "card_091" and card["revealed"] for card in match["player"]["discard"])
    assert any("anula" in str(event) for event in match["result"]["ability_events"])


def test_defeated_monster_leaves_battlefield_and_goes_to_discard():
    """Regression: destroyed monsters used to stay on the field forever because
    field_slots() rebuilt from side["battlefield"], which was never cleared.
    """
    match = start_match(seed="defeat-removes-card")
    attacker = create_card_instance("card_002", "player", 1)
    match["player"]["hand"] = [attacker]
    weak_defender = create_card_instance("card_041", "bot", 1)
    weak_defender["guard"] = 1
    weak_defender["current_guard"] = 1
    defender_instance_id = weak_defender["instance_id"]
    match["bot"]["hand"] = [weak_defender]

    play_card(match, card_instance_id=attacker["instance_id"])
    _bot_auto_summon(match)
    match["player"]["battlefield"][0]["just_summoned"] = False
    declare_attack(
        match,
        attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    assert match["bot"]["battlefield"] == []
    assert match["bot"]["field"] == [None, None, None]
    assert any(card["instance_id"] == defender_instance_id for card in match["bot"]["discard"])

    next_turn(match)
    surviving_ids = {card.get("instance_id") for card in match["bot"]["battlefield"]}
    assert defender_instance_id not in surviving_ids, "defeated monster must not resurrect after next_turn"


def test_next_turn_resets_result_and_refills_hand():
    match = start_match(seed="next")
    original_card = deepcopy(
        next(card for card in match["player"]["hand"] if card.get("type") == "MONSTER" and int(card.get("cost", 9)) <= 2)
    )

    play_card(match, card_instance_id=original_card["instance_id"])
    next_turn(match)

    assert match["turn"] == 2
    assert match["phase"] == "choose"
    assert match["result"] is None
    assert match["player"]["played_card"] is None
    assert match["player"]["energy"] == 2
    assert match["player"]["max_energy"] == 2
    assert len(match["player"]["hand"]) == 5
    assert original_card["id"] in {card["id"] for card in match["player"]["battlefield"]}
    assert original_card["id"] not in {card["id"] for card in match["player"]["discard"]}
    assert match["player"]["battlefield"][0]["has_acted"] is False


def test_next_turn_rejects_invalid_phase():
    match = start_match(seed="next-invalid")
    match["phase"] = "combat"

    with pytest.raises(RebirthError) as error:
        next_turn(match)

    assert error.value.code == "invalid_phase"


def test_public_state_exposes_player_hand_and_hides_bot_hand():
    match = start_match(seed="public")
    match["player"]["hand"] = [
        create_card_instance("card_001", "player", 1),
        create_card_instance("card_001", "player", 2),
    ]
    state = public_state(match)

    assert "hand" in state["player"]
    assert "hand_count" in state["bot"]
    assert "hand" not in state["bot"]
    assert state["player"]["max_hp"] == 30
    assert state["player"]["battlefield"] == []
    assert state["bot"]["battlefield"] == []
    assert state["player_field"] == [None, None, None]
    assert state["bot_field"] == [None, None, None]
    assert state["available_evolutions"][0]["card_id"] == "card_001"
    assert state["mulligan_available"] is True

    for field in [
        "match_id",
        "phase",
        "turn",
        "player",
        "bot",
        "bot_profile",
        "available_evolutions",
        "last_clash",
        "result",
        "winner",
        "log",
    ]:
        assert field in state
