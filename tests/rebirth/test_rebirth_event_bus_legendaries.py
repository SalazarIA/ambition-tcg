from copy import deepcopy

import pytest

from services.rebirth_bot import MCTSAgent, deterministic_move_order, threat_score
from services.rebirth_cards import create_card_instance
from services.rebirth_contracts import RebirthError
from services.rebirth_domain import MAX_EFFECT_CHAIN_DEPTH, canonical_state_hash, serialize_canonical_state
from services.rebirth_effects import EffectBus, apply_legendary_passives, expire_statuses_for_trigger
from services.rebirth_engine import next_turn, play_card, resolve_turn, start_match
from services.rebirth_replay import build_replay_envelope, replay_match, verify_replay
from services.rebirth_state import compact_battlefield


REQUIRED_EVENT_FIELDS = {
    "event_id",
    "event_type",
    "source_card_id",
    "target_id",
    "owner_id",
    "turn_number",
    "sequence_id",
    "effect_chain_id",
    "replay_frame",
    "canonical_state_hash",
}


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


def field_instance(match, side_name, instance_id):
    return next(card for card in match[side_name]["battlefield"] if card["instance_id"] == instance_id)


def test_game_events_expose_canonical_required_fields_and_hashes():
    match = start_match(seed="event-fields-v66")
    bus = EffectBus(match, effect_chain_id="test-chain")
    bus.dispatch("TARGET_SELECTED", actor="player", source_card_id="card_x", target_id="target_y", payload={"b": 2, "a": 1})
    emitted = bus.flush()

    event = emitted[-1]
    assert REQUIRED_EVENT_FIELDS.issubset(event)
    assert event["event_id"] == event["id"]
    assert event["event_type"] == event["type"] == "TARGET_SELECTED"
    assert event["sequence_id"] == event["replay_frame"]
    assert len(event["canonical_state_hash"]) == 64


def test_serialize_canonical_state_is_stable_for_dict_ordering():
    match = start_match(seed="canonical-serialization-v66")
    clone = deepcopy(match)
    match["player"]["statuses"] = {"burn": {"turns": 1}, "shield": {"potency": 2}}
    clone["player"]["statuses"] = {"shield": {"potency": 2}, "burn": {"turns": 1}}

    assert serialize_canonical_state(match) == serialize_canonical_state(clone)
    assert canonical_state_hash(match) == canonical_state_hash(clone)


def test_event_payload_is_detached_from_later_source_mutation():
    match = start_match(seed="immutable-payload-v66")
    payload = {"nested": {"value": 1}}
    event = EffectBus(match, effect_chain_id="immutable-chain")
    event.dispatch("STATUS_APPLIED", payload=payload)
    emitted = event.flush()
    payload["nested"]["value"] = 99

    assert emitted[-1]["payload"]["nested"]["value"] == 1


def test_duplicate_dispatch_protection_blocks_same_chain_reactivation():
    match = start_match(seed="infernus-duplicate-v66")
    infernus = place(match, "player", battlefield_card("legend_infernus_core", "player", 1, 0))
    match["player"]["energy"] = 3

    context = {"attacker_card": infernus, "attacker_side": "player", "effect_chain_id": "same-combat-chain"}
    first = apply_legendary_passives(match, "UNIT_SURVIVED_COMBAT", context)
    second = apply_legendary_passives(match, "UNIT_SURVIVED_COMBAT", context)

    assert first
    assert second == []
    assert match["player"]["energy"] == 2
    reduced = field_instance(match, "player", infernus["instance_id"])
    assert reduced["permanent_attack_bonus"] == 2


def test_recursion_depth_protection_rejects_unbounded_event_dispatch():
    match = start_match(seed="recursion-depth-v66")
    match["_event_dispatch_depth"] = MAX_EFFECT_CHAIN_DEPTH
    bus = EffectBus(match, effect_chain_id="deep-chain")

    with pytest.raises(RebirthError) as error:
        bus.dispatch("STATUS_APPLIED", payload={"status": "loop"})

    assert error.value.code == "effect_chain_depth_exceeded"


def test_infernus_core_consumes_mana_and_applies_permanent_attack_after_surviving_combat():
    match = start_match(seed="infernus-combat-v66")
    attacker = place(match, "player", battlefield_card("legend_infernus_core", "player", 1, 0))
    defender = place(match, "bot", battlefield_card("card_021", "bot", 1, 0, attack=2, guard=3))
    match["player"]["energy"] = 2

    resolve_turn(match, attacker, defender, persistent_field=True)

    assert match["player"]["energy"] == 1
    reduced = field_instance(match, "player", attacker["instance_id"])
    assert reduced["attack"] == 8
    assert reduced["permanent_attack_bonus"] == 2
    assert [event["type"] for event in match["events"] if event["effect_chain_id"].startswith("combat-")][-4:] == [
        "RESOURCE_CONSUMED",
        "STAT_MODIFIER_APPLIED",
        "EFFECT_RESOLVED",
        "DAMAGE_DEALT",
    ]


def test_aegis_sentinel_grants_non_stacking_temporary_shield_on_turn_end():
    match = start_match(seed="aegis-shield-v66")
    aegis = place(match, "player", battlefield_card("legend_aegis_sentinel", "player", 1, 0))
    base_guard = aegis["current_guard"]

    first = apply_legendary_passives(match, "TURN_ENDED", {"effect_chain_id": "aegis-chain-a"})
    second = apply_legendary_passives(match, "TURN_ENDED", {"effect_chain_id": "aegis-chain-b"})

    assert first
    assert second == []
    reduced = field_instance(match, "player", aegis["instance_id"])
    assert reduced["current_guard"] == base_guard + 2
    assert reduced["max_guard"] == base_guard + 2
    assert reduced["statuses"]["aegis_sentinel_shield"]["expires_on"] == "DAMAGE_RESOLVED"


