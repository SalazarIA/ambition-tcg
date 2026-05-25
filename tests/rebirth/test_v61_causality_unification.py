from copy import deepcopy

import pytest

from services.rebirth_bot import MCTSAgent, heuristic_vector, threat_score
from services.rebirth_cards import create_card_instance
from services.rebirth_contracts import RebirthError
from services.rebirth_dispatcher import DeclareAttackCommand, PIPELINE_STAGES, SummonCardCommand
from services.rebirth_domain import (
    REDUCER_VERSION,
    REPLAY_SCHEMA_VERSION,
    RULESET_VERSION,
    canonical_state_hash,
    serialize_canonical_state,
)
from services.rebirth_effects import EffectBus
from services.rebirth_events import append_event, validate_event_ordering
from services.rebirth_reducers import REDUCER_ORDER, reduce_event, reduce_events
from services.rebirth_engine import declare_attack, start_match
from services.rebirth_replay import build_replay_envelope, replay_match
from services.rebirth_state import compact_battlefield


def battlefield_card(card_id, owner, sequence, slot, *, attack=None, guard=None):
    card = create_card_instance(card_id, owner, sequence)
    if attack is not None:
        card["attack"] = attack
        card["power"] = attack
    if guard is not None:
        card["guard"] = guard
    card["owner_side"] = owner
    card["field_slot"] = slot
    card["slot"] = slot + 1
    card["current_guard"] = int(card.get("guard", 0) or 0)
    card["max_guard"] = int(card.get("guard", 0) or 0)
    card["exhausted"] = False
    card["has_attacked"] = False
    card["has_acted"] = False
    card["statuses"] = {}
    return card


def place(match, side_name, card):
    match[side_name]["field"][int(card["field_slot"])] = card
    compact_battlefield(match[side_name])
    return card


def event_of(match, event_type):
    return next(event for event in match["events"] if event["type"] == event_type)


def test_v61_command_model_names_the_single_pipeline():
    assert PIPELINE_STAGES == (
        "COMMAND",
        "VALIDATE",
        "BUILD_EFFECT_STACK",
        "RESOLVE_EFFECTS",
        "REDUCER_PHASE",
        "EMIT_EVENTS",
        "PERSIST_SNAPSHOT",
    )
    assert SummonCardCommand(card_instance_id="c1", field_slot=0).command_type == "PLAY_CARD"
    assert DeclareAttackCommand(attacker_instance_id="a", target_instance_id="t").as_payload()["target_instance_id"] == "t"


def test_v61_reducer_is_pure_and_does_not_mutate_input_state():
    match = start_match(seed="v61-reducer-purity")
    card = place(match, "player", battlefield_card("legend_infernus_core", "player", 1, 0))
    original = deepcopy(match)
    event = {
        "event_type": "STAT_MODIFIER_APPLIED",
        "target_id": card["instance_id"],
        "payload": {"stat": "attack", "amount": 2, "duration": "permanent"},
    }

    reduced = reduce_event(match, event)

    assert match == original
    assert reduced != match
    assert reduced["player"]["battlefield"][0]["attack"] == card["attack"] + 2


def test_v61_reducer_ordering_is_canonical_and_deterministic():
    assert REDUCER_ORDER == tuple(sorted(REDUCER_ORDER))
    match = start_match(seed="v61-reducer-ordering")
    card = place(match, "player", battlefield_card("legend_infernus_core", "player", 1, 0))
    match["player"]["energy"] = 3
    events = [
        {"event_type": "STAT_MODIFIER_APPLIED", "sequence_id": 2, "target_id": card["instance_id"], "payload": {"stat": "attack", "amount": 2, "duration": "permanent"}},
        {"event_type": "RESOURCE_CONSUMED", "sequence_id": 1, "owner_id": "player", "payload": {"resource": "mana", "amount": 1}},
    ]

    forward = reduce_events(match, events)
    reversed_result = reduce_events(match, list(reversed(events)))

    assert canonical_state_hash(forward) == canonical_state_hash(reversed_result)
    assert forward["player"]["energy"] == 2
    assert forward["player"]["battlefield"][0]["attack"] == 8


def test_v61_effect_bus_applies_reducers_and_reconstructs_from_events():
    match = start_match(seed="v61-event-sourcing")
    card = place(match, "player", battlefield_card("legend_infernus_core", "player", 1, 0))
    match["player"]["energy"] = 3
    base = deepcopy(match)
    bus = EffectBus(match, effect_chain_id="v61-chain")
    bus.dispatch("RESOURCE_CONSUMED", actor="player", owner_id="player", target_id=card["instance_id"], payload={"resource": "mana", "amount": 1})
    bus.dispatch("STAT_MODIFIER_APPLIED", actor="player", owner_id="player", target_id=card["instance_id"], payload={"stat": "attack", "amount": 2, "duration": "permanent"}, chain_from_previous=True)
    emitted = bus.flush()

    reconstructed = reduce_events(base, emitted)

    assert match["player"]["energy"] == 2
    assert match["player"]["battlefield"][0]["attack"] == 8
    assert canonical_state_hash(reconstructed) == canonical_state_hash(match)


