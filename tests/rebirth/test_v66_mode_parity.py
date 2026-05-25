from copy import deepcopy

import pytest

from services.rebirth_bot import MCTSAgent
from services.rebirth_dispatcher import DeclareAttackCommand, EndTurnCommand, SummonCardCommand, dispatch_command
from services.rebirth_domain import canonical_state_hash, serialize_canonical_state
from services.rebirth_parity import (
    DeterministicParityRunner,
    ParityViolationError,
    effect_chain_ordering,
    replay_chain_trace,
    runtime_projection,
)
from services.rebirth_profiler import current_profiler, debug_profile
from services.rebirth_replay import build_replay_envelope, replay_match, verify_replay
from services.rebirth_engine import start_match
from services.rebirth_events import append_snapshot


BASE_DECK = [
    "card_091",
    "card_001",
    "legend_shadow_reaper",
    "card_084",
    "card_021",
    "legend_infernus_core",
    "legend_aegis_sentinel",
] + ["card_001", "card_021", "card_041", "card_061", "card_002"] * 6


def _first_attacker(match):
    for card in match["player"].get("battlefield", []):
        if not card.get("exhausted") and not card.get("has_attacked") and not card.get("has_acted"):
            return card
    return None


def _attack_first_target(match):
    attacker = _first_attacker(match)
    if not attacker:
        return
    target = (match["bot"].get("battlefield") or [None])[0]
    if not target and int(match.get("turn", 1) or 1) <= 1:
        return
    dispatch_command(
        match,
        DeclareAttackCommand(
            attacker_instance_id=attacker["instance_id"],
            target_instance_id=(target or {}).get("instance_id"),
        ),
    )


def _scripted_match(seed, *, legend_id="legend_shadow_reaper", attack_legend=False):
    deck = list(BASE_DECK)
    deck[2] = legend_id
    match = start_match(seed=seed, player_card_ids=deck, bot_profile_id="defensive")
    dispatch_command(match, SummonCardCommand(card_id="card_091"))
    dispatch_command(match, EndTurnCommand(turn=match["turn"]))
    dispatch_command(match, SummonCardCommand(card_id="card_001", field_slot=0))
    _attack_first_target(match)
    if not match.get("is_finished"):
        dispatch_command(match, EndTurnCommand(turn=match["turn"]))
    if not match.get("is_finished"):
        dispatch_command(match, SummonCardCommand(card_id="card_084"))
        dispatch_command(match, EndTurnCommand(turn=match["turn"]))
    if not match.get("is_finished"):
        dispatch_command(match, SummonCardCommand(card_id=legend_id, field_slot=1))
        if attack_legend:
            legend = next(card for card in match["player"]["battlefield"] if card["id"] == legend_id)
            target = (match["bot"].get("battlefield") or [None])[0]
            if target:
                dispatch_command(
                    match,
                    DeclareAttackCommand(
                        attacker_instance_id=legend["instance_id"],
                        target_instance_id=target["instance_id"],
                    ),
                )
        if not match.get("is_finished"):
            dispatch_command(match, EndTurnCommand(turn=match["turn"]))
    return match


def test_v66_full_match_parity_for_five_realistic_scenarios():
    scenarios = [
        ("v66-full-shadow-a", "legend_shadow_reaper", False),
        ("v66-full-shadow-b", "legend_shadow_reaper", True),
        ("v66-full-infernus-a", "legend_infernus_core", True),
        ("v66-full-infernus-b", "legend_infernus_core", False),
        ("v66-full-aegis", "legend_aegis_sentinel", False),
    ]

    reports = [
        DeterministicParityRunner().verify(_scripted_match(seed, legend_id=legend_id, attack_legend=attack))
        for seed, legend_id, attack in scenarios
    ]

    assert len(reports) == 5
    assert all(report["ok"] for report in reports)
    assert all(report["event_count"] >= 20 for report in reports)


