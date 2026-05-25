from pathlib import Path
from time import perf_counter

from services.rebirth_bot import MCTSAgent
from services.rebirth_cards import create_card_instance
from services.rebirth_dispatcher import EndTurnCommand, SummonCardCommand, dispatch_command
from services.rebirth_domain import canonical_state_hash
from services.rebirth_effects import EffectBus, purge_effect_runtime_caches
from services import rebirth_effects, rebirth_events
from services.rebirth_engine import start_match
from services.rebirth_events import append_command, append_snapshot
from services.rebirth_replay import build_replay_envelope, replay_match


ROOT = Path(__file__).resolve().parents[2]


def _put_hand_card(match, card_id, owner="player", sequence=90):
    card = create_card_instance(card_id, owner, sequence)
    match[owner]["hand"].insert(0, card)
    match[owner]["energy"] = max(9, int(match[owner].get("energy", 0) or 0))
    match[owner]["max_energy"] = max(9, int(match[owner].get("max_energy", 0) or 0))
    return card


def _placed_card(card_id, owner, sequence, slot, *, attack=None, guard=None):
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


def test_v65_singleplayer_matches_start_with_inline_reducers_disabled():
    match = start_match(seed="v65-singleplayer-runtime")

    assert match["_runtime_mode"] == "singleplayer"
    assert match["_apply_reducers_inline"] is False


def test_v65_replay_audit_and_network_modes_keep_inline_reducers_enabled():
    replay = start_match(seed="v65-replay-runtime", runtime_mode="replay")
    audit = start_match(seed="v65-audit-runtime", runtime_mode="audit")
    network = start_match(seed="v65-network-runtime", runtime_mode="network_sync")

    assert replay["_apply_reducers_inline"] is True
    assert audit["_apply_reducers_inline"] is True
    assert network["_apply_reducers_inline"] is True


def test_v65_replay_loader_forces_reducer_backed_runtime():
    source = start_match(seed="v65-replay-loader")
    replayed = replay_match(build_replay_envelope(source))

    assert replayed["_runtime_mode"] == "replay"
    assert replayed["_apply_reducers_inline"] is True


def test_v65_effect_bus_in_place_path_matches_copy_on_write_reducer_state():
    fast = start_match(seed="v65-effect-equivalence", apply_reducers_inline=False)
    reducer = start_match(seed="v65-effect-equivalence", runtime_mode="replay", apply_reducers_inline=True)
    for match in (fast, reducer):
        card = _placed_card("legend_infernus_core", "player", 1, 0)
        match["player"]["field"][0] = card
        match["player"]["battlefield"] = [card]
        match["player"]["energy"] = 3

    for match in (fast, reducer):
        target_id = match["player"]["battlefield"][0]["instance_id"]
        bus = EffectBus(match, effect_chain_id="v65-equivalence")
        bus.dispatch("RESOURCE_CONSUMED", actor="player", owner_id="player", target_id=target_id, payload={"resource": "mana", "amount": 1})
        bus.dispatch(
            "STAT_MODIFIER_APPLIED",
            actor="player",
            owner_id="player",
            target_id=target_id,
            payload={"stat": "attack", "amount": 2, "duration": "permanent"},
            chain_from_previous=True,
        )
        bus.flush()

    assert fast["player"]["energy"] == reducer["player"]["energy"] == 2
    assert canonical_state_hash(fast) == canonical_state_hash(reducer)


def test_v65_singleplayer_effect_bus_never_calls_copy_on_write_reducer(monkeypatch):
    match = start_match(seed="v65-no-inline-reducer", apply_reducers_inline=False)
    match["player"]["hp"] = 20
    calls = {"count": 0}

    def tracked_reduce_event(state, event):
        calls["count"] += 1
        return state

    monkeypatch.setattr(rebirth_effects, "reduce_event", tracked_reduce_event)
    bus = EffectBus(match, effect_chain_id="v65-fast-heal")
    bus.dispatch("HEALTH_RECOVERED", actor="player", target_id="player", owner_id="player", payload={"side": "player", "amount": 3})
    bus.flush()

    assert calls["count"] == 0
    assert match["player"]["hp"] == 23


def test_v65_replay_effect_bus_still_uses_copy_on_write_reducer(monkeypatch):
    match = start_match(seed="v65-inline-reducer", runtime_mode="replay", apply_reducers_inline=True)
    match["player"]["hp"] = 20
    original = rebirth_effects.reduce_event
    calls = {"count": 0}

    def tracked_reduce_event(state, event):
        calls["count"] += 1
        return original(state, event)

    monkeypatch.setattr(rebirth_effects, "reduce_event", tracked_reduce_event)
    bus = EffectBus(match, effect_chain_id="v65-replay-heal")
    bus.dispatch("HEALTH_RECOVERED", actor="player", target_id="player", owner_id="player", payload={"side": "player", "amount": 3})
    bus.flush()

    assert calls["count"] == 1
    assert match["player"]["hp"] == 23


