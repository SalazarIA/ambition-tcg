# Rebirth — Roadmap Industrial de Lógica & Gameplay

Data: 2026-06-21 · Base: engine `v102` / release `v107_LOGIC_SEARCH` · Modelo: Opus 4.8
Foco: **lógica e gameplay**. Anti-escopo explícito no fim (visual/CSS, mobile, infra de deploy).

> Princípio que rege tudo abaixo: **o lab é telemetria, não gatilho de re-tuning cego**. Toda
> iniciativa de balance entra com instrumentação primeiro; o árbitro é `decision_made` em produção.

---

## 1. Sumário executivo

A base v107 é sólida: matemática de combate unificada ([rebirth_combat_rules.py](../services/rebirth_combat_rules.py)),
busca multi-ataque determinística no bot ([rebirth_bot.py](../services/rebirth_bot.py)), 11 keywords,
4 famílias, invariantes/fuzz ([rebirth_invariants.py](../services/rebirth_invariants.py)) e telemetria de
decisão. O que falta para um patamar **industrial** não é mais sistema — é **profundidade honesta** e
**observabilidade**. Três dívidas dominam: (a) a meta colapsa em Fortaleza EARTH porque WATER e SHADOW
não têm win-condition própria; (b) as dificuldades do bot diferem só em `budget/depth`, não em
personalidade de erro — um `easy` "burro" ainda joga linhas corretas, só mais rasas; (c) a infra de
cadeia/interrupção (`MAX_INTERRUPT_DEPTH`) existe mas é subutilizada, então a interação reativa é pobre.
O roadmap ataca isso em 4 ondas, começando pela observabilidade (risco ~zero) e terminando em
win-conditions alternativas (alto esforço). A régua de sucesso é sempre a telemetria de produção, não o lab.

---

## 2. Diagnóstico do estado atual (fundamentado)

| Sistema | Onde vive | Estado | Lacuna de gameplay |
|---|---|---|---|
| Combate | [rebirth_combat_rules.py](../services/rebirth_combat_rules.py), [rebirth_engine.py](../services/rebirth_engine.py) | Fonte única, consolidada | Fórmula madura; pouca interação reativa |
| IA do bot | [rebirth_bot.py](../services/rebirth_bot.py) `search_attack_sequences`, `BOT_DIFFICULTIES` | Beam search determinística; easy/normal/hard | Dificuldade = só profundidade; sem perfil de erro |
| Keywords | [rebirth_keywords.py](../services/rebirth_keywords.py) (RUSH…SUNDER, 11) | Funcionais, com cor/label | Cobertura desigual por família; SUNDER recém-nascido |
| Famílias | [rebirth_cards.py:15](../services/rebirth_cards.py) `FAMILY_CONFIGS` | FIRE/WATER/EARTH/SHADOW | WATER/SHADOW sem win-condition própria → hegemonia EARTH |
| Win-conditions | HP + `total_guard` ([rebirth_keywords.py:333](../services/rebirth_keywords.py)) | Só 2 | Estratégia converge para muralha EARTH |
| Sinergia | `synergy_active` (`controls_family`/`low_hp`/`field_count`/`tier_2`/`total_guard`) | 5 condições | Boa base, subexplorada por família |
| Interação | traps (`trap_effect`/trigger), `MAX_INTERRUPT_DEPTH=4` ([rebirth_domain.py](../services/rebirth_domain.py)) | Infra existe | Janelas de resposta rasas; decisões reativas escassas |
| Evolução | tier 1→2 por duplicata, `_monster_cost` canônico | Funciona | Evolução é quase automática, não decisão |
| Observabilidade | `decision_made` + [rebirth_live_balance.py](../services/rebirth_live_balance.py) | Evento + regret | Sem dashboard por arquétipo; lab fora do CI |

---

## 3. Tabela de priorização

Escala 1–5 (impacto/esforço/risco). **Alavancagem = impacto ÷ (esforço × risco)** — quanto maior, antes.

