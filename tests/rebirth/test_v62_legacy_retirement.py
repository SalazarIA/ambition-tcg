from copy import deepcopy
from pathlib import Path

import pytest

from services.rebirth_cards import create_card_instance
from services.rebirth_contracts import RebirthError
from services.rebirth_dispatcher import PHASED_RESOLUTION_STAGES, PRIORITY_MODEL
from services.rebirth_domain import MAX_EFFECT_CHAIN_DEPTH, MAX_INTERRUPT_DEPTH, canonical_state_hash, serialize_canonical_state
from services.rebirth_effects import (
    EffectBus,
    PRIORITY_ACTIVE_SPELL,
    PRIORITY_DELAYED_EXPIRATION,
    PRIORITY_INTERRUPT,
    PRIORITY_REPLACEMENT,
    cleanup_defeated_units,
    resolve_status_ticks,
)
from services.rebirth_engine import play_card, start_match
from services.rebirth_reducers import reduce_events
from services.rebirth_replay import build_replay_envelope, replay_match, verify_replay
from services.rebirth_state import compact_battlefield


ROOT = Path(__file__).resolve().parents[2]


def place(match, side_name, card_id, slot, *, guard=None):
    card = create_card_instance(card_id, side_name, slot + 1)
    card["owner_side"] = side_name
    card["field_slot"] = slot
    card["slot"] = slot + 1
    card["current_guard"] = int(guard if guard is not None else card.get("guard", 0) or 0)
    card["max_guard"] = int(card.get("guard", 0) or 0)
    match[side_name]["field"][slot] = card
    compact_battlefield(match[side_name])
    return card


def test_v62_legacy_effect_stack_symbols_are_retired():
    engine_source = (ROOT / "services/rebirth_engine.py").read_text(encoding="utf-8")

    assert "class EffectStack" not in engine_source
    assert "effect_stack_for" not in engine_source
    assert "resolve_stack" not in engine_source
    assert "match.setdefault(\"effect_stack\"" not in engine_source


def test_v62_phased_resolution_contract_is_explicit():
    assert PHASED_RESOLUTION_STAGES == (
        "PRE_RESOLUTION",
        "TRIGGER_COLLECTION",
        "PRIORITY_SORT",
        "REDUCER_PHASE",
        "POST_RESOLUTION",
        "CLEANUP_PHASE",
    )
    assert PRIORITY_MODEL[0] == ("Replacement Effects", 1)
    assert PRIORITY_MODEL[-1] == ("Delayed / Expiration Effects", 6)


def test_v62_effect_bus_orders_replacement_before_interrupt_and_spell():
    match = start_match(seed="v62-priority")
    bus = EffectBus(match, effect_chain_id="v62-order")
    bus.dispatch("ACTIVE_SPELL_EFFECT", payload={"n": 3}, order=10, priority_level=PRIORITY_ACTIVE_SPELL, apply_reducer=False)
    bus.dispatch("TRAP_INTERRUPT", payload={"n": 2}, order=10, priority_level=PRIORITY_INTERRUPT, apply_reducer=False)
    bus.dispatch("REPLACEMENT_EFFECT", payload={"n": 1}, order=10, priority_level=PRIORITY_REPLACEMENT, apply_reducer=False)

    emitted = bus.flush()

    assert [event["event_type"] for event in emitted] == ["REPLACEMENT_EFFECT", "TRAP_INTERRUPT", "ACTIVE_SPELL_EFFECT"]
    assert [event["priority_level"] for event in emitted] == [1, 2, 4]


def test_v62_effect_bus_uses_deterministic_tiebreakers():
    match = start_match(seed="v62-tiebreak")
    bus = EffectBus(match, effect_chain_id="v62-tiebreak")
    bus.dispatch("THIRD", payload={"n": 3}, order=1, priority_level=PRIORITY_ACTIVE_SPELL, slot_index=1, stable_entity_id="b", apply_reducer=False)
    bus.dispatch("FIRST", payload={"n": 1}, order=1, priority_level=PRIORITY_ACTIVE_SPELL, slot_index=0, stable_entity_id="z", apply_reducer=False)
    bus.dispatch("SECOND", payload={"n": 2}, order=1, priority_level=PRIORITY_ACTIVE_SPELL, slot_index=1, stable_entity_id="a", apply_reducer=False)

    emitted = bus.flush()

    assert [event["event_type"] for event in emitted] == ["FIRST", "SECOND", "THIRD"]


def test_v62_duplicate_dispatch_and_invalid_phase_are_rejected():
    match = start_match(seed="v62-dup")
    bus = EffectBus(match, effect_chain_id="v62-dup")

    assert bus.dispatch("NOOP", payload={"stable": True}, apply_reducer=False) is True
    assert bus.dispatch("NOOP", payload={"stable": True}, apply_reducer=False) is False
    with pytest.raises(RebirthError) as error:
        bus.dispatch("NOOP", resolution_phase="SIDE_EFFECT_PHASE", apply_reducer=False)

    assert error.value.code == "invalid_resolution_phase"


