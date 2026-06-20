# Rebirth Logic Priorities V107

Data: 2026-06-20

As sete prioridades de evolução da lógica foram implementadas.

## Entregas

1. API canônica de ações em `services/rebirth_actions.py`, com enumeração de
   ações legais, tradução para comandos e simulação sem mutar o estado original.
2. Matemática de combate compartilhada em `services/rebirth_combat_rules.py`,
   eliminando divergências entre engine e projeções do bot.
3. Busca determinística multi-ataque no bot, com principal variation, orçamento
   limitado e dificuldades `easy`, `normal` e `hard` separadas da personalidade.
4. Laboratório pareado em `services/rebirth_balance_lab.py`, com troca de lados
   por seed, viés de iniciativa, round-robin e regret de decisão.
5. Keyword `SUNDER` / Ruptura para midrange misto: bônus contra muralhas e
   quebra de Escudo no mesmo combate, sem buff genérico de SHADOW.
6. Invariantes e fuzzing determinístico em `services/rebirth_invariants.py`,
   cobrindo recursos, zonas, IDs, conservação, fases, eventos, hashes e replay.
7. Telemetria `decision_made`, com opções legais, ação escolhida, melhor ação,
   scores, regret, perfil, dificuldade e agregações no live balance.

## Resultado de balanceamento

- otimizado: jogador 46,7% / bot 53,3%;
- casual: jogador 56,7% / bot 43,3%;
- presença média de campo casual: 1,899;
- dead turn rate: 15,7%;
- stalemate: 0%;
- cadeia máxima observada: 16 eventos.

O laboratório pareado confirmou, na amostra de smoke dos decks padrão:

- viés de iniciativa: 0,0;
- lado jogador / lado bot: 50% / 50%;
- partidas inacabadas: 0%.

## Validação

- `1408 passed, 5 skipped, 22 deselected`;
- 10 fuzzings adicionais concluídos com invariantes e replay válidos;
- `node --check` verde para arena, deck builder e service worker;
- `py_compile` verde para os módulos alterados;
- navegador integrado não executou localhost devido à política de URL da
  superfície, portanto a validação visual ficou coberta pelos contratos
  frontend, baselines e testes E2E existentes.

Versões:

- engine: `rebirth_engine_v102`;
- card set: `rebirth_card_set_v102`;
- ruleset: `rebirth_ruleset_v102`;
- reducer: `rebirth_reducer_v100`;
- frontend/cache: `v107_LOGIC_SEARCH`.

## Sanity de balance independente (revisão pós-merge, 2026-06-20)

Reexecução de `simulate_balance(30)` e `simulate_casual_balance(30)` na
revisão, contra o reportado acima:

| Métrica | Reportado | Revisão |
|---|---|---|
| Casual — player WR | 56,7% | 53,3% |
| Casual — board presence | 1,899 | 1,842 |
| Casual — inacabadas | 0% | 0% |
| Otimizado — player WR | 46,7% | 36,7% |
| Otimizado — dead-turn | 15,7% | 15,4% |
| Otimizado — stalemate | 0% | 0% |
| Otimizado — max chain | 16 | 17 |

A estrutura do meta reproduz (sem stalemate, sem inacabadas; dead-turn e
cadeias batem). O WR otimizado cai puxado pelo bot `opportunist`, que tem
player WR **0,10 no otimizado vs 0,50 no casual** — o mesmo bot (em `normal`)
perde para o jogador casual mas vence o simulador "otimizado". Jogar
"perfeito" perdendo mais que jogar de novato é assinatura de **artefato de
medição do simulador** (cf. commit `047867a`, dead_turn era artefato), não
carta dominante nem bot forte demais para o jogador real.

Dificuldade default de produção: `easy` na 1ª partida, `normal` depois — o
lab também roda `normal`. Decisão: **não re-tunar no lab**; baseline
registrado e a telemetria `decision_made` (regret por perfil/dificuldade) de
produção é o árbitro real.
