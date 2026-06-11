from copy import deepcopy
from pathlib import Path

from services.rebirth_balance import simulate_balance
from services.rebirth_cards import create_card_instance
from services.rebirth_dispatcher import EndTurnCommand, dispatch_command
from services.rebirth_effects import apply_legendary_passives, resolve_effect_sequence
from services.rebirth_engine import next_turn, resolve_turn, start_match
from services.rebirth_parity import compare_checkpoint_hashes
from services.rebirth_profiler import debug_profile
from services.rebirth_reducers import reduce_event, reduce_unit_destroyed
from services.rebirth_replay import build_replay_envelope, build_sync_payload, replay_match
from services.rebirth_serializers import public_state
from services.rebirth_state import compact_battlefield
from tools.rebirth_replay_visualizer import render_html


ROOT = Path(__file__).resolve().parents[2]


def _place(match, side_name, card_id, slot=0):
    card = create_card_instance(card_id, side_name, slot + 1)
    card["owner_side"] = side_name
    card["field_slot"] = slot
    card["slot"] = slot + 1
    card["current_guard"] = card["guard"]
    card["max_guard"] = card["guard"]
    card["exhausted"] = False
    card["has_attacked"] = False
    card["has_acted"] = False
    card["statuses"] = {}
    match[side_name]["field"][slot] = card
    compact_battlefield(match[side_name])
    return card


def test_v67_destroy_shield_breaks_leftmost_aegis_unit_armor():
    match = start_match(seed="v67-armor-break")
    aegis = _place(match, "bot", "legend_aegis_sentinel")
    apply_legendary_passives(match, "TURN_ENDED", {"effect_chain_id": "aegis-protect"})
    protected = match["bot"]["battlefield"][0]
    assert protected["current_guard"] == aegis["guard"] + 2

    messages = resolve_effect_sequence(
        match,
        "player",
        [{"type": "destroy_shield", "target": "opponent"}],
        effect_chain_id="armor-break",
    )

    broken = match["bot"]["battlefield"][0]
    assert messages == ["Aegis Sentinel perde sua armadura temporária."]
    assert broken["current_guard"] == broken["guard"]
    assert "aegis_sentinel_shield" not in broken["statuses"]
    assert any(event["type"] == "SHIELD_BROKEN" and event["payload"]["armor_break"] for event in match["events"])


def test_v67_breakthrough_converts_excess_guard_damage_into_capped_hero_pressure():
    match = start_match(seed="v67-breakthrough")
    attacker = _place(match, "player", "card_002")
    defender = _place(match, "bot", "card_041")
    attacker["attack"] = attacker["power"] = 10
    defender["current_guard"] = 1

    result = resolve_turn(match, attacker, defender, persistent_field=True)

    assert result["hero_damage"] == {"player": 0, "bot": 2}
    assert match["bot"]["hp"] == 28
    assert any("Breakthrough" in event for event in result["ability_events"])
    damage_event = next(event for event in match["events"] if event["type"] == "DAMAGE_RESOLVED")
    assert damage_event["payload"]["hero_damage"]["bot"] == 2


def test_v67_bot_turn_attacks_with_existing_ready_unit_before_reinforcing():
    match = start_match(seed="v67-bot-pressure", bot_profile_id="aggressive")
    _place(match, "player", "card_041")
    attacker = _place(match, "bot", "card_002")
    attacker["attack"] = attacker["power"] = 10
    match["player"]["field"][0]["current_guard"] = 1
    # Pós-clemência (2026-06-11): nos turnos 1-2 o bot poupa a única unidade
    # do jogador; o contrato deste teste é "ataca antes de reforçar", então
    # o cenário roda fora dessa janela.
    match["turn"] = 4

    next_turn(match)

    bot_attacks = [event for event in match["events"] if event["type"] == "ATTACK_DECLARED" and event["actor"] == "bot"]
    assert bot_attacks
    assert match["player"]["hp"] == 28
    assert any(event["type"] == "DAMAGE_RESOLVED" and event["actor"] == "bot" for event in match["events"])


def test_v67_reducer_clone_shares_transport_history_but_not_gameplay_entities():
    state = start_match(seed="v67-structural-share", runtime_mode="replay", apply_reducers_inline=True)
    state["player"]["hp"] = 20
    event = {"type": "HEALTH_RECOVERED", "actor": "player", "target_id": "player", "payload": {"side": "player", "amount": 2}}

    with debug_profile(enabled=True) as profiler:
        reduced = reduce_event(state, event)

    assert reduced["player"]["hp"] == 22
    assert state["player"]["hp"] == 20
    assert reduced["player"] is not state["player"]
    assert reduced["events"] is state["events"]
    assert "gameplay_entities" in profiler.summary()["metrics"]["clone_cost"]["details"]


def test_v71_destroy_reducer_copies_only_the_mutated_side():
    state = start_match(seed="v71-destroy-hotpath", runtime_mode="replay", apply_reducers_inline=True)
    defeated = _place(state, "player", "card_001")
    _place(state, "bot", "card_041")

    reduced = reduce_unit_destroyed(
        state,
        {"type": "UNIT_DESTROYED", "target_id": defeated["instance_id"], "payload": {"side": "player"}},
    )

    assert reduced["player"] is not state["player"]
    assert reduced["bot"] is state["bot"]
    assert state["player"]["battlefield"][0]["instance_id"] == defeated["instance_id"]
    assert reduced["player"]["battlefield"] == []