def test_v62_recursion_and_interrupt_depth_guards_are_defensive():
    match = start_match(seed="v62-depth")
    match["_event_dispatch_depth"] = MAX_EFFECT_CHAIN_DEPTH

    with pytest.raises(RebirthError) as effect_error:
        EffectBus(match).dispatch("NOOP", apply_reducer=False)

    match["_event_dispatch_depth"] = 0
    match["_interrupt_depth"] = MAX_INTERRUPT_DEPTH
    with pytest.raises(RebirthError) as interrupt_error:
        EffectBus(match).dispatch("TRAP_INTERRUPT", priority_level=PRIORITY_INTERRUPT, apply_reducer=False)

    assert effect_error.value.code == "effect_chain_depth_exceeded"
    assert interrupt_error.value.code == "interrupt_depth_exceeded"


def test_v62_spell_effects_resolve_through_reducers_and_not_a_stack():
    match = start_match(seed="v62-spell")
    spell = create_card_instance("card_084", "player", 99)
    match["player"]["hand"] = [spell]
    match["player"]["energy"] = 9
    before_hp = match["bot"]["hp"]

    play_card(match, card_instance_id=spell["instance_id"])

    spell_events = [event for event in match["events"] if event.get("effect_chain_id", "").startswith("spell-")]
    assert match["bot"]["hp"] == before_hp - 3
    assert match["player"]["discard"][-1]["id"] == "card_084"
    assert any(event["event_type"] == "DAMAGE_RESOLVED" and event["priority_level"] == 4 for event in spell_events)
    assert any(event["event_type"] == "CARD_DISCARDED" for event in spell_events)
    assert "effect_stack" not in match


def test_v62_status_ticks_are_cleanup_phase_events():
    match = start_match(seed="v62-status")
    match["bot"]["statuses"]["burn"] = {"turns": 1, "potency": 2}
    before_hp = match["bot"]["hp"]

    messages = resolve_status_ticks(match, effect_chain_id="v62-status")

    tick = next(event for event in match["events"] if event["event_type"] == "TURN_STATUS_TICKED")
    assert match["bot"]["hp"] == before_hp - 2
    assert "burn" not in match["bot"]["statuses"]
    assert tick["resolution_phase"] == "CLEANUP_PHASE"
    assert tick["priority_level"] == PRIORITY_DELAYED_EXPIRATION
    assert any("dano de queimadura" in message for message in messages)


def test_v62_cleanup_phase_destroys_units_via_reducer():
    match = start_match(seed="v62-cleanup")
    dead = place(match, "bot", "card_001", 0, guard=0)

    defeated = cleanup_defeated_units(match, effect_chain_id="v62-cleanup")

    destroyed = next(event for event in match["events"] if event["event_type"] == "UNIT_DESTROYED")
    assert defeated[0]["instance_id"] == dead["instance_id"]
    assert match["bot"]["field"][0] is None
    assert match["bot"]["discard"][-1]["instance_id"] == dead["instance_id"]
    assert destroyed["resolution_phase"] == "CLEANUP_PHASE"


def test_v62_event_sourcing_reconstructs_reducer_state():
    match = start_match(seed="v62-reconstruct")
    card = place(match, "player", "card_001", 0)
    base = deepcopy(match)
    bus = EffectBus(match, effect_chain_id="v62-reconstruct")
    bus.dispatch("STAT_MODIFIER_APPLIED", target_id=card["instance_id"], owner_id="player", payload={"stat": "attack", "amount": 2})
    emitted = bus.flush()

    reconstructed = reduce_events(base, emitted)

    assert reconstructed["player"]["battlefield"][0]["attack"] == match["player"]["battlefield"][0]["attack"]
    assert canonical_state_hash(reconstructed) == canonical_state_hash(match)


def test_v62_replay_round_trip_preserves_hashes_and_frames():
    match = start_match(seed="v62-replay", bot_profile_id="defensive")
    card = match["player"]["hand"][0]

    play_card(match, card_instance_id=card["instance_id"])
    envelope = build_replay_envelope(match)
    replayed = replay_match(envelope)
    verification = verify_replay(envelope)

    assert canonical_state_hash(replayed) == canonical_state_hash(match)
    assert verification["ok"] is True
    assert verification["replay_frame_consistency_ok"] is True


def test_v62_canonical_serialization_is_byte_stable():
    match = start_match(seed="v62-byte-stable")
    encoded_once = serialize_canonical_state(match)
    encoded_twice = serialize_canonical_state(deepcopy(match))

    assert encoded_once == encoded_twice
    assert canonical_state_hash(match) == canonical_state_hash(deepcopy(match))
