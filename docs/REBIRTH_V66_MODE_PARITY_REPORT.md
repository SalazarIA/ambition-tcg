# Ambitionz Rebirth v66 - Mode Parity Infrastructure & Runtime Verification

## 1. Parity architecture final

`services/rebirth_parity.py` introduces `DeterministicParityRunner`.
It captures the fast runtime command/event log, rebuilds the match through
the reducer-backed replay runtime, compares canonical bytes, hashes, reducer
traces, board projections, resources, graveyards, statuses, replay frame
counts and effect-chain ordering.

Parity failures raise `ParityViolationError`; there is no warning-only path
in strict mode.

## 2. Runtime mode model

- `singleplayer`: fast operational runtime, `_apply_reducers_inline=False`.
- `replay`: deterministic runtime, `_apply_reducers_inline=True`.
- `audit`, `network_sync`, `pvp_sync`: reducer-backed deterministic modes.

The parity runner explicitly rejects matches that are not fast-runtime inputs.

## 3. Benchmark realista

`tools/rebirth_benchmark.py` runs scripted combat scenarios with traps,
interrupts, passives, legendary chains, replay reconstruction and MCTS load.

Latest local run:

- matches: 2
- commands: 40
- events: 350
- MCTS simulations: 800
- elapsed: ~11.3s
- parity: ok
- replay reconstruction: ok

## 4. Hotspots encontrados

The current structural hotspot is reducer copy-on-write cloning during replay
and parity verification, not fast singleplayer gameplay.

Observed hottest reducer in the benchmark:

- `UNIT_DESTROYED`
- average: ~6.9ms in the profiled run

## 5. Reducers mais caros

Reducer cost is dominated by reducers that copy large match state during
combat cleanup and board mutation:

- `UNIT_DESTROYED`
- `RESOURCE_CONSUMED`
- `STAT_MODIFIER_APPLIED`
- shield cleanup reducers during turn/replay reconstruction

## 6. Snapshot growth analysis

Snapshot policy is formalized in `services/rebirth_events.py`.
Snapshots are persisted only for:

- `match_started`
- `TURN_ENDED`
- `MATCH_FINISHED`
- `MATCH_EXHAUSTED`
- replay checkpoint every 15 commands
- explicit debug/sync capture

Latest benchmark:

- snapshots: 18
- snapshot encoded growth: ~64KB
- largest snapshot: ~3.9KB

## 7. Replay reconstruction metrics

Replay reconstruction is measured through `replay_cost`, with per-command
aggregation for replay frames.

Latest benchmark:

- replay frame commands: 40 live commands across the benchmark
- replay verification: ok
- parity verification: ok

## 8. MCTS throughput metrics

`tools/rebirth_stress_mcts.py` performs 800 tactical search simulations.

Latest local run:

- iterations: 800
- choices: 800
- elapsed: ~197.5ms
- throughput: ~4051 simulations/sec
- average simulation: ~0.24ms

## 9. Riscos futuros restantes

- Reducer copy-on-write remains intentionally expensive in audit/replay.
- New event types must add both pure reducer behavior and fast in-place
  behavior, then be covered by mode parity tests.
- Any future imperative mutation outside command boundaries must opt into
  debug mutation tracking or be covered by parity replay.

## 10. Estrategia futura para PvP sync

PvP/network sync should run command logs through the deterministic runtime
at authoritative boundaries:

- keep client/runtime fast for local responsiveness;
- publish command/event logs, not raw state mutations;
- run `DeterministicParityRunner` in audit/debug gates;
- use command-level hash checkpoints as sync anchors;
- use snapshot checkpoints only for replay recovery or network resync.