| # | Iniciativa | Impacto | Esforço | Risco | Onda |
|---|---|:--:|:--:|:--:|:--:|
| I1 | Telemetria de decisão como árbitro (WR por arquétipo/dificuldade) | 5 | 2 | 1 | **1** |
| I2 | Honestidade das dificuldades (perfil de erro, não só profundidade) | 4 | 2 | 2 | **1** |
| I3 | Fuzz/invariantes + golden replays p/ SUNDER e busca multi-ataque | 4 | 2 | 1 | **1** |
| I4 | Identidade/win-condition de WATER (inevitabilidade) e SHADOW (atrito) | 5 | 4 | 3 | **2** |
| I5 | Counters estruturais ao EARTH sem nerf cego | 4 | 3 | 3 | **2** |
| I6 | Auditoria de cobertura de keywords × família × mana-curve | 3 | 2 | 2 | **2** |
| I7 | Profundidade reativa: ativar `MAX_INTERRUPT_DEPTH`, traps ricas | 5 | 4 | 4 | **3** |
| I8 | Spells com alvo/stack mais expressivo | 3 | 3 | 3 | **3** |
| I9 | Win-conditions alternativas (atrito/combo) | 4 | 5 | 4 | **4** |
| I10 | Evolução/fusão como decisão estratégica | 3 | 4 | 3 | **4** |

---

## 4. Ondas

### Onda 1 — Fundação: observabilidade e honestidade (risco baixo)
Pré-requisito industrial: medir antes de mexer. Nada aqui altera o balance — só o torna legível e robusto.

**I1 · Telemetria de decisão como árbitro**
- *Gameplay:* transforma "achismo de lab" em fato de produção — sabemos qual arquétipo/dificuldade frustra jogadores reais.
- *Escopo:* agregar `decision_made` ([rebirth_telemetry.py](../services/rebirth_telemetry.py), [rebirth_live_balance.py](../services/rebirth_live_balance.py)) por `profile_id`×`difficulty`×família dominante do board; expor um relatório (reusar `match_telemetry_report.py` em `tools/`). Promover `rebirth_balance_lab` a **gate de CI** que falha se uma carta cruzar o flag `dominant`.
- *Riscos:* custo no caminho quente — já mitigado (telemetria observacional, `verify=False`, flag `REBIRTH_ENABLE_DECISION_TELEMETRY`). Manter assim.
- *DoD:* relatório de WR por arquétipo a partir de eventos reais; CI vermelho quando o lab detecta `dominant`.
- *Métrica:* cobertura de partidas com `decision_made`; tempo até detectar uma carta dominante cai de "playtest manual" para "CI".

**I2 · Honestidade das dificuldades**
- *Gameplay:* hoje `easy/normal/hard` só mudam `budget/depth` ([rebirth_bot.py](../services/rebirth_bot.py) `BOT_DIFFICULTIES`) — um `easy` ainda escolhe a linha certa, só vê menos à frente. Um bom `easy` deve **errar como humano** (não trocar quando devia, não enxergar lethal às vezes), e `hard` deve ter regret≈0.
- *Escopo:* adicionar um *perfil de erro* por dificuldade (probabilidade de pular a melhor `principal_variation`, ruído determinístico por seed) sem quebrar o determinismo; manter separado da personalidade (`defensive/aggressive/opportunist/novice`).
- *Riscos:* determinismo/replay — ruído tem de ser função pura de seed; cobrir com replay golden.
- *DoD:* `regret_p95` por dificuldade segue ordem `easy > normal > hard`; `hard` com `meaningful_regret_rate ≈ 0`.
- *Métrica:* curva de regret por dificuldade na telemetria; satisfação implícita (menos abandono em `easy`).

**I3 · Robustez das mecânicas novas**
- *Gameplay:* nada visível, mas é o que separa "feature" de "industrial": SUNDER e a busca não podem ter estados ilegais nem divergência de replay.
- *Escopo:* estender `run_deterministic_command_fuzz` ([rebirth_invariants.py](../services/rebirth_invariants.py)) para cobrir SUNDER (quebra de Escudo) e sequências multi-ataque; congelar **golden replays** de partidas-chave.
- *Riscos:* baixo.
- *DoD:* fuzz cobre as novas keywords; golden replays no CI; hash de estado estável.

### Onda 2 — Diversidade de arquétipos (ataca a hegemonia EARTH)
A meta colapsa em Fortaleza EARTH porque é a única família com win-condition própria (`total_guard`). A resposta industrial não é nerfar EARTH — é **dar a WATER e SHADOW uma razão de existir** e counters estruturais.

