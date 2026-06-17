# Rebirth — Roadmap de Profundidade (K3): 4 frentes da lógica

Trabalho nas 4 frentes deferidas pelos findings de 2026-06-15 (ver
[REBIRTH_PLAYTEST_FINDINGS.md](REBIRTH_PLAYTEST_FINDINGS.md)):
arquétipos/win-condition, respostas, IA do bot, ritmo/legibilidade.

Branch: `feat/game-depth-waves`. Filosofia mantida: **mudança grande só com
medição**; o lab (`simulate_controlled_balance` / `simulate_match`) é rede de
regressão, não verdade final.

## Baseline (contrato de regressão)

`simulate_controlled_balance(matches=300)` antes de qualquer mudança
(`/tmp/rb_baseline_full.json`):

| métrica | baseline |
|---|---|
| player_win_rate / bot_win_rate | 0,503 / 0,497 |
| dead_turn_rate | 0,476 |
| average_turns | 9,35 |
| max_chain_events | 19 |
| cluster EARTH base (média WR) | ~0,507 |

> **Achado:** o "cluster defensivo fraco 0,37–0,42" dos findings **não
> reproduz** no build atual — já foi corrigido pelos overrides v96 (custo de
> card_044/045, guarda de card_041…). Logo, a frente #1 deixou de ser resgate
> de número e passou a ser **profundidade de arquétipo**.

## Onda 1 — Keywords de Fortaleza (engine) ✅

Decisão de design (escolha do dono): **Fortaleza cirúrgica** — payoff defensivo
por keywords/sinergias, sem segundo recurso novo.

- `THORNS` (Espinhos): unidade atacada reflete 2 de Guarda ao atacante quando
  este vence/empata. Pune agressão contra a muralha.
- `ENTRENCH` (Entrincheirar): +1 de Guarda permanente por turno sem atacar.
  Recompensa segurar a linha (turno defensivo deixa de ser turno morto).
- Sinergia K2 `total_guard`: a muralha **contra-ataca** (bônus de ataque)
  quando a Guarda somada do board atinge o limiar — a win-condition.

Wire: THORNS em `resolve_turn` (cobre ataque do player e do bot, antes do
cleanup); ENTRENCH no tick de início de turno; sinergia em `clash_attack` via
`_synergy_bonuses`. **Lab idêntico ao baseline** (keywords não usadas ainda) →
prova de wiring inerte. Testes em `tests/rebirth/test_k3_fortress.py`.

## Onda 2 — Arquétipo EARTH de Fortaleza ✅

Kit aplicado pelas tabelas de override (sem mexer na curva `_monster_cost`):

- Muralhas evoluídas: `card_051` SHIELD+TAUNT+THORNS, `card_059`
  SHIELD+TAUNT+ENTRENCH, `card_056` SHIELD+THORNS, `card_058`/`card_060`
  SHIELD+ENTRENCH.
- Âncoras da win-con (só **sinergia**, preservando "tier-1 limpo de keyword"):
  `card_044`/`card_050` (base) e `card_060` (evo), `total_guard ≥ 6`.

Achados medidos:

- **TAUNT precisa andar com THORNS na mesma carta.** Na 1ª versão, TAUNT (051)
  protegia a carta de THORNS (056) → a punição nunca acontecia. Corrigido:
  a muralha provocadora é a espinhada.
- **ENTRENCH e a sinergia disparam** em jogo real (instrumentado:
  ENTRENCH_TICK 15/60 partidas; sinergia em decks semi-concentrados). THORNS
  dispara pouco **no lab** porque o `simulate_match` faz o "player" ser sempre o
  agressor — na mão do defensor (uso real da Fortaleza) ele pune muito mais.
- **Macro preservado:** 600 partidas → player 0,48 / bot 0,52 (dentro do ruído,
  EP ~2,0pp). `dead_turn` +0,9pp (muralhas vivem mais — alvo da Onda 5).
- **Deck-building viável:** Fortaleza dedicada vence Agressão ~0,77 — a
  profundidade pedida existe (defender agora é uma estratégia que ganha).

Versões bumpadas: ENGINE/CARD_SET/RULESET → v100 (reducers/replay-format
inalterados → mantêm versão). Paridade e replay verdes (45/45).

## Próximas ondas

- **Onda 3** — respostas: aprofundar traps reativos (sobre o motor existente).
- **Onda 4** — IA do bot: punir board aberto / fechar lethal; revalidar o macro.
- **Onda 5** — ritmo: reduzir `dead_turn_rate` e capar cadeias (19→~15).
