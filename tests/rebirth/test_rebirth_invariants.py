from copy import deepcopy

import pytest

from services.rebirth_dispatcher import MulliganCommand, SummonCardCommand, dispatch_command
from services.rebirth_engine import start_match
from services.rebirth_invariants import (
    assert_rebirth_invariants,
    capture_card_baseline,
    run_deterministic_command_fuzz,
    validate_rebirth_state,
)


def _playable_monster(match):
    return next(
        card
        for card in match["player"]["hand"]
        if card.get("type") == "MONSTER" and int(card.get("cost", 99) or 99) <= match["player"]["energy"]
    )


def test_clean_state_and_public_dispatch_commands_hold_invariants():
    match = start_match(
        seed="invariants-clean",
        bot_card_ids=["card_084"] * 30,
        runtime_mode="replay",
        apply_reducers_inline=True,
    )
    baseline = capture_card_baseline(match)

    assert_rebirth_invariants(match, baseline=baseline, check_hash=True)
    card = _playable_monster(match)
    dispatch_command(match, SummonCardCommand(card_instance_id=card["instance_id"]))
    assert_rebirth_invariants(match, baseline=baseline, check_hash=True, check_replay=True)


def test_dispatcher_invariant_hook_runs_after_a_valid_command():
    match = start_match(seed="invariant-hook", runtime_mode="replay", apply_reducers_inline=True)
    match["_validate_invariants_after_command"] = True

    dispatch_command(match, MulliganCommand())

    assert match["mulligan_used"] is True


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (lambda match: match["player"].update(hp=-1), "resource.negative_hp"),
        (lambda match: match["player"].update(energy=-1), "resource.negative_energy"),
        (
            lambda match: match["player"]["field"].append(deepcopy(match["player"]["hand"][0])),
            "field.too_many_slots",
        ),
        (
            lambda match: match["player"]["battlefield"].append(deepcopy(match["player"]["hand"][0])),
            "field.out_of_sync",
        ),
        (
            lambda match: match["player"]["discard"].append(deepcopy(match["player"]["hand"][0])),
            "card.duplicate_side",
        ),
        (
            lambda match: match["bot"]["hand"][0].update(
                instance_id=match["player"]["hand"][0]["instance_id"]
            ),
            "card.duplicate_global",
        ),
        (lambda match: match.update(phase="finished", is_finished=False), "winner.finished_mismatch"),
        (lambda match: match["events"][0].update(sequence_id=2, replay_frame=1), "event.replay_frame_order"),
    ],
)
def test_structured_validator_detects_corrupted_state(mutate, expected_code):
    match = start_match(seed=f"detect-{expected_code}", runtime_mode="replay", apply_reducers_inline=True)
    mutate(match)

    report = validate_rebirth_state(match)

    assert report.ok is False
    assert expected_code in report.codes()
    assert all(violation.message and violation.code for violation in report.violations)


def test_baseline_detects_lost_and_unexplained_created_cards():
    match = start_match(seed="conservation", runtime_mode="replay", apply_reducers_inline=True)
    baseline = capture_card_baseline(match)
    match["player"]["deck"].pop()
    created = deepcopy(match["bot"]["deck"][0])
    created["instance_id"] = "player-created-without-lineage"
    created["owner"] = "player"
    match["player"]["hand"].append(created)

    report = validate_rebirth_state(match, baseline=baseline)

    assert {"card.lost", "card.created"} <= report.codes()


def test_action_flags_hash_and_replay_checks_are_optional_and_structured():
    match = start_match(seed="action-hash", runtime_mode="replay", apply_reducers_inline=True)
    baseline = capture_card_baseline(match)
    card = _playable_monster(match)
    dispatch_command(match, SummonCardCommand(card_instance_id=card["instance_id"]))

    corrupted = deepcopy(match)
    corrupted["player"]["field"][0]["has_attacked"] = True
    corrupted["player"]["field"][0]["has_acted"] = False
    corrupted["player"]["field"][0]["exhausted"] = False
    corrupted["_last_canonical_state_hash"] = "0" * 64
    report = validate_rebirth_state(corrupted, baseline=baseline, check_hash=True, check_replay=True)

    assert "action.impossible_attack_state" in report.codes()
    assert "hash.mismatch" in report.codes()
    assert "replay.mismatch" in report.codes()
    assert report.replay and report.replay["ok"] is False


@pytest.mark.parametrize("flag", ["shield_consumed", "just_summoned"])
def test_canonical_card_flags_must_be_boolean(flag):
    match = start_match(seed=f"flag-type-{flag}", runtime_mode="replay", apply_reducers_inline=True)
    card = _playable_monster(match)
    dispatch_command(match, SummonCardCommand(card_instance_id=card["instance_id"]))
    match["player"]["field"][0][flag] = "yes"

    report = validate_rebirth_state(match)

    assert "action.non_boolean_flag" in report.codes()
    assert any(violation.path == f"player.field[0].{flag}" for violation in report.violations)


@pytest.mark.parametrize("seed", ["fuzz-0", "fuzz-1", "fuzz-2"])
def test_deterministic_command_fuzzing_validates_every_step_and_replay(seed):
    result = run_deterministic_command_fuzz(seed, max_commands=12)

    assert result.ok, [violation.code for violation in result.final_report.violations]
    assert result.attempted_commands > 0
    assert result.accepted_commands > 0
    assert result.replay and result.replay["ok"] is True


def test_fuzzing_is_reproducible_for_the_same_seed():
    first = run_deterministic_command_fuzz("repeatable", max_commands=10)
    second = run_deterministic_command_fuzz("repeatable", max_commands=10)

    assert first.command_types == second.command_types
    assert first.final_report.canonical_hash == second.final_report.canonical_hash


@pytest.mark.parametrize("seed", ["sunder-fuzz-0", "sunder-fuzz-1"])
def test_midrange_sunder_vs_fortress_fuzz_holds_invariants(seed):
    """I3: decks midrange-Ruptura contra muralhas-Escudo passam pelo caminho
    público sem violar invariantes nem divergir no replay."""
    player_deck = (["card_073", "card_077", "card_079"] * 6 + ["card_001", "card_021"] * 6)[:30]
    bot_deck = ["card_051", "card_059"] * 15
    result = run_deterministic_command_fuzz(
        seed,
        max_commands=16,
        match_kwargs={"player_card_ids": player_deck, "bot_card_ids": bot_deck},
    )

    assert result.ok, [violation.code for violation in result.final_report.violations]
    assert result.replay and result.replay["ok"] is True