def test_v67_turn_checkpoints_sync_payload_and_early_desync_detection():
    match = start_match(seed="v67-sync")
    dispatch_command(match, EndTurnCommand(turn=match["turn"]))
    payload = build_sync_payload(match)

    assert [item["reason"] for item in match["checkpoints"]][:2] == ["match_started", "TURN_ENDED"]
    assert payload["commands"]
    assert payload["replay_frames"]
    assert payload["checkpoints"]
    assert "snapshots" not in payload

    remote = deepcopy(match)
    remote["checkpoints"][-1]["canonical_state_hash"] = "0" * 64
    desync = compare_checkpoint_hashes(match, remote)
    assert desync["desync_detected"] is True
    assert desync["turn"] == 1


def test_v67_compact_replay_and_public_resolution_signals_remain_deterministic(tmp_path):
    match = start_match(seed="v67-stream-ui")
    dispatch_command(match, EndTurnCommand(turn=match["turn"]))
    compact = build_replay_envelope(match, include_stream=False)
    replayed = replay_match(compact)
    state = public_state(match)

    assert "events" not in compact
    assert replayed["turn"] == match["turn"]
    assert state["resolution_context"]["current_phase"] == "MAIN_PHASE"
    assert state["resolution_context"]["priority_label"] == "Jogador"
    assert state["checkpoint"]["canonical_state_hash"]

    target = tmp_path / "timeline.html"
    render_html(build_replay_envelope(match), target)
    content = target.read_text(encoding="utf-8")
    assert "Phase Timeline" in content
    assert "Event Chain / Interrupts" in content
    assert "Reducer Diff Viewer" in content


def test_v67_gameplay_health_exposes_pacing_and_retention_signals():
    summary = simulate_balance(matches=6)["summary"]

    for metric in (
        "average_turns",
        "lethal_frequency",
        "dead_turn_rate",
        "stalemate_frequency",
        "events_per_turn",
        "trigger_events_per_turn",
        "symmetric_destroy_chains_per_match",
        "max_chain_events",
    ):
        assert metric in summary


def test_v71_gameplay_health_avoids_one_sided_dominance_and_stalls():
    summary = simulate_balance(matches=30)["summary"]

    assert 0.4 <= summary["player_win_rate"] <= 0.7
    assert summary["bot_win_rate"] >= 0.2
    assert summary["unfinished_rate"] <= 0.1
    assert summary["average_turns"] <= 25
    # Teto recalibrado: keywords reais (LIFESTEAL/PIERCE/SHIELD/EXECUTE) e
    # traps contextuais alongaram a cadeia legítima de um combate.
    assert summary["max_chain_events"] <= 26


def test_v73_aggressive_profile_is_winnable_after_tuning():
    # Antes do tuning v73, agressivo dava ao jogador ~15% de win-rate; o
    # counter_window dele foi puxado pra 0.28 pra abrir janela de leitura.
    # Este teste garante que a "vitória clara" não regrida silenciosamente —
    # se cair abaixo de 0.25 de novo, o problema voltou.
    payload = simulate_balance(matches=60)
    rates = {profile["profile_id"]: profile["player_win_rate"] for profile in payload["profile_results"]}

    assert rates.get("aggressive", 0) >= 0.25, (
        f"aggressive ficou inviável de novo (player_win={rates.get('aggressive')})"
    )
    spread = max(rates.values()) - min(rates.values())
    assert spread <= 0.65, f"spread de dificuldade entre perfis muito alto: {spread:.3f}"


def test_v74_profile_spread_and_pacing_hit_release_health_targets():
    payload = simulate_balance(matches=60)
    summary = payload["summary"]
    rates = {profile["profile_id"]: profile["player_win_rate"] for profile in payload["profile_results"]}

    assert 0.4 <= summary["player_win_rate"] <= 0.6
    assert summary["average_turns"] <= 24
    assert summary["max_chain_events"] <= 26
    assert max(rates.values()) - min(rates.values()) <= 0.35


def test_v67_turn_flow_and_impact_feedback_ui_contract_is_present():
    template = (ROOT / "templates" / "rebirth.html").read_text(encoding="utf-8")
    script = (ROOT / "static" / "js" / "rebirth.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "static" / "css" / "rebirth.css").read_text(encoding="utf-8")

    assert 'id="phase-timeline"' in template
    assert 'id="priority-label"' in template
    assert 'id="chain-label"' in template
    assert 'id="interrupt-label"' in template
    assert "resolution_context" in script
    assert '"UNIT_DESTROYED"' in script
    assert "feedbackHighlight()" in script
    assert "novelEvents" in script
    assert ".rb-phase-timeline" in stylesheet
    assert ".rb-resolution-strip" in stylesheet
    assert ".rb-mobile-native .rb-result-panel p" in stylesheet
    assert "-webkit-line-clamp: unset;" in stylesheet
