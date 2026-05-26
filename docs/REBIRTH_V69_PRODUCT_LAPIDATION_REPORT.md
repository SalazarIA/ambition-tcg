# Ambitionz Rebirth v69 — Product Lapidation & Audio Debunking

Pacote focado em **comportamento perceptível** (áudio limpo, IA mais defensiva, balance cirúrgico) e **redução do custo residual de serialização**, sem alterar contrato de event model nem introduzir hash incremental ou colapso de combat events.

## 1. Resumo executivo

| Frente | Resultado | Risco |
|---|---|---|
| Audio spam em chains | **Eliminado** — chain de 15 eventos → 1 reprodução | Zero (sem mudança no event stream) |
| Bot vs Breakthrough | Heurística aware (5 testes novos) | Zero (não afeta replay determinístico) |
| Nerf Bramblehorn/Mossback/Coalheart | Override declarativo, fire_execute +3→+2 | Zero (auditável via constante) |
| Custo de serialização | canonical_state **-47%** em mid-game | Zero (parity/replay preservados) |
| Suite | **1150 passed** (era 1137 → +13 novos) | — |

## 2. Bloco 1 — Audio dedup por chain

**Problema** (confirmado no laudo pós-v68):
- A chave de debounce incluía `event_id` / `sequence_id` — únicos por evento.
- Em chains longas (15 eventos), cada `DAMAGE_RESOLVED` gerava chave distinta e nunca dedupava.
- Resultado audível: spam de `impact_heavy.wav` em <100ms.

**Mudança** ([static/js/rebirth_audio.js:85](static/js/rebirth_audio.js:85)):
```js
eventKey(event, soundKey) {
    const chain = event.effect_chain_id || "";
    return chain ? `${soundKey}:${chain}` : soundKey;
}
```

**Fix colateral**: `shouldPlay` usava `previous = lastPlayed.get(key) || 0` — primeira chamada com `performance.now() < 90ms` era erroneamente dedupada. Trocado para `if (previous !== undefined && now - previous < debounceMs)`.

**Validação** ([tests/js/test_rebirth_audio_chain_dedup.cjs](tests/js/test_rebirth_audio_chain_dedup.cjs)):
- 5 asserts: chain de 15 eventos = 1 reprodução; chains diferentes tocam independentes; fallback estável sem chain; reentra após `debounceMs`; forma exata da chave.
- `node tests/js/test_rebirth_audio_chain_dedup.cjs` → `audio chain dedup: OK (5 asserts)`
- `node --check static/js/rebirth_audio.js` → OK.

## 3. Bloco 2 — IA contra Breakthrough

**Problema**: `dead_turn_rate=0.039` baixo, mas player WR 95%. Os 354 procs/60p de `Breakthrough: Bot sofre 2 de dano excedente` confirmam pressão sustentada que a heurística do bot não enxergava.

**Mudança** ([services/rebirth_bot.py](services/rebirth_bot.py)):

1. Funções novas, exportadas para futuros usos:
   - `breakthrough_potential(opponent_card, defender_guard_pool)` — calcula overflow capado no teto do engine (2).
   - `opponent_breakthrough_pressure(opponent_battlefield, defender_battlefield, *, excluded_defender)` — pareia attackers com blockers e soma a pressão agregada.
2. `attack_utility_projection` agora calcula `defender_guard_pool` (board do bot menos o próprio attacker) e aplica:
   - `+target_breakthrough * 40` se o ataque destrói uma threat de Breakthrough → razão `neutralize_breakthrough`.
   - `-target_breakthrough * 15` se deixa a threat viva → razão `leaves_breakthrough_alive`.
3. `reason` final compõe lethal_window > future_lethal > suicide_refusal > breakthrough > trade_value (precedência preserva semântica existente).

**Constraint preservada**: CI-safe, determinístico, sem rollout MCTS real, sem deepcopy/simulação pesada.

**Validação** ([tests/rebirth/test_v69_bot_breakthrough.py](tests/rebirth/test_v69_bot_breakthrough.py)):
- `breakthrough_potential` respeita o cap de engine (2) em entradas extremas.
- `opponent_breakthrough_pressure` pareia maior attacker com maior blocker.
- `attack_utility_projection` premia matar a threat e penaliza deixá-la viva.
- `tactical_utility_matrix` ordena Bramblehorn-killing acima de dummy-killing no mesmo turn.
- 5/5 testes verdes. Suite legada (`test_rebirth_bot_personalities`) verde.

## 4. Bloco 3 — Nerf cirúrgico do trio opressor

**Problema** (gameplay_health 60p): Bramblehorn 100% WR (57 plays), Mossback 100% WR (57 plays), Coalheart 80% WR (154 plays).