def test_v66_parity_violation_detection_explodes_with_dump():
    match = _scripted_match("v66-illegal-mutation", legend_id="legend_shadow_reaper")
    match["player"]["hp"] -= 1

    with pytest.raises(ParityViolationError) as error:
        DeterministicParityRunner().verify(match)

    dump = error.value.dump
    assert dump["checks"]["canonical_state_hash"] is False
    assert dump["state_diffs"]
    assert dump["replay_trace"]["fast"]
    assert dump["reducer_trace"]["reducer"]


def test_v66_event_log_mutation_points_to_event_and_reducer_divergence():
    match = _scripted_match("v66-event-divergence", legend_id="legend_infernus_core", attack_legend=True)
    damage_event = next(event for event in match["events"] if event["type"] == "DAMAGE_RESOLVED")
    damage_event["payload"]["bot"] = int(damage_event["payload"].get("bot", 0) or 0) + 9
    damage_event["resolution_phase"] = "CORRUPTED_PHASE"

    with pytest.raises(ParityViolationError) as error:
        DeterministicParityRunner().verify(match)

    dump = error.value.dump
    assert dump["first_event_divergence"]
    assert dump["first_reducer_divergence"]


def test_v66_hash_checkpoints_are_invalidated_and_finalized_per_command():
    match = start_match(seed="v66-hash-checkpoint", player_card_ids=BASE_DECK)
    dispatch_command(match, SummonCardCommand(card_id="card_091"))

    assert match["_canonical_hash_dirty"] is False
    assert len(match["_last_canonical_state_hash"]) == 64
    command_hashes = {event["canonical_state_hash"] for event in match["events"][1:]}
    assert command_hashes == {match["_last_canonical_state_hash"]}

    dispatch_command(match, EndTurnCommand(turn=match["turn"]))

    assert match["_canonical_hash_dirty"] is False
    assert canonical_state_hash(match) == match["_last_canonical_state_hash"]


def test_v66_snapshot_policy_boundaries_and_explicit_debug_capture():
    match = start_match(seed="v66-snapshot-policy", player_card_ids=BASE_DECK)
    initial_count = len(match["snapshots"])
    dispatch_command(match, SummonCardCommand(card_id="card_091"))

    assert len(match["snapshots"]) == initial_count
    debug_snapshot = append_snapshot(match, "debug_capture", force=True)
    assert debug_snapshot["reason"] == "debug_capture"

    dispatch_command(match, EndTurnCommand(turn=match["turn"]))
    assert "TURN_ENDED" in [snapshot["reason"] for snapshot in match["snapshots"]]


def test_v66_replay_round_trip_equals_live_runtime_and_verify_replay():
    match = _scripted_match("v66-replay-round-trip", legend_id="legend_infernus_core", attack_legend=True)
    replayed = replay_match(build_replay_envelope(match))
    verification = verify_replay(build_replay_envelope(match))

    assert serialize_canonical_state(replayed) == serialize_canonical_state(match)
    assert verification["ok"] is True
    assert DeterministicParityRunner().verify(match)["ok"] is True


def test_v66_phase_and_effect_chain_ordering_are_identical_between_modes():
    match = _scripted_match("v66-phase-order", legend_id="legend_shadow_reaper")
    replayed = replay_match(build_replay_envelope(match))

    assert runtime_projection(match)["phase"] == runtime_projection(replayed)["phase"]
    assert runtime_projection(match)["turn_phase"] == runtime_projection(replayed)["turn_phase"]
    assert effect_chain_ordering(match["events"]) == effect_chain_ordering(replayed["events"])
    phases = [item["resolution_phase"] for item in replay_chain_trace(match["events"]) if item["resolution_phase"]]
    assert "REDUCER_PHASE" in phases
    assert "CLEANUP_PHASE" in phases