def test_aegis_sentinel_shield_expires_after_damage_resolved():
    match = start_match(seed="aegis-expire-v66")
    aegis = place(match, "player", battlefield_card("legend_aegis_sentinel", "player", 1, 0))
    apply_legendary_passives(match, "TURN_ENDED", {"effect_chain_id": "aegis-expire-chain"})
    field_instance(match, "player", aegis["instance_id"])["current_guard"] -= 1

    expired = expire_statuses_for_trigger(match, "DAMAGE_RESOLVED", {"effect_chain_id": "damage-chain"})

    reduced = field_instance(match, "player", aegis["instance_id"])
    assert expired
    assert "aegis_sentinel_shield" not in reduced["statuses"]
    assert reduced["max_guard"] == reduced["guard"]
    assert reduced["current_guard"] == reduced["guard"] - 1
    assert any(event["type"] == "SHIELD_BROKEN" for event in match["events"])


def test_shadow_reaper_selects_highest_attack_with_leftmost_tie_break_and_exhausts_one_turn():
    match = start_match(seed="shadow-target-v66")
    source = place(match, "player", battlefield_card("legend_shadow_reaper", "player", 1, 0))
    left = place(match, "bot", battlefield_card("card_001", "bot", 1, 0, attack=9, guard=4))
    right = place(match, "bot", battlefield_card("card_002", "bot", 2, 1, attack=9, guard=4))

    events = apply_legendary_passives(match, "CARD_SUMMONED", {"source_card": source, "owner_side": "player", "effect_chain_id": "shadow-chain"})

    reduced_left = field_instance(match, "bot", left["instance_id"])
    reduced_right = field_instance(match, "bot", right["instance_id"])
    assert events
    assert reduced_left["exhausted"] is True
    assert reduced_left["has_acted"] is True
    assert reduced_right["exhausted"] is False
    assert reduced_left["statuses"]["shadow_reaper_exhausted"]["turns"] == 1
    assert [event["type"] for event in match["events"] if event["effect_chain_id"] == "shadow-chain"] == [
        "TARGET_SELECTED",
        "UNIT_EXHAUSTED",
        "STATUS_APPLIED",
        "EFFECT_RESOLVED",
    ]


def test_shadow_reaper_exhausted_status_expires_on_turn_started():
    match = start_match(seed="shadow-expire-v66")
    source = place(match, "player", battlefield_card("legend_shadow_reaper", "player", 1, 0))
    target = place(match, "bot", battlefield_card("card_001", "bot", 1, 0, attack=9, guard=4))
    apply_legendary_passives(match, "CARD_SUMMONED", {"source_card": source, "owner_side": "player", "effect_chain_id": "shadow-expire-chain"})

    expired = expire_statuses_for_trigger(match, "TURN_STARTED", {"effect_chain_id": "turn-start-chain"})

    reduced = field_instance(match, "bot", target["instance_id"])
    assert expired
    assert reduced["exhausted"] is False
    assert "shadow_reaper_exhausted" not in reduced["statuses"]


def test_replay_round_trip_preserves_hash_and_event_ordering_with_legendary_card_set():
    deck = ["legend_shadow_reaper", "card_001", "card_002", "card_021", "card_041"] + ["card_001"] * 25
    match = start_match(seed="legend-replay-v66", player_card_ids=deck, bot_profile_id="defensive")
    card = next(item for item in match["player"]["hand"] if item["id"] == "legend_shadow_reaper")

    next_turn(match)
    next_turn(match)
    next_turn(match)
    play_card(match, card_instance_id=card["instance_id"], field_slot=0)
    next_turn(match)

    envelope = build_replay_envelope(match)
    replayed = replay_match(envelope)
    verification = verify_replay(envelope)
    sequence_ids = [event["sequence_id"] for event in match["events"]]

    assert canonical_state_hash(replayed) == canonical_state_hash(match)
    assert verification["ok"] is True
    assert verification["event_ordering_ok"] is True
    assert verification["replay_frame_consistency_ok"] is True
    assert verification["snapshot_hash_consistency_ok"] is True
    assert sequence_ids == sorted(sequence_ids)
    assert all(event["replay_frame"] == event["sequence_id"] for event in match["events"])


def test_mcts_threat_evaluation_prioritizes_scaling_legendary_targets_without_branch_explosion():
    attacker = battlefield_card("card_010", "bot", 1, 0, attack=10, guard=6)
    ordinary = battlefield_card("card_001", "player", 1, 0, attack=4, guard=3)
    infernus = battlefield_card("legend_infernus_core", "player", 2, 1)

    ordered = deterministic_move_order([ordinary, infernus])
    choice = MCTSAgent(budget=999, depth_limit=99, beam_width=99).choose_attack([attacker], [ordinary, infernus], player_hp=30)

    assert threat_score(infernus) > threat_score(ordinary)
    assert ordered[0]["id"] == "legend_infernus_core"
    assert choice["target_id"] == "legend_infernus_core"
    assert MCTSAgent(budget=999).budget <= 24
