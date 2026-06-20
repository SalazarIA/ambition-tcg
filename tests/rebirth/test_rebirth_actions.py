from copy import deepcopy
import json

from services.rebirth_actions import (
    action_to_command,
    canonical_action,
    command_for_action,
    legal_actions,
    simulate_action,
)
from services.rebirth_cards import create_card_instance
from services.rebirth_dispatcher import (
    DeclareAttackCommand,
    EndTurnCommand,
    EvolveDuplicateCommand,
    MulliganCommand,
    SummonCardCommand,
    dispatch_command,
)
from services.rebirth_engine import start_match


def _action(actions, action_type, **payload):
    return next(
        action
        for action in actions
        if action["type"] == action_type
        and all(action["payload"].get(key) == value for key, value in payload.items())
    )


def _ready(card, slot):
    card["field_slot"] = slot
    card["slot"] = slot + 1
    card["current_guard"] = int(card.get("guard", 0) or 0)
    card["max_guard"] = int(card.get("guard", 0) or 0)
    card["exhausted"] = False
    card["has_attacked"] = False
    card["has_acted"] = False
    card["just_summoned"] = False
    return card


def test_canonical_action_is_stable_and_json_serializable():
    first = canonical_action(
        "play_card",
        actor="player",
        target_instance_id="bot-2",
        card_instance_id="player-1",
        field_slot=0,
    )
    second = canonical_action(
        "play_card",
        field_slot=0,
        card_instance_id="player-1",
        target_instance_id="bot-2",
    )

    assert first == second
    assert list(first) == ["version", "type", "actor", "payload"]
    assert list(first["payload"]) == ["card_instance_id", "field_slot", "target_instance_id"]
    assert json.loads(json.dumps(first, sort_keys=True)) == first


def test_action_to_command_maps_every_basic_action():
    assert isinstance(action_to_command(canonical_action("mulligan")), MulliganCommand)
    assert isinstance(
        action_to_command(canonical_action("play_card", card_instance_id="p-1", field_slot=2)),
        SummonCardCommand,
    )
    assert isinstance(
        action_to_command(canonical_action("attack", attacker_instance_id="p-1", target_instance_id="b-1")),
        DeclareAttackCommand,
    )
    assert isinstance(action_to_command(canonical_action("evolve", card_id="card_001")), EvolveDuplicateCommand)
    assert isinstance(action_to_command(canonical_action("end_turn", turn=3)), EndTurnCommand)
    assert command_for_action({"type": "end_turn", "turn": 4}).turn == 4


def test_legal_actions_does_not_mutate_match_and_lists_basic_actions():
    match = start_match(seed="actions-basic")
    cheap_monster = create_card_instance("card_021", "player", 501)
    spell = create_card_instance("card_081", "player", 502)
    trap = create_card_instance("card_091", "player", 503)
    match["player"]["hand"] = [cheap_monster, spell, trap]
    match["player"]["energy"] = 10
    before = deepcopy(match)

    actions = legal_actions(match)

    assert match == before
    assert _action(actions, "mulligan")
    for slot in range(3):
        assert _action(actions, "play_card", card_instance_id=cheap_monster["instance_id"], field_slot=slot)
    assert _action(actions, "play_card", card_instance_id=spell["instance_id"])
    assert _action(actions, "play_card", card_instance_id=trap["instance_id"])
    assert _action(actions, "end_turn", turn=1)


