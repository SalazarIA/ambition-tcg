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

## Onda 3 — Camada de respostas ✅

**Achado:** a camada de respostas **já existe e é madura** — 10 traps reativos
(`opponent_attacks` / `owner_attacked`) num bus com `PRIORITY_INTERRUPT`
(negate, reflect, freeze, weaken, drain, shield, cleanse, heal…). No lab
disparam ~3/partida (TRAP_TRIGGERED 162 em 50 partidas). O catálogo é travado em
exatamente 100 cartas, então não se adicionam traps novos sem restruturar.

Logo, em vez de reconstruir um stack, a onda **amarra a represália ao
arquétipo**: o trap `reflect_damage` ("Espinhos Espelhados") agora escala com a
Guarda do board do controlador (`3 + min(3, guarda_total//6)`), unindo o tema
THORNS à camada de respostas. Archetype-gated (board de pouca Guarda mantém 3).

**Fairness provado por espelho** (mesmo deck dos dois lados):
- Fortaleza espelhada: **0,475** (justo).
- Agressão espelhada: 0,608 (vantagem do 1º a jogar).

O kit é justo. O drift do lab controlado (player ~0,46–0,48) é **artefato de
atribuição de deck** (o perfil "defensive" do bot recebe decks EARTH-heavy que
aproveitam a defesa mais forte) + o fato real de que **defender ficou mais
forte** — a ser re-centrado na Onda 4 (melhorar a agressão/lethal do bot).

## Onda 4 — IA do bot ✅

**A frente inverteu (medido).** O problema dos findings — "casual ganha 0,72
porque o bot perde pra agressão" — **já foi resolvido pelo trabalho de
profundidade**: o jogador casual agressivo caiu de **0,72 → 0,567** (o bot
agora defende bem contra agressão ingênua, via Fortaleza). O otimizado ficou
0,463/0,537 (bot levemente forte).

**Knobs de win-rate pioram** (medido): `defensive summon 1→2` estoura
(casual_player 0,567→0,433, otim_player 0,463→0,357) — com a Fortaleza o bot
defensivo já é forte; o knob antigo super-corrige. **Nenhum knob alterado.**
Para PvE, casual ~0,57 (ganha confortável, sem trivializar) + otimizado ~0,46
(jogador habilidoso é desafiado) é uma curva de dificuldade saudável.

**Ajuste de qualidade de decisão** (não de win-rate): o bot agora **respeita
THORNS** na projeção de troca (`attack_utility_projection`) — para de jogar
corpos em muralhas espinhadas sem lethal. Macro-neutro no lab (situação rara em
deck genérico), mas melhora a decisão real contra decks de Fortaleza.

> Item menor conhecido: `estimated_attack` do bot não espelha a sinergia K2
> (gap pré-existente); impacto baixo (o combate real aplica a sinergia de toda
> forma) — fica como tarefa de polish de IA.

## Onda 5 — ritmo & legibilidade ✅

**Achado 1 — `dead_turn_rate` era artefato de medição.** A detecção de turno
morto no lab ignorava invocação/evolução: um turno em que você desenvolve o
board (invoca, sem poder atacar por sickness) era contado como "morto".
Corrigido (`MEANINGFUL_TURN_EVENTS` inclui MONSTER_SUMMONED/CARD_SUMMONED/
CARD_EVOLVED): **0,476 → 0,173**. ~87% dos "mortos" eram turnos de
desenvolvimento. Metade da preocupação dos findings era a métrica, não o jogo.

**Achado 2 — ENTRENCH não causa "muro eterno".** Fortaleza espelhada (40 turnos
máx): `stalemate_frequency 0,000`, avg 9,2 turnos, pior cadeia 14. A win-con
(muralha contra-ataca + THORNS) faz a partida resolver — **sem necessidade de
cap em ENTRENCH**. O design evita o stall por construção.

**Cap de cadeia (`max_chain_events` 19):** mantido como item de telemetria
humana, **não** ajustado às cegas (guia dos próprios findings: capar a cadeia no
motor muda comportamento de combate). O K3 não piora cadeias (Fortaleza pior=14
< 19 genérico).

## Resumo das 4 frentes

| Frente | Estado | Evidência |
|---|---|---|
| #1 Arquétipos/win-con | ✅ Fortaleza viável | mirror justo 0,475; Fort-vs-Aggro 0,77 |
| #2 Respostas | ✅ já madura + tie-in | traps ~3/partida; reflect escala c/ muralha |
| #3 IA do bot | ✅ casual resolvido | 0,72 → 0,567; bot respeita THORNS |
| #4 Ritmo/legibilidade | ✅ métrica corrigida | dead_turn 0,476 → 0,173; 0 stalls |

Macro otimizado: 0,503/0,497 → ~0,46/0,54 (defesa ficou mais forte; **justo por
espelho**; re-centra com tuning de deck/IA agressiva futuro). Casual: saudável.
