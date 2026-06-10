from copy import deepcopy

import pytest

from services.rebirth_cards import create_card_instance
from services.rebirth_domain import canonical_state, canonical_state_hash, decompress_snapshot_state
from services.rebirth_engine import RebirthError, declare_attack, next_turn, play_card, start_match
from services.rebirth_replay import build_replay_envelope, replay_match, verify_replay


def test_canonical_hash_ignores_match_identity_and_tracks_semantics():
    match = start_match(seed="canonical-v60")
    clone = deepcopy(match)
    clone["match_id"] = "transport-id-only"

    assert canonical_state_hash(match) == canonical_state_hash(clone)

    clone["player"]["hp"] -= 1

    assert canonical_state_hash(match) != canonical_state_hash(clone)


def test_snapshots_store_compressed_canonical_state():
    match = start_match(seed="snapshot-v64")
    snapshot = match["snapshots"][-1]
    restored = decompress_snapshot_state(snapshot["canonical_state"])

    assert snapshot["state_encoding"] == "gzip+base64+json"
    assert snapshot["canonical_state_hash"] == canonical_state_hash(match)
    assert restored == canonical_state(match)


def test_invalid_play_does_not_append_accepted_command_or_advance_version():
    match = start_match(seed="invalid-command-v61")
    commands_before = len(match["commands"])
    version_before = match["version"]

    with pytest.raises(RebirthError) as error:
        play_card(match, card_instance_id="not-in-hand")

    assert error.value.code == "invalid_card"
    assert len(match["commands"]) == commands_before
    assert match["version"] == version_before


def test_replay_rebuilds_final_canonical_state_from_commands():
    match = start_match(seed="replay-v63", bot_profile_id="defensive")
    player_card = next(
        card for card in match["player"]["hand"]
        if card.get("type") == "MONSTER" and int(card.get("cost", 9)) <= 2
    )

    play_card(match, card_instance_id=player_card["instance_id"])
    next_turn(match)
    declare_attack(
        match,
        attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
        target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
    )

    envelope = build_replay_envelope(match)
    replayed = replay_match(envelope)
    verification = verify_replay(envelope)

    assert canonical_state_hash(replayed) == canonical_state_hash(match)
    assert verification["ok"] is True
    assert verification["command_count"] == 3


def test_effect_bus_emits_reducer_backed_spell_events():
    match = start_match(seed="effects-v62")
    spell = create_card_instance("card_084", "player", 99)
    match["player"]["hand"] = [spell]
    match["player"]["energy"] = 9

    play_card(match, card_instance_id=spell["instance_id"])

    effect_events = [event for event in match["events"] if event["type"] == "DAMAGE_RESOLVED" and event.get("effect_chain_id", "").startswith("spell-")]
    assert effect_events
    assert effect_events[-1]["payload"]["side"] == "bot"
    assert effect_events[-1]["payload"]["amount"] == 3
    assert effect_events[-1]["priority_level"] == 4
    assert effect_events[-1]["resolution_phase"] == "REDUCER_PHASE"