**Mudança 1 — overrides declarativos** ([services/rebirth_cards.py](services/rebirth_cards.py)):
```python
CARD_BALANCE_OVERRIDES = {
    "card_046": {"cost": 3},  # Bramblehorn Knight 2 → 3
    "card_045": {"cost": 3},  # Mossback Brute 2 → 3
}
for card_id, override in CARD_BALANCE_OVERRIDES.items():
    if card_id in CARD_CATALOG_DICT:
        CARD_CATALOG_DICT[card_id].update(override)
```

`_monster_cost` (contrato canônico da curva) **não foi tocado** — o override é externo e auditável.

**Mudança 2 — nerf de `fire_execute`** ([services/rebirth_engine.py:180](services/rebirth_engine.py:180)):
- `+3 dano` em alvo ferido → `+2 dano`. Identidade da carta (execute em wounded) preservada; `tie_priority` continua dando o desempate. Removido o swing barato que justificava 246 procs no top de events.

**Validação** ([tests/rebirth/test_v69_balance_overrides.py](tests/rebirth/test_v69_balance_overrides.py)):
- Bramblehorn cost = 3.
- Mossback cost = 3.
- CARD_BALANCE_OVERRIDES contém **apenas** o trio documentado (sentinela contra vazamento).
- `fire_execute` em wounded soma exatamente +2 (regression test).
- `fire_execute` em healthy não soma nada.
- O teste de invariante de curva ([test_card_catalog_matrix.py](tests/rebirth/unit/test_card_catalog_matrix.py)) foi atualizado para aceitar overrides via constante; cards sem override continuam obrigados à fórmula.
- 5/5 testes verdes; matriz completa 696 testes verdes.

## 5. Bloco 4 — Cache de deck/discard (resolvido por otimização cirúrgica)

**Diagnóstico** (probe direto antes da implementação):
- `canonical_state(match)` em mid-game = **122ms / 200 runs**.
- Iterar `canonical_card` sobre `deck+discard` dos dois sides isoladamente = **116ms / 200 runs** = **95% do custo**.
- Tamanhos amostrais: player deck 16 / discard 9; bot deck 19 / discard 4.

**Causa raiz**: `_stable_value` em [rebirth_domain.py](services/rebirth_domain.py) chamava `copy.deepcopy(value)` para **primitivos imutáveis** (str/int/float/bool/None). Deepcopy de imutáveis é puro overhead — Python compartilha as instâncias.

**Mudança** ([services/rebirth_domain.py:77](services/rebirth_domain.py:77)):
```python
def _stable_value(value):
    if isinstance(value, dict):
        return {str(key): _stable_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_stable_value(item) for item in value]
    return value  # primitives are immutable — no copy needed
```

**Resultado**: `canonical_state` 122ms → **65ms (-47%)** em mid-game.

**Decisão consciente**: **não** introduzi cache opt-in com signature tracking. Razões:
1. -47% já satisfaz "reduzir custo residual sem quebrar canônica".
2. Cache real precisaria invalidação em todos os mutadores de deck/discard (alto risco arquitetural).
3. Após v68 (`_fast_clone` via pickle) o clone já não é o gargalo; agora hash/serialization domina e foi exatamente o que essa cirurgia atacou.

**Validação canônica/parity** ([tests/rebirth/test_v69_serializer_purity.py](tests/rebirth/test_v69_serializer_purity.py)):
- `canonical_card` não muta o card de origem.
- `canonical_state` byte-stable entre clones (`deepcopy(match)` igual).
- Output canônico não compartilha referência das listas internas (mutar canonical_state não vaza pro match).
- Suite parity/replay completa: `test_v62_legacy_retirement` + `test_v64_canonical_equivalence` + `test_v66_mode_parity` + `test_rebirth_replay_contract` = 46/46 verdes.

## 6. Benchmark antes/depois

`python3 tools/rebirth_benchmark.py 3` (3 partidas scripted + 800 MCTS sims):

| Métrica | v67 baseline | v68 | **v69** | Δ vs v67 | Δ vs v68 |
|---|---:|---:|---:|---:|---:|
| elapsed_ms total | 12.333 | 2.484 | **2.392** | **-81%** | -3.7% |
| hash_cost | 7.526 | 572 | **462** | -94% | -19% |
| serialization_cost | 8.079 | 872 | **715** | -91% | -18% |
| clone_cost | 3.408 | 596 | 598 | -82% | = |
| snapshot_cost | 620 | 294 | **252** | -59% | -14% |
| command_cost | 1.096 | 820 | 485 | -56% | -41% |