**I4 · Win-condition de WATER e SHADOW**
- *Gameplay:* WATER vira "inevitabilidade" (cura/tempo que vence o longo jogo); SHADOW vira "atrito" (deterioração/dreno que mina o oponente). Cada uma ganha um eixo de vitória que não é "ter a maior muralha".
- *Escopo:* novas condições de sinergia/win em `synergy_active` ([rebirth_keywords.py:306](../services/rebirth_keywords.py)) — ex. `sustained_heal` (WATER) e `decay_stacks`/`drain_total` (SHADOW); cartas-âncora em `FAMILY_CONFIGS` ([rebirth_cards.py:15](../services/rebirth_cards.py)) respeitando `_monster_cost`.
- *Riscos:* introduzir nova dominante — mitigar com I1 (lab como gate) antes do deploy.
- *DoD:* no lab pareado, EARTH deixa de ser modal; WATER e SHADOW têm WR ≥ 40% em ≥1 matchup.
- *Métrica:* distribuição de arquétipos vencedores em produção (telemetria) deixa de ser EARTH-pesada.

**I5 · Counters estruturais ao EARTH (sem nerf cego)**
- *Gameplay:* SUNDER foi o primeiro passo (anti-muralha condicionado a board misto). Ampliar a tesoura: efeitos que punem **passividade** (não-atacar) e ignoram Guarda condicionalmente, mantendo EARTH forte mas não inevitável.
- *Escopo:* nova keyword/efeito anti-stall em [rebirth_keywords.py](../services/rebirth_keywords.py) + hook em `damage_details`/`overflow_hero_damage` ([rebirth_combat_rules.py](../services/rebirth_combat_rules.py)); interagir com `ENTRENCH`/`THORNS` por design, não por número.
- *Riscos:* re-tuning cego — proibido; só entra com leitura de telemetria pós-I4.
- *DoD:* `dead_turn_rate` estável; EARTH WR converge para a faixa saudável sem cair de relevância.

**I6 · Auditoria de keywords × família × curva**
- *Gameplay:* garantir que cada família tem identidade mecânica nítida e que nenhuma keyword é "morta".
- *Escopo:* script de auditoria (em `tools/`) cruzando `ALL_KEYWORDS` × cartas que a possuem × `_monster_cost`; relatório de lacunas.
- *DoD:* cada keyword tem ≥N portadores e ≥1 sinergia; nenhuma família sem win-condition após I4.

### Onda 3 — Profundidade de interação reativa
O motor já tem `MAX_EFFECT_CHAIN_DEPTH=8` / `MAX_INTERRUPT_DEPTH=4` ([rebirth_domain.py](../services/rebirth_domain.py)) — capacidade de cadeia/interrupção **subutilizada**. É aqui que o jogo ganha "teto de skill".

**I7 · Janelas de resposta e traps ricas**
- *Gameplay:* decisões reativas reais (segurar uma trap, responder a um ataque) — o que diferencia um TCG raso de um profundo.
- *Escopo:* expandir `trap_effect`/trigger ([rebirth_cards.py:427](../services/rebirth_cards.py)) e o fluxo de resposta no [rebirth_dispatcher.py](../services/rebirth_dispatcher.py)/[rebirth_engine.py](../services/rebirth_engine.py); o bot precisa avaliar respostas (estender a projeção da busca para incluir interrupts).
- *Riscos:* **alto** — cadeias reativas estressam determinismo, replay e performance da busca. Mitigar: cap de profundidade já existe; cada incremento entra com fuzz (I3) e golden replay.
- *DoD:* partidas com cadeia reativa replicam bit-a-bit; busca do bot continua dentro do `CI_SAFE_SIMULATION_CEILING`.
- *Métrica:* aumento de decisões significativas por turno (telemetria `legal_action_count`) sem subir `dead_turn_rate`.

**I8 · Spells com alvo / stack mais expressivo**
- *Escopo:* enriquecer `stack_effects` ([rebirth_cards.py:394](../services/rebirth_cards.py)) com alvo e condicionais; reusar o enumerador de alvos já existente em `legal_actions` ([rebirth_actions.py](../services/rebirth_actions.py)).
- *DoD:* novos spells passam pelos invariantes; cobertura de `legal_actions` inclui os novos alvos.

### Onda 4 — Sistemas de longo prazo (alto esforço, alto teto)
Só após Ondas 1–3 estabilizadas e com telemetria sustentando as decisões.