def test_v65_singleplayer_command_resolves_spell_without_inline_reducers():
    match = start_match(seed="v65-spell-fast-path", apply_reducers_inline=False)
    spell = _put_hand_card(match, "card_084")

    dispatch_command(match, SummonCardCommand(card_instance_id=spell["instance_id"]))

    assert match["bot"]["hp"] == 27
    assert match["player"]["discard"][-1]["instance_id"] == spell["instance_id"]
    assert all(event["canonical_state_hash"] for event in match["events"][1:])


def test_v65_intermediate_actions_do_not_emit_gzip_snapshots(monkeypatch):
    match = start_match(seed="v65-no-intermediate-snapshots", apply_reducers_inline=False)
    card = _put_hand_card(match, "card_001")
    snapshot_count = len(match["snapshots"])
    compression_calls = {"count": 0}

    def tracked_compress(state):
        compression_calls["count"] += 1
        return "compressed"

    monkeypatch.setattr(rebirth_events, "compress_canonical_state", tracked_compress)
    dispatch_command(match, SummonCardCommand(card_instance_id=card["instance_id"], field_slot=0))

    assert len(match["snapshots"]) == snapshot_count
    assert compression_calls["count"] == 0


def test_v65_turn_end_is_the_lifecycle_snapshot_boundary():
    match = start_match(seed="v65-turn-snapshot", apply_reducers_inline=False)

    dispatch_command(match, EndTurnCommand(turn=match["turn"]))

    reasons = [snapshot["reason"] for snapshot in match["snapshots"]]
    assert "TURN_ENDED" in reasons
    assert "turn_started" not in reasons


def test_v65_replay_checkpoints_persist_only_every_15_actions():
    match = start_match(seed="v65-snapshot-checkpoint")
    initial_snapshots = len(match["snapshots"])

    for index in range(14):
        append_command(match, "NOOP", payload={"index": index})
    assert append_snapshot(match, "action_checkpoint") is None
    assert len(match["snapshots"]) == initial_snapshots

    append_command(match, "NOOP", payload={"index": 14})
    checkpoint = append_snapshot(match, "action_checkpoint")

    assert checkpoint["reason"] == "action_checkpoint"
    assert len(match["snapshots"]) == initial_snapshots + 1
    assert append_snapshot(match, "action_checkpoint") is None


def test_v65_canonical_hash_finalizes_once_per_command(monkeypatch):
    match = start_match(seed="v65-hash-once", apply_reducers_inline=False)
    spell = _put_hand_card(match, "card_084")
    original = rebirth_effects.canonical_state_hash
    calls = {"count": 0}

    def tracked_hash(state):
        calls["count"] += 1
        return original(state)

    monkeypatch.setattr(rebirth_effects, "canonical_state_hash", tracked_hash)
    dispatch_command(match, SummonCardCommand(card_instance_id=spell["instance_id"]))

    command_hashes = {event["canonical_state_hash"] for event in match["events"][1:]}
    assert calls["count"] == 1
    assert len(command_hashes) == 1
    assert len(next(iter(command_hashes))) == 64


def test_v65_mcts_800_search_loop_avoids_snapshot_compression(monkeypatch):
    bot_cards = [_placed_card("card_010", "bot", 1, 0, attack=8, guard=5), _placed_card("card_041", "bot", 2, 1)]
    player_cards = [_placed_card("legend_infernus_core", "player", 1, 0), _placed_card("card_001", "player", 2, 1)]
    match = start_match(seed="v65-mcts-load")
    compression_calls = {"count": 0}

    def tracked_compress(state):
        compression_calls["count"] += 1
        return "compressed"

    monkeypatch.setattr(rebirth_events, "compress_canonical_state", tracked_compress)
    started = perf_counter()
    for index in range(800):
        MCTSAgent(budget=800).choose_attack(bot_cards, player_cards, player_hp=30, turn=index % 6 + 1)
        append_snapshot(match, "mcts_rollout")
    ms_per_move = (perf_counter() - started) * 1000 / 800

    assert compression_calls["count"] == 0
    assert ms_per_move < 5.0


def test_v65_effect_runtime_cache_purge_keeps_only_recent_chains():
    match = start_match(seed="v65-cache-purge")
    match["_effect_dispatch_keys"] = {f"chain-{index:03d}": ["dispatch"] for index in range(40)}
    match["_effect_activation_keys"] = {f"chain-{index:03d}": ["activation"] for index in range(40)}

    purge_effect_runtime_caches(match, keep_last=8)

    assert len(match["_effect_dispatch_keys"]) == 8
    assert len(match["_effect_activation_keys"]) == 8
    assert min(match["_effect_dispatch_keys"]) == "chain-032"
    assert max(match["_effect_activation_keys"]) == "chain-039"


def test_v65_service_worker_runtime_cache_is_bounded_and_purged():
    service_worker = (ROOT / "static/js/service-worker.js").read_text(encoding="utf-8")

    assert "MAX_RUNTIME_CACHE_ENTRIES = CORE_ASSETS.length" in service_worker
    assert "function trimRuntimeCache(cache)" in service_worker
    assert "return trimRuntimeCache(cache);" in service_worker
    assert "pruneActiveCache()" in service_worker
    assert "key !== CACHE_NAME && REBIRTH_CACHE_RE.test(key)" in service_worker
