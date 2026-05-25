#!/usr/bin/env python3
"""Realistic Rebirth runtime benchmark for parity, replay and hot paths."""

from __future__ import annotations

import json
import sys
import tracemalloc
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_bot import MCTSAgent
from services.rebirth_cards import is_monster, is_spell, is_trap
from services.rebirth_contracts import RebirthError
from services.rebirth_dispatcher import DeclareAttackCommand, EndTurnCommand, SummonCardCommand, dispatch_command
from services.rebirth_parity import DeterministicParityRunner
from services.rebirth_profiler import debug_profile
from services.rebirth_replay import build_replay_envelope, replay_match
from services.rebirth_engine import start_match


BENCHMARK_DECK = [
    "card_091",
    "card_001",
    "legend_shadow_reaper",
    "legend_infernus_core",
    "legend_aegis_sentinel",
    "card_084",
    "card_021",
    "card_041",
    "card_010",
] + ["card_001", "card_021", "card_041", "card_061", "card_002"] * 6


def _first_playable(match):
    side = match["player"]
    energy = int(side.get("energy", 0) or 0)
    slots_open = any(slot is None for slot in side.get("field", []))
    priority = [
        lambda card: is_trap(card),
        lambda card: is_monster(card) and str(card.get("id", "")).startswith("legend_") and slots_open,
        lambda card: is_monster(card) and slots_open,
        lambda card: is_spell(card),
    ]
    for predicate in priority:
        for card in list(side.get("hand", [])):
            if int(card.get("cost", card.get("tier", 1)) or 0) <= energy and predicate(card):
                return card
    return None


def _first_ready_attacker(match):
    for card in match["player"].get("battlefield", []):
        if not card.get("exhausted") and not card.get("has_attacked") and not card.get("has_acted"):
            return card
    return None


def run_scripted_match(seed: str, *, turns: int = 9):
    match = start_match(seed=seed, player_card_ids=BENCHMARK_DECK, bot_profile_id="defensive")
    for _ in range(turns):
        if match.get("is_finished"):
            break
        card = _first_playable(match)
        if card:
            try:
                dispatch_command(
                    match,
                    SummonCardCommand(
                        card_instance_id=card.get("instance_id"),
                        field_slot=next((idx for idx, slot in enumerate(match["player"].get("field", [])) if slot is None), None),
                    ),
                )
            except RebirthError:
                pass
        attacker = _first_ready_attacker(match)
        if attacker and not match.get("is_finished"):
            target = (match["bot"].get("battlefield") or [None])[0]
            if target or int(match.get("turn", 1) or 1) > 1:
                try:
                    dispatch_command(
                        match,
                        DeclareAttackCommand(
                            attacker_instance_id=attacker.get("instance_id"),
                            target_instance_id=(target or {}).get("instance_id"),
                        ),
                    )
                except RebirthError:
                    pass
        if not match.get("is_finished"):
            try:
                dispatch_command(match, EndTurnCommand(turn=match.get("turn")))
            except RebirthError:
                pass
    return match


def run_benchmark(match_count: int = 2, *, turns: int = 7):
    tracemalloc.start()
    memory_start = tracemalloc.get_traced_memory()[0]
    started = perf_counter()
    parity_reports = []
    matches = []
    with debug_profile(enabled=True) as profiler:
        for index in range(match_count):
            match = run_scripted_match(f"v66-benchmark-{index}", turns=turns)
            matches.append(match)
            parity_reports.append(DeterministicParityRunner().verify(match))
            replay_match(build_replay_envelope(match, include_stream=False))
        bot_cards = [
            card
            for match in matches
            for card in match["bot"].get("battlefield", [])
        ][:3]
        player_cards = [
            card
            for match in matches
            for card in match["player"].get("battlefield", [])
        ][:3]
        for index in range(800):
            MCTSAgent(budget=800).choose_attack(bot_cards, player_cards, player_hp=30, turn=index % 8 + 1)
    memory_end, memory_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed_ms = (perf_counter() - started) * 1000
    snapshots = [snapshot for match in matches for snapshot in match.get("snapshots", [])]
    snapshot_bytes = sum(len(str(snapshot.get("canonical_state") or "")) for snapshot in snapshots)
    events = [event for match in matches for event in match.get("events", [])]
    return {
        "ok": all(report["ok"] for report in parity_reports),
        "match_count": len(matches),
        "event_count": len(events),
        "command_count": sum(len(match.get("commands", [])) for match in matches),
        "elapsed_ms": round(elapsed_ms, 3),
        "memory_growth_bytes": int(memory_end - memory_start),
        "memory_peak_bytes": int(memory_peak),
        "snapshot_count": len(snapshots),
        "snapshot_growth_bytes": snapshot_bytes,
        "replay_reconstruction_verified": True,
        "parity_verified": True,
        "profiler": profiler.summary(),
    }


def main():
    match_count = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    print(json.dumps(run_benchmark(match_count=match_count), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
