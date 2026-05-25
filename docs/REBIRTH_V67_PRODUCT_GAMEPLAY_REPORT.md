# Ambitionz Rebirth v67 - Product, Gameplay and Runtime Pass

## 1. Gameplay pacing metrics

Command: `python3 tools/rebirth_gameplay_health.py 60`

| Metric | Result |
| --- | ---: |
| Matches | 60 |
| Average turns | 25.55 |
| Lethal frequency | 1.000 |
| Dead turn rate | 0.039 |
| Stalemate frequency | 0.000 |
| Events per turn | 21.86 |
| Trigger events per turn | 3.39 |
| Symmetric destroy chains per match | 8.85 |
| Largest event chain | 15 |

The simulator now follows matches for up to 30 turns rather than classifying
still-live matches as stalemates at turn 12. This exposed slow pacing honestly:
matches terminate, but they remain longer and denser than a competitive target.

## 2. Match quality metrics

The 60-match run reports `player_win_rate=0.95` and `bot_win_rate=0.05`.
Defensive and aggressive profiles lost all sampled matches; opportunist reached
`0.15` bot win rate. Product health flags are:

- `match_duration_high`
- `outcome_dominance_high`
- `chain_readability_risk`

Flagged card patterns include dominant `Bramblehorn Knight`, `Mossback Brute`
and `Coalheart Runner`, plus low-impact defensive/basic bodies. The report is
intentionally diagnostic: balance is not ready for competitive framing yet.

## 3. Performance improvements reais

Profiler command: `python3 tools/rebirth_benchmark.py 3`

| Metric | Baseline | v67 | Change |
| --- | ---: | ---: | ---: |
| Elapsed time | 18,749.4 ms | 12,348.6 ms | -34.1% |
| `clone_cost` total | 8,977.2 ms | 3,407.6 ms | -62.0% |
| `UNIT_DESTROYED` total | 545.7 ms | 151.7 ms | -72.2% |
| Replay reconstruction average | 421.7 ms | 211.6 ms | -49.8% |
| Command cost total | 2,343.1 ms | 1,096.2 ms | -53.2% |
| Peak memory | 5,924,207 B | 5,664,302 B | -4.4% |

The optimized run includes additional bot-attack and feedback events
(`537` events versus baseline `525`), so the measured improvements are not
coming from a reduced gameplay workload.

## 4. Hotspots resolved

- Reducer copy-on-write now clones mutable gameplay entities rather than the
  complete growing transport/replay history.
- `UNIT_DESTROYED`, the requested reducer hotpath, drops by `72.2%` in total
  profiled cost.
- Replay parity builds compact envelopes without copying event/snapshot streams
  when reconstruction only needs commands and canonical validation.
- Replay envelope hashing reuses its computed final canonical hash.

The largest remaining measured cost is canonical serialization/hashing:
`hash_cost=7,526.7 ms` and `serialization_cost=8,079.4 ms` in the profiled run.

## 5. Remaining bottlenecks

- Canonical hash/serialization now dominates audit and replay benchmarking.
- Average match duration is too high for a fast competitive loop.
- Symmetric destruction still occurs `8.85` times per match despite the new
  overkill pressure.
- Current bot profiles do not contest the tactical player simulation evenly.

These are the next practical targets; no new generic engine layer is warranted.

## 6. Replay and network readiness

- Turn-boundary canonical checkpoints are recorded for lightweight sync anchors.
- `compare_checkpoint_hashes()` detects the earliest shared desync checkpoint.
- `build_sync_payload()` exports commands, incremental replay frames,
  checkpoints and final canonical hash without transport infrastructure.
- `replay_stream_frames()` supplies already-resolved incremental frames for a
  future spectator consumer without full replay re-execution.

No websocket, matchmaking, ranked or distributed-server system was introduced.

## 7. UX and gameplay improvements

- The arena now presents a phase timeline, authoritative priority, active
  chain count and interrupt-window state.
- Damage, shield break, destruction and exhaustion feedback consumes canonical
  events; `UNIT_DESTROYED` now correctly drives death feedback.
- Visual event chips batch secondary event noise, and combat motion timings are
  shorter to reduce waiting between decisions.
- Aegis protection can be answered by deterministic armor break, and capped
  `Breakthrough` turns meaningful overkill into hero pressure.
- Ready bot survivors can attack at their next turn before reinforcement,
  increasing board-position consequence without removing the response window.
- The scaled desktop board no longer scrolls underneath the fixed navigation
  when action buttons receive focus; mobile retains native scrolling.
- Client assets ship under `v67_PRODUCT_FLOW-6`, invalidating stale PWA copies.

Browser QA exercised summon and end-turn into turn `02` on desktop and checked
the same populated state at a `390 x 844` mobile viewport. Both had no console
warnings or errors; desktop preserved `scrollTop=0` after interaction.

## 8. Retention risk analysis

The interface is faster and clearer, but the simulation indicates weak
retention fundamentals for repeated competitive play:

- `95%` player wins will quickly make PvE feel solved.
- `25.55` average turns delays resolution and rematch appetite.
- Chains reaching `15` events still risk making decisive moments hard to parse.

The highest-value follow-up is a short balance season focused on bot decision
quality, dominant cards and trade frequency, measured by this health report.

## 9. Proximos gargalos reais

1. Tune match pacing toward a shorter target band while maintaining meaningful
   response windows.
2. Reduce player dominance with card/profile-specific balance changes supported
   by mass simulation, not global rule complexity.
3. Lower canonical hash/serialization frequency or payload size at validated
   checkpoint boundaries.
4. Use the debug replay HTML timeline to inspect the longest event chains and
   eliminate noisy trigger combinations.

## 10. O que ainda impede um produto comercial competitivo

The game now reads and responds more like a product, and its deterministic
foundation is prepared for lightweight sync. It is not commercially
competitive yet because its match loop is demonstrably unbalanced and too
long, and PvP transport/recovery still does not exist. Those are product
milestones now supported by evidence, rather than hidden behind engine work.

## Verification

- `python3 -m pytest tests/rebirth -q`
- `python3 -m pytest tests/rebirth/test_rebirth_replay_contract.py tests/rebirth/test_v64_canonical_equivalence.py tests/rebirth/test_v66_mode_parity.py tests/rebirth/test_v67_product_gameplay.py -q`
- `python3 tools/rebirth_gameplay_health.py 60`
- `python3 tools/rebirth_benchmark.py 3`
- `python3 tools/rebirth_stress_mcts.py 800`
- `node --check static/js/rebirth.js`
- `node --check static/js/service-worker.js`
- `git diff --check`

Final observed statuses are recorded in the delivery summary for this phase.