def test_v61_causal_tree_propagates_parent_and_root_ids_through_attack_chain():
    match = start_match(seed="v61-causal-tree")
    attacker = place(match, "player", battlefield_card("legend_infernus_core", "player", 1, 0))
    target = place(match, "bot", battlefield_card("card_021", "bot", 1, 0, attack=2, guard=3))
    match["player"]["energy"] = 3

    declare_attack(match, attacker_instance_id=attacker["instance_id"], target_instance_id=target["instance_id"])

    attack = event_of(match, "ATTACK_DECLARED")
    damage = event_of(match, "DAMAGE_RESOLVED")
    survived = event_of(match, "UNIT_SURVIVED_COMBAT")
    resource = event_of(match, "RESOURCE_CONSUMED")
    stat = event_of(match, "STAT_MODIFIER_APPLIED")
    assert damage["parent_event_id"] == attack["event_id"]
    assert survived["parent_event_id"] == damage["event_id"]
    assert resource["parent_event_id"] == survived["event_id"]
    assert stat["parent_event_id"] == resource["event_id"]
    assert {event["root_event_id"] for event in (attack, damage, survived, resource, stat)} == {attack["event_id"]}


def test_v61_events_include_reducer_and_ruleset_versions():
    match = start_match(seed="v61-event-versions")
    event = append_event(match, "TARGET_SELECTED", payload={"target": "x"})

    assert event["reducer_version"] == REDUCER_VERSION
    assert event["ruleset_version"] == RULESET_VERSION


def test_v61_replay_rejects_reducer_ruleset_and_schema_mismatches():
    match = start_match(seed="v61-replay-version")
    envelope = build_replay_envelope(match)

    for field, code in (
        ("reducer_version", "replay_reducer_mismatch"),
        ("ruleset_version", "replay_ruleset_mismatch"),
        ("replay_schema_version", "replay_schema_mismatch"),
    ):
        corrupted = deepcopy(envelope)
        corrupted[field] = "old"
        with pytest.raises(RebirthError) as error:
            replay_match(corrupted)
        assert error.value.code == code


def test_v61_replay_envelope_freezes_required_versions_and_frame_count():
    match = start_match(seed="v61-replay-envelope")
    envelope = build_replay_envelope(match)

    assert envelope["ruleset_version"] == RULESET_VERSION
    assert envelope["reducer_version"] == REDUCER_VERSION
    assert envelope["replay_schema_version"] == REPLAY_SCHEMA_VERSION
    assert envelope["deterministic_seed"] == match["game_seed"]
    assert envelope["canonical_state_hash"] == canonical_state_hash(match)
    assert envelope["replay_frame_count"] == len(match["events"])


def test_v61_event_ordering_validator_detects_out_of_order_sequences():
    assert validate_event_ordering([{"sequence_id": 1}, {"sequence_id": 2}]) is True
    assert validate_event_ordering([{"sequence_id": 2}, {"sequence_id": 1}]) is False


def test_v61_causal_cycle_detection_blocks_invalid_trace_growth():
    match = start_match(seed="v61-causal-cycle")
    match["events"].append({"id": 999, "event_id": 999, "parent_event_id": 999, "root_event_id": 999})

    with pytest.raises(RebirthError) as error:
        append_event(match, "STATUS_APPLIED", parent_event_id=999)

    assert error.value.code == "causal_cycle_detected"


def test_v61_mcts_uses_generic_vectors_independent_from_card_names():
    a = {"name": "Alpha", "attack": 4, "guard": 4, "tier": 1, "heuristic_vector": {"scaling_potential": 9, "survivability": 5, "trigger_threat": 8, "board_tempo": 7, "value_persistence": 8, "future_resource_swing": 3}}
    b = {**a, "name": "Beta"}
    c = {**a, "name": "Low", "heuristic_vector": {"scaling_potential": 1, "survivability": 1, "trigger_threat": 1, "board_tempo": 1, "value_persistence": 1, "future_resource_swing": 1}}

    assert heuristic_vector(a) == heuristic_vector(b)
    assert threat_score(a) == threat_score(b)
    assert threat_score(a) > threat_score(c)
    assert MCTSAgent(budget=999, depth_limit=99, beam_width=99).budget <= 24


def test_v61_serialization_is_byte_stable_across_dict_ordering():
    match = start_match(seed="v61-byte-stable")
    clone = deepcopy(match)
    match["player"]["statuses"] = {"z": {"b": 2, "a": 1}, "a": {"turns": 1}}
    clone["player"]["statuses"] = {"a": {"turns": 1}, "z": {"a": 1, "b": 2}}

    assert serialize_canonical_state(match).encode("utf-8") == serialize_canonical_state(clone).encode("utf-8")