**I9 · Win-conditions alternativas (atrito/combo)** — vitória por deck-out, por acúmulo de status, ou combo; cada uma com guarda rígida de determinismo/replay e gate de lab. Maior alavanca de variedade estratégica, maior risco de degenerar — entra por último.

**I10 · Evolução como decisão estratégica** — hoje a evolução por duplicata é quase automática; torná-la trade-off (tempo vs valor, sacrifício) usando `_monster_cost` como âncora. Aprofunda o early-game sem inflar a curva.

---

## 5. Sequenciamento recomendado

1. **Onda 1 inteira primeiro** (I1→I3): risco ~zero, e cria a régua (telemetria + lab-gate + golden replays) sem a qual as ondas seguintes são chute. I1 e I3 podem correr em paralelo; I2 depois de I1.
2. **Onda 2** com I4 antes de I5 (dar alternativa antes de mexer no counter), cada carta nova passando pelo lab-gate de I1.
3. **Onda 3** incremental: um tipo de interação reativa por vez, cada um com fuzz + golden replay. Nunca um "big bang" de stack.
4. **Onda 4** só quando produção mostrar meta saudável e diversa.

Regra transversal: **toda mudança mantém a suíte rápida verde, o determinismo do replay e o teto de busca do bot.** Nenhuma entra direto na `main` — feature branch → fast suite verde + juiz visual → fast-forward.

## 6. O que explicitamente NÃO faremos agora (anti-escopo)
- Visual/CSS/arte, animação de arena — fora do foco de lógica.
- Mobile (Capacitor/Play Store), ícones, splashes.
- Infra de deploy, Render, CI de build (exceto adicionar o **lab-gate** de gameplay, que é lógica).
- Re-tuning cego de números com base no lab — proibido por política; só com telemetria de produção.
- Multiplayer/PvP em tempo real — é outra trilha (arquitetura), não este roadmap de lógica de partida single.

## 7. Status de execução (2026-06-21)

**Onda 1 — entregue** (commits `e49dc57`): I1 lab-gate (`dominant_cards` + `simulate_balance` no CI) e decisão por arquétipo; I2 gradiente de erro do bot (easy 33% / normal 14% / hard 0%); I3 invariantes/replay/determinismo das mecânicas v107.

**Onda 2 — entregue:** I4 eixos próprios — WATER `high_hp` (inevitabilidade, cards 039/040), SHADOW `low_hp` (atrito, card 080), ao lado do EARTH `total_guard`. I5 keyword **SIEGE/Cerco** (ignora metade da mitigação de Guarda; capstones FIRE 018/020) — counter à Fortaleza sem nerf. I6 auditoria de cobertura (`keyword_coverage`, `family_synergy_coverage`) com testes-gate. Lab-gate confirmou: nenhuma carta dominante após as adições.

**Onda 3 — re-escopada e entregue:** ao ler o código, I7 e I8 **já estavam majoritariamente implementados** — 10 traps reativas disparam na interrupt chain (`opponent_attacks`/`owner_attacked`) e spells miram unidade via `_spell_effects_for_target`. Em vez de reinventar, a Onda 3 aplicou a **régua industrial** (invariantes + replay + determinismo) a esses caminhos (`test_rebirth_reactive_interaction.py`).

**Correção (2026-06-22):** uma versão anterior deste status afirmava que "o bot não arma nem usa traps" — **incorreto**, e o crédito da pega é da auditoria independente do Codex. O bot **já arma traps e joga spells de suporte** via `_bot_auto_play_support` ([rebirth_engine.py:892](../services/rebirth_engine.py)), pontuando-as em `_bot_support_score` ([rebirth_engine.py:855](../services/rebirth_engine.py)) — arma trap quando o jogador tem atacantes prontos ou pressão de board, com teto de 2 traps — e chamando `_arm_trap_card`. O erro veio de um `grep` restrito a `rebirth_bot.py`; a lógica de suporte do bot vive no engine.

**Gap real refinado (backlog):** a heurística de trap/suporte do bot é por **regras fixas** (`_bot_support_score`), **fora da busca multi-ataque / MCTS** — o bot *joga* traps mas não as *raciocina* na árvore de decisão, e esse uso reativo é **pouco coberto por teste/telemetria**. Integrar o suporte à busca e instrumentá-lo (quantas traps o bot arma, quando disparam, regret das escolhas de suporte) é o próximo passo de profundidade reativa. Alto risco: timing na interrupt chain + determinismo da busca.