def test_legal_actions_respects_energy_sickness_exhaustion_and_taunt():
    match = start_match(seed="actions-combat")
    match["turn"] = 2
    expensive = create_card_instance("card_011", "player", 601)
    match["player"]["hand"] = [expensive]
    match["player"]["energy"] = 0

    ready = _ready(create_card_instance("card_021", "player", 602), 0)
    sick = _ready(create_card_instance("card_022", "player", 603), 1)
    sick["just_summoned"] = True
    exhausted = _ready(create_card_instance("card_023", "player", 604), 2)
    exhausted["exhausted"] = True
    match["player"]["field"] = [ready, sick, exhausted]
    match["player"]["battlefield"] = [ready, sick, exhausted]

    taunt = _ready(create_card_instance("card_041", "bot", 605), 0)
    taunt["keywords"] = sorted(set(list(taunt.get("keywords") or []) + ["TAUNT"]))
    ordinary = _ready(create_card_instance("card_042", "bot", 606), 1)
    match["bot"]["field"] = [taunt, ordinary, None]
    match["bot"]["battlefield"] = [taunt, ordinary]

    actions = legal_actions(match)
    attacks = [action for action in actions if action["type"] == "attack"]

    assert not any(action["payload"].get("card_instance_id") == expensive["instance_id"] for action in actions)
    assert attacks == [
        canonical_action(
            "attack",
            attacker_instance_id=ready["instance_id"],
            target_instance_id=taunt["instance_id"],
        )
    ]


def test_targetable_spell_lists_hero_and_each_live_enemy_unit():
    match = start_match(seed="actions-spell-targets")
    spell = create_card_instance("card_084", "player", 701)
    match["player"]["hand"] = [spell]
    match["player"]["energy"] = 10
    first = _ready(create_card_instance("card_041", "bot", 702), 0)
    second = _ready(create_card_instance("card_042", "bot", 703), 2)
    match["bot"]["field"] = [first, None, second]
    match["bot"]["battlefield"] = [first, second]

    plays = [
        action
        for action in legal_actions(match)
        if action["type"] == "play_card" and action["payload"].get("card_instance_id") == spell["instance_id"]
    ]

    assert {action["payload"].get("target_instance_id") for action in plays} == {
        None,
        first["instance_id"],
        second["instance_id"],
    }


def test_evolution_and_attack_actions_are_dispatcher_legal():
    match = start_match(seed="actions-evolve")
    first = create_card_instance("card_001", "player", 801)
    second = create_card_instance("card_001", "player", 802)
    attacker = _ready(create_card_instance("card_021", "player", 803), 0)
    defender = _ready(create_card_instance("card_041", "bot", 804), 0)
    match["turn"] = 2
    match["player"]["hand"] = [first, second]
    match["player"]["field"] = [attacker, None, None]
    match["player"]["battlefield"] = [attacker]
    match["bot"]["field"] = [defender, None, None]
    match["bot"]["battlefield"] = [defender]

    actions = legal_actions(match)
    evolve = _action(actions, "evolve", card_id="card_001")
    attack = _action(
        actions,
        "attack",
        attacker_instance_id=attacker["instance_id"],
        target_instance_id=defender["instance_id"],
    )

    assert simulate_action(match, evolve)["error"] is None
    assert simulate_action(match, attack)["error"] is None


def test_simulate_action_preserves_original_and_matches_real_dispatcher():
    original = start_match(seed="actions-parity")
    monster = create_card_instance("card_021", "player", 901)
    original["player"]["hand"] = [monster]
    original["player"]["energy"] = 10
    before = deepcopy(original)
    action = canonical_action("play_card", card_instance_id=monster["instance_id"], field_slot=1)

    simulation = simulate_action(original, action)
    repeated = simulate_action(original, action)
    dispatched = deepcopy(original)
    expected_result = dispatch_command(dispatched, action_to_command(action))

    assert original == before
    assert simulation["error"] is None
    assert repeated == simulation
    assert simulation["state"] == dispatched
    assert simulation["result"] == expected_result


def test_failed_simulation_returns_error_and_unchanged_state():
    match = start_match(seed="actions-invalid")
    before = deepcopy(match)
    invalid = canonical_action("attack", attacker_instance_id="missing")

    simulation = simulate_action(match, invalid)

    assert match == before
    assert simulation["state"] == before
    assert simulation["result"] is None
    assert simulation["error"]["code"] == "invalid_attacker"