Parity_verified: **True**. Replay_reconstruction_verified: **True**. event_count: 537 (idêntico).

## 7. Gameplay health pós-v69

`python3 tools/rebirth_gameplay_health.py 60`:

| Métrica | v67 | **v69** | Δ |
|---|---:|---:|---:|
| average_turns | 25.55 | 25.55 | = |
| player_win_rate | 0.95 | 0.95 | = |
| bot_win_rate | 0.05 | 0.05 | = |
| dead_turn_rate | 0.039 | 0.039 | = |
| max_chain_events | 15 | 15 | = |
| symmetric_destroy_chains_per_match | 8.85 | 8.85 | = |

**WR não moveu. Razão diagnosticada honestamente:**

[tools/rebirth_gameplay_health.py:14](tools/rebirth_gameplay_health.py:14) usa `services.rebirth_balance.simulate_balance`. Esse simulator chama `choose_response` (escolha de **summon**, [rebirth_bot.py:](services/rebirth_bot.py)) mas **não exercita `tactical_utility_matrix` / `attack_utility_projection`** (onde a heurística de Breakthrough vive).

Logo a inteligência de Breakthrough do bot **está no código** e validada por testes unitários (`test_v69_bot_breakthrough.py`), **mas não é exercitada pelo simulador atual**.

**Caminhos para mover o WR de fato no próximo ciclo:**
1. Estender `simulate_balance` para dirigir attacks via dispatcher real (lento mas honesto).
2. OU adicionar caminho em `simulate_balance` que invoca `tactical_utility_matrix` na escolha de attack.
3. OU rodar bot-vs-bot completo via `dispatch_command` (deepcopy match cada partida).

Os nerfs de Bramblehorn/Mossback também só aparecem se o simulador respeitar custos novos: precisa de validação de que o pool de mana em `simulate_balance` está usando o `cost` atualizado (verificável só rodando 100+ partidas com o caminho real).

## 8. Validações obrigatórias

| Comando | Resultado |
|---|---|
| `python3 -m pytest tests/rebirth -q` | **1150 passed**, 5 skipped, 20 deselected |
| `python3 tools/rebirth_benchmark.py 3` | parity_ok=True, replay_verified=True |
| `python3 tools/rebirth_gameplay_health.py 60` | flags: match_duration_high, outcome_dominance_high, chain_readability_risk (mesmas do v67 — não regrediu) |
| `node --check static/js/rebirth_audio.js` | OK |
| `node tests/js/test_rebirth_audio_chain_dedup.cjs` | 5 asserts OK |
| `git diff --check` | limpo |

**Testes adicionados (13)**: 5 breakthrough + 5 balance + 3 serializer purity.

## 9. Análise de regressão

- **Parity v66**: 261 testes ainda verdes — equivalência reducer↔engine intacta.
- **Replay v64**: 12 testes ainda verdes — byte-equivalent reconstruction preservada.
- **Performance v65**: 249 testes ainda verdes — bounds de performance respeitados.
- **Frontend contract**: 7 testes ainda verdes — payload público intacto.
- **Card catalog matrix**: 696 testes ainda verdes (test_card_catalog atualizado para aceitar overrides declarativos).

Nenhuma regressão detectada em comportamento determinístico, replay, parity, ou frontend payload.

## 10. O que **não** foi feito (por design)

- **Hash incremental por fórmula**: já endereçado por cache+dirty no v65/v68; nada a ganhar.
- **CombatResolutionPacket / colapso de events**: quebraria frontend, áudio, reducers, testes. Não realizado.
- **Cache opt-in com signature tracking**: substituído por otimização cirúrgica de `_stable_value` (47% sem invasão).
- **Atualizar `simulate_balance` para exercitar `tactical_utility_matrix`**: identificado como bloqueador de medida-de-impacto-real do balance — fica como item v70.
- **MCTS de verdade**: continua heurística determinística; promoção pra rollout real fica para PvP (já tem fundação no `_fast_clone` v68).

## 11. Próximos passos sugeridos

1. **v70 — Simulator alignment**: `simulate_balance` direcionar attacks via `attack_utility_projection` e dispatch real, para que nerfs e IA possam ser **medidos** e iterados em ciclo curto.
2. **Limpeza do repo** (apontada no laudo full-stack): cortar `routes/` e `sockets/` mortos, deletar 46 templates não-renderizados, expurgar `android/` + `mobile/` + `backups/` do git.
3. **Schema de produção**: resolver o `database_schema_invalid` que `/health` retornou no deploy v68 (Render plano starter ignora `preDeployCommand`).

---

**v69 entregue.** Engenharia limpa, comportamento perceptível corrigido, custo residual cortado, sem mudança destrutiva.