def test_v66_profiler_opt_in_collects_structural_metrics():
    with debug_profile(enabled=True) as profiler:
        match = _scripted_match("v66-profiler", legend_id="legend_infernus_core", attack_legend=True)
        replay_match(build_replay_envelope(match))
        MCTSAgent(budget=800).choose_attack(match["bot"]["battlefield"], match["player"]["battlefield"], player_hp=30)

    summary = profiler.summary()
    metrics = summary["metrics"]
    for name in ("command_cost", "phase_cost", "reducer_cost", "clone_cost", "replay_cost", "hash_cost", "serialization_cost", "snapshot_cost", "MCTS_simulation_cost"):
        assert name in metrics
        assert "average_ms" in metrics[name]
        assert "p95_ms" in metrics[name]
        assert "p99_ms" in metrics[name]
    assert summary["hottest_reducer"]
    assert summary["deepest_effect_chain"] >= 1
    assert summary["largest_snapshot"]["bytes"] > 0


def test_v66_profiler_is_disabled_by_default():
    assert current_profiler() is None
    match = _scripted_match("v66-no-profiler", legend_id="legend_shadow_reaper")

    assert current_profiler() is None
    assert DeterministicParityRunner().verify(match)["ok"] is True


def test_v66_mutation_origin_tracking_is_debug_only():
    match = start_match(seed="v66-mutation-origin", player_card_ids=BASE_DECK)
    dispatch_command(match, SummonCardCommand(card_id="card_091"))
    assert "_mutation_origins" not in match

    tracked = start_match(seed="v66-mutation-origin-tracked", player_card_ids=BASE_DECK)
    tracked["_debug_mutation_tracking"] = True
    dispatch_command(tracked, SummonCardCommand(card_id="card_091"))

    assert tracked["_mutation_dirty"] is True
    assert any(origin.startswith("command:") for origin in tracked["_mutation_origins"])


def test_v66_mcts_800_load_and_fast_runtime_avoids_clone_pressure():
    fast = _scripted_match("v66-fast-clone-pressure", legend_id="legend_shadow_reaper")
    with debug_profile(enabled=True) as fast_profiler:
        for index in range(800):
            MCTSAgent(budget=800).choose_attack(fast["bot"]["battlefield"], fast["player"]["battlefield"], player_hp=30, turn=index % 6 + 1)
    with debug_profile(enabled=True) as reducer_profiler:
        replay_match(build_replay_envelope(fast))

    fast_clone_count = fast_profiler.summary()["metrics"].get("clone_cost", {}).get("count", 0)
    reducer_clone_count = reducer_profiler.summary()["metrics"]["clone_cost"]["count"]
    assert fast_clone_count == 0
    assert reducer_clone_count > fast_clone_count
    assert fast_profiler.summary()["metrics"]["MCTS_simulation_cost"]["count"] == 800


def test_v66_runner_rejects_wrong_runtime_mode():
    reducer_match = start_match(seed="v66-wrong-mode", runtime_mode="replay", apply_reducers_inline=True)

    with pytest.raises(ParityViolationError) as error:
        DeterministicParityRunner().verify(reducer_match)

    assert error.value.dump["_apply_reducers_inline"] is True


def test_v66_parity_validation_hook_is_opt_in_after_command():
    match = start_match(seed="v66-parity-hook", player_card_ids=BASE_DECK)
    match["_parity_validate_after_command"] = True

    dispatch_command(match, SummonCardCommand(card_id="card_091"))

    assert match["_canonical_hash_dirty"] is False
    assert len(match["_last_canonical_state_hash"]) == 64


def test_v66_serialization_byte_check_after_deepcopy_is_stable():
    match = _scripted_match("v66-byte-stability", legend_id="legend_aegis_sentinel")
    clone = deepcopy(match)

    assert serialize_canonical_state(match).encode("utf-8") == serialize_canonical_state(clone).encode("utf-8")
    assert DeterministicParityRunner().verify(match)["checks"]["byte_equivalent"] is True
