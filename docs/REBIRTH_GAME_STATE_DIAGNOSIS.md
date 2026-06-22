# Rebirth — diagnóstico do estado atual do jogo

Data do diagnóstico: 2026-06-21  
Base declarada: engine `v102` / release lógica `v107_LOGIC_SEARCH`  
Escopo: lógica e gameplay; nenhuma alteração de código ou balance.

## 1. Sumário executivo

O estado atual é **jogável e estruturalmente saudável**, mas ainda não há evidência de produção suficiente para declarar o meta balanceado:

- não houve stalemate nem partida inacabada nos lotes observados;
- o lab casual ficou dentro da faixa de saúde documentada, com `53,3%` de WR do jogador, `10,07` turnos médios e presença de board `1,832`;
- o lab otimizado de 30 partidas favoreceu o bot (`63,3%`), porém essa leitura não foi estável: em 200 partidas controladas o resultado convergiu para `53,0%` do bot;
- nenhuma carta acionou o gate `dominant`, tanto no raio-x de 30 partidas quanto na sensibilidade de 200;
- a matriz mono-família aponta EARTH como melhor e SHADOW como pior, mas o teste usa decks ilegais para produção — 30 monstros, sem spells/traps — e desativa por construção o `SUNDER` de SHADOW, que exige aliado de outra família;
- a saída `ARQUETIPOS WR` está inflada por espelhos computados como `100%`, e `INICIATIVA` mede principalmente assimetria entre a política do “player” do simulador e a IA do bot, não iniciativa pura;
- não existe amostra local utilizável de produção: foram encontrados `0` jogos concluídos e `0` eventos `decision_made`;
- o backlog “bot não usa traps” está **desatualizado em relação à árvore atual**. O bot tem traps no deck padrão, pontua essas cartas e as arma. A lacuna real é mais estreita: traps/spells do bot são escolhidas por heurística separada, fora da busca, da dificuldade e da telemetria de regret.

Conclusão operacional: **não fazer re-tuning agora**. Primeiro, corrigir a semântica das medições e obter telemetria humana suficiente. O próprio roadmap determina que o lab é telemetria, não gatilho de tuning (`docs/REBIRTH_INDUSTRIAL_ROADMAP_LOGIC.md:6-7`).

## 2. Fontes e método

Foram usados:

- o raio-x solicitado, sem alteração;
- `tools/rebirth_gameplay_health.py`;
- uma sensibilidade de 200 partidas com `simulate_controlled_balance`;
- uma sensibilidade casual de 200 partidas;
- `services.rebirth_live_balance.live_balance_report`;
- `tools/rebirth_telemetry_analyzer.py`;
- inspeção de `tools/audit_*.py`, `tools/balance_report.py`, `tools/rebirth_balance_report.py`, `tools/rebirth_balance_harness.py` e `tools/match_telemetry_report.py`;
- inspeção do roadmap e das implementações atuais.

Ferramentas consideradas autoritativas para Rebirth:

- `services/rebirth_balance.py`;
- `services/rebirth_balance_lab.py`;
- `tools/rebirth_gameplay_health.py`;
- `tools/rebirth_balance_report.py`;
- `tools/rebirth_balance_harness.py`;
- `services/rebirth_live_balance.py`;
- `tools/rebirth_telemetry_analyzer.py`.

`tools/balance_report.py` usa o catálogo legado `game.cards`, e `tools/match_telemetry_report.py` consulta `MatchTelemetry` e se identifica como relatório “Ambitionz V1.05”; portanto não foram usados como árbitros do módulo Rebirth.

## 3. Saída crua do raio-x solicitado

```text
OTIMIZADO: {'player_win_rate': 0.367, 'bot_win_rate': 0.633, 'unfinished_rate': 0.0, 'average_turns': 8.8, 'lethal_frequency': 1.0, 'dead_turn_rate': 0.174, 'stalemate_frequency': 0.0, 'events_per_turn': 34.06, 'trigger_events_per_turn': 7.59, 'symmetric_destroy_chains_per_match': 2.07, 'max_chain_events': 17}
CASUAL: {'player_win_rate': 0.533, 'bot_win_rate': 0.467, 'unfinished_rate': 0.0, 'average_turns': 10.07, 'board_presence': 1.832}
DOMINANTES (gate I1): []
EIXOS POR FAMILIA: {'FIRE': ['controls_family', 'low_hp'], 'WATER': ['controls_family', 'field_count', 'high_hp'], 'EARTH': ['controls_family', 'tier_2', 'total_guard'], 'SHADOW': ['controls_family', 'low_hp']}
KEYWORDS (n portadores): {'BURST': 21, 'ENTRENCH': 3, 'EXECUTE': 2, 'LIFESTEAL': 10, 'PIERCE': 11, 'REGEN': 10, 'RUSH': 10, 'SHIELD': 11, 'SIEGE': 2, 'SUNDER': 3, 'TAUNT': 3, 'THORNS': 2}
ARQUETIPOS WR: [('EARTH', 0.719), ('FIRE', 0.672), ('WATER', 0.625), ('SHADOW', 0.484)]
MATRIZ matchups: {'EARTH': {'EARTH': 1.0, 'FIRE': 0.5, 'SHADOW': 0.75, 'WATER': 0.625}, 'FIRE': {'EARTH': 0.5, 'FIRE': 1.0, 'SHADOW': 0.562, 'WATER': 0.625}, 'SHADOW': {'EARTH': 0.25, 'FIRE': 0.438, 'SHADOW': 1.0, 'WATER': 0.25}, 'WATER': {'EARTH': 0.375, 'FIRE': 0.375, 'SHADOW': 0.75, 'WATER': 1.0}}
INICIATIVA: {'game_count': 160, 'player_side_win_rate': 0.419, 'bot_side_win_rate': 0.581, 'initiative_bias': -0.081, 'unfinished_rate': 0.0}
CARTAS-PROBLEMA: [('card_046', ['low-impact']), ('card_053', ['unused']), ('card_060', ['unused']), ('card_056', ['unused']), ('card_054', ['unused']), ('card_058', ['unused']), ('card_051', ['unused']), ('card_013', ['unused']), ('card_011', ['unused']), ('card_014', ['unused']), ('card_017', ['unused']), ('card_015', ['unused']), ('card_019', ['unused']), ('card_016', ['unused']), ('card_018', ['unused']), ('card_079', ['unused']), ('card_077', ['unused']), ('card_071', ['unused']), ('card_074', ['unused']), ('card_072', ['unused']), ('card_073', ['unused']), ('card_078', ['unused']), ('legend_shadow_reaper', ['unused']), ('card_084', ['selection-biased-win-rate']), ('card_037', ['unused']), ('card_036', ['unused']), ('card_039', ['unused']), ('card_031', ['unused']), ('card_038', ['unused']), ('card_034', ['unused']), ('card_035', ['unused']), ('card_032', ['unused'])]
```

## 4. Estado de balance

### 4.1 Otimizado versus casual

| Visão | Partidas | WR jogador | WR bot | Turnos | Dead-turn | Stalemate | Board presence |
|---|---:|---:|---:|---:|---:|---:|---:|
| Otimizado solicitado | 30 | 36,7% | 63,3% | 8,80 | 17,4% | 0% | não medido |
| Casual solicitado | 30 | 53,3% | 46,7% | 10,07 | não medido | 0% | 1,832 |
| Otimizado, sensibilidade | 200 | 47,0% | 53,0% | 8,10 | 16,9% | 0% | não medido |
| Casual, sensibilidade | 200 | 58,5% | 41,5% | 9,22 | não medido | 0% | 1,919 |

O resultado otimizado de 30 partidas é volátil e não deve ser lido como dominância consolidada do bot. A sensibilidade de 200 partidas ficou próxima de 50/50 e continuou sem stalemate ou unfinished.

Também não é válido concluir que “o casual joga melhor que o otimizado”. Os dois labs não diferem apenas na qualidade da decisão:

- o otimizado usa decks sazonais rotativos com spells e traps (`services/rebirth_balance.py:87-125`, `694-702`);
- o casual usa os decks padrão ao chamar `start_match` sem decks customizados (`services/rebirth_balance.py:891-892`);
- o casual não evolui, escolhe alvos por regra simples e joga no máximo uma magia após as invocações (`services/rebirth_balance.py:895-975`);
- o otimizado evolui, joga suporte tático e projeta trades (`services/rebirth_balance.py:134-194`, `434-503`).

Portanto, são duas sondas diferentes de saúde, não dois níveis comparáveis de habilidade.

### 4.2 Dead-turn, stalemate e presença de board

- `dead_turn_rate=17,4%` está abaixo do teto de `22%` usado pelo health check (`tools/rebirth_gameplay_health.py:41-42`);
- `stalemate_frequency=0` está abaixo do teto de `15%` (`tools/rebirth_gameplay_health.py:31-33`);
- `board_presence=1,832` supera a meta casual documentada de `1,0` (`services/rebirth_balance.py:881-888`);
- duração média de `8,8`/`10,07` turnos fica com ampla margem abaixo do teto operacional de `24` (`tools/rebirth_gameplay_health.py:34-38`).

Esses sinais sustentam que o loop básico não está travado, vazio ou excessivamente longo.

### 4.3 Densidade de eventos e legibilidade

O health check marcou:

- `trigger_density_high`: `7,59` eventos de trigger por turno, contra limiar `4`;
- `chain_readability_risk`: cadeia máxima `17`, contra limiar `15`;
- `bot_profile_difficulty_spread_high`.

Os dois primeiros são sinais reais de complexidade de resolução e merecem playtest focado em compreensão da cadeia. Não implicam nerf automático.

O terceiro nome é enganoso: a ferramenta calcula spread entre **perfis** do bot, não dificuldades (`tools/rebirth_gameplay_health.py:47-49`). Além disso, cada perfil recebe rotações de deck diferentes porque `profile_id` entra no seed do deck (`services/rebirth_balance.py:95-97`, `694-702`). O número não isola personalidade nem dificuldade.

## 5. Viabilidade dos quatro arquétipos

### 5.1 Matriz observada

Linhas vencendo colunas:

| Arquétipo | FIRE | WATER | EARTH | SHADOW |
|---|---:|---:|---:|---:|
| FIRE | artefato | 62,5% | 50,0% | 56,2% |
| WATER | 37,5% | artefato | 37,5% | 75,0% |
| EARTH | 50,0% | 62,5% | artefato | 75,0% |
| SHADOW | 43,8% | 25,0% | 25,0% | artefato |

Excluindo os espelhos defeituosos, a média dos três matchups cruzados é:

| Arquétipo | WR cruzado derivado da matriz |
|---|---:|
| EARTH | 62,5% |
| FIRE | 56,2% |
| WATER | 50,0% |
| SHADOW | 31,3% |

Essa segunda tabela é uma derivação da matriz crua, não uma nova simulação.

### 5.2 Artefatos importantes do round-robin

1. **Espelhos são inválidos.** O round-robin inclui `left == right`; `paired_matchup` agrega as vitórias pelo nome do deck e divide pelo total de jogos (`services/rebirth_balance_lab.py:110-124`). Como os dois lados têm o mesmo nome, toda vitória conta para a mesma chave, produzindo diagonal `1,0`. Depois, esses espelhos entram nos standings (`services/rebirth_balance_lab.py:169-200`), inflando todos os WRs publicados em `ARQUETIPOS WR`. **(Corrigido em `32d8bc3`: o round-robin passou a agregar só matchups cruzados e a diagonal vira `None`; standings reais — EARTH 0,625 / FIRE 0,562 / WATER 0,500 / SHADOW 0,312.)**

2. **“Iniciativa” não é iniciativa pura.** O pareamento troca os decks de lado, mas mantém duas políticas diferentes: o lado `player` usa o piloto tático de `simulate_match`, enquanto o lado `bot` usa a IA do engine (`services/rebirth_balance_lab.py:62-98`; `services/rebirth_balance.py:413-503`). Assim, `41,9%` versus `58,1%` mede principalmente lado/agente, não apenas quem começou.

3. **Os decks do comando são probes ilegais para produção.** Cada deck tem 30 monstros e nenhum suporte. O contrato do catálogo define mínimo 18 e máximo 22 monstros (`services/rebirth_cards.py:9-11`), enquanto o construtor sazonal legal valida a distribuição (`services/rebirth_balance.py:103-125`).

4. **SHADOW perde sua ferramenta anti-muralha.** `SUNDER` exige um aliado de outra família (`services/rebirth_keywords.py:270-287`). Em um deck mono-SHADOW, as três portadoras nunca ativam Ruptura. FIRE, em contraste, usa `SIEGE` sem requisito de board misto.

Logo, a matriz é útil como stress test mecânico, mas não mede o meta de produção.

### 5.3 Leitura por família

#### EARTH — dominante no probe, mas não comprovadamente dominante em produção

EARTH empata com FIRE e vence WATER/SHADOW. A causa provável é estrutural:

- três âncoras de `total_guard` (`card_044`, `card_050`, `card_060`) recebem ataque quando o board soma Guarda suficiente (`services/rebirth_cards.py:604-613`);
- `total_guard` conta a Guarda atual de todo o board e usa limiar baixo o bastante para dois corpos EARTH (`services/rebirth_keywords.py:345-350`);
- as evoluídas recebem `SHIELD`, que ignora a primeira instância de dano (`services/rebirth_keywords.py:118-123`; `services/rebirth_engine.py:1567-1619`);
- `TAUNT`, `THORNS` e `ENTRENCH` concentram-se em capstones EARTH (`services/rebirth_cards.py:570-577`).

Isto é uma vantagem real de coesão no probe. Ainda assim, `dominant_cards=[]` e a ausência de produção impedem chamar a família de quebrada.

#### FIRE — viável e cumpre o papel anti-sustain

FIRE empata com EARTH e vence WATER/SHADOW:

- `BURST` existe em FIRE desde tier 1 e causa dano direto ao invocar (`services/rebirth_keywords.py:128-137`, `193-202`);
- `card_018` e `card_020` têm `SIEGE`, que reduz a mitigação efetiva da Guarda (`services/rebirth_cards.py:584-587`; `services/rebirth_combat_rules.py:136-144`).

O resultado contra EARTH sugere que Cerco está cumprindo a função de tesoura sem apagar a Fortaleza.

#### WATER — funcional, mas polarizada

WATER derrota SHADOW, porém perde para FIRE e EARTH:

- `card_039` e `card_040` ativam `high_hp` a partir de 24 PV (`services/rebirth_cards.py:614-619`);
- evoluídas recebem `LIFESTEAL + REGEN` (`services/rebirth_keywords.py:118-123`, `144-149`);
- lifesteal cura pelo dano causado e regen recompõe Guarda (`services/rebirth_keywords.py:205-209`; `services/rebirth_engine.py:2444-2465`).

O eixo liga cedo enquanto WATER está saudável, mas BURST/SIEGE contornam sustain e EARTH constrói mais valor de board.

#### SHADOW — sinal vermelho do probe, com forte componente de medição

SHADOW perde os três matchups cruzados. Existem três causas prováveis:

- `low_hp` só liga em 12/14 PV nas âncoras relevantes, portanto o payoff chega tarde (`services/rebirth_cards.py:602-603`, `617-619`; `services/rebirth_keywords.py:331-338`);
- `SUNDER` é impossível no deck mono-família usado pelo raio-x;
- a identidade básica `PIERCE` só entra nas cartas tier 2+ (`services/rebirth_keywords.py:118-123`, `155-172`), enquanto FIRE já leva BURST no tier 1.

Classificação: **risco real de viabilidade**, mas ainda não evidência suficiente para buff. O próximo teste deve usar decks legais e representativos — inclusive shells mistos que possam ativar SUNDER — e depois confrontar a telemetria humana.

## 6. Honestidade das dificuldades do bot

### 6.1 O que o código garante

As dificuldades não diferem apenas por profundidade:

- easy: `depth=1`, `budget=6`, `mistake_window=2`;
- normal: `depth=2`, `budget=16`, `mistake_window=6`;
- hard: `depth=3`, `budget=24`, `mistake_window=0`.

Fonte: `services/rebirth_bot.py:25-54`.

O ruído é determinístico por partida/turno/perfil e não é aplicado em janela de lethal (`services/rebirth_bot.py:840-879`). O teste industrial verifica que easy diverge mais que normal, e normal mais que hard (`tests/rebirth/test_rebirth_logic_priorities.py:237-274`).

Reexecutando o cenário sintético de 63 decisões do teste:

| Dificuldade | Divergências contra hard |
|---|---:|
| easy | 26/63, 41,3% |
| normal | 12/63, 19,0% |
| hard | 0/63, 0% |

Isso comprova o contrato determinístico, não a experiência real do jogador.

### 6.2 Telemetria real disponível

Não há dados suficientes para reportar WR por arquétipo, WR por dificuldade ou regret por dificuldade.

Dados locais encontrados:

- `instance/rebirth.db`: 199 eventos entre 2026-05-26 e 2026-06-01;
- 91 `match_started`, 50 `card_played`, 31 `turn_ended`, 18 `combat_resolved`, 9 `match_abandoned`;
- 0 `match_finished`;
- 0 `decision_made`;
- `instance/database.db`: 0 eventos.

O relatório real retornou:

```text
human_match_gate.state: insufficient_sample
required_finished_matches: 500
observed_finished_matches: 0
matches_abandoned: 9
decision_count: 0
by_difficulty: []
by_archetype: []
flags: [low_sample_size, needs_human_telemetry]
```

O gate de produção exige 500 partidas concluídas (`services/rebirth_live_balance.py:11-12`, `214-243`). A amostra local antecede a entrega da Onda 1 em 2026-06-21, portanto sua ausência de `decision_made` não prova falha da instrumentação atual.

### 6.3 Lacunas de medição da dificuldade

- a telemetria do bot captura somente `ATTACK_DECLARED`; invocação, spell e trap não entram no regret (`app.py:846-885`);
- `live_balance_report` agrega dificuldade, perfil e arquétipo em listas independentes, não no cruzamento dificuldade × perfil × arquétipo (`services/rebirth_live_balance.py:224-235`);
- `best_search_score` é o topo da busca, mas a escolha passa antes pela personalidade. Assim, regret pode misturar “erro de dificuldade” com preferência intencional de perfil (`services/rebirth_bot.py:830-879`).

Portanto, a honestidade das dificuldades está implementada no contrato sintético, mas **não está validada em produção**.

## 7. Interação reativa: traps e spells

### 7.1 Estado atual

O catálogo tem:

- 10 spells (`services/rebirth_cards.py:198-209`);
- 10 traps (`services/rebirth_cards.py:212-223`);
- traps face-down com trigger de combate (`services/rebirth_cards.py:426-456`);
- disparo apenas pelo lado atacado, inclusive em ataque direto (`services/rebirth_engine.py:1162-1243`);
- spells de dano com alvo de unidade cobertas por invariantes/replay (`tests/rebirth/test_rebirth_reactive_interaction.py:32-44`).

### 7.2 O “bot não usa traps” não corresponde ao código atual

O deck padrão do bot contém `card_096`–`card_100`, todas traps (`services/rebirth_cards.py:696-728`). A engine:

- pontua traps conforme pressão, turno, custo e limite de duas armadas (`services/rebirth_engine.py:841-864`);
- reserva mana para monstros;
- remove a trap da mão e chama `_arm_trap_card` (`services/rebirth_engine.py:892-927`);
- executa esse suporte antes dos ataques do bot (`services/rebirth_engine.py:2521-2528`).

Validação executada em estado controlado:

```text
BOT_DECK_SUPPORT: [('card_083', 'SPELL'), ('card_082', 'SPELL'), ('card_087', 'SPELL'), ('card_088', 'SPELL'), ('card_089', 'SPELL'), ('card_096', 'TRAP'), ('card_097', 'TRAP'), ('card_098', 'TRAP'), ('card_099', 'TRAP'), ('card_100', 'TRAP')]
TRAP_ARMADA: [('card_096', True, True)]
ENERGIA_RESTANTE: 1
EVENTOS_FINAIS: [('MATCH_STARTED', None), ('BOT_DECISION', 'card_096'), ('TRAP_ARMED', 'card_096')]
```

O roadmap está desatualizado nesse ponto (`docs/REBIRTH_INDUSTRIAL_ROADMAP_LOGIC.md:152-154`).

### 7.3 Gap reativo real

O bot **usa** traps, mas não as **planeja** dentro da busca:

- a escolha de suporte usa uma tabela heurística separada e recebe `profile_id`, mas não `difficulty_id`;
- o regret do bot só observa ataques;
- os testes de interação reativa exercitam principalmente traps do jogador contra ataques do bot (`tests/rebirth/test_rebirth_reactive_interaction.py:17-29`);
- o teste de lab só exige que alguma trap tenha sido usada, sem verificar o lado (`tests/rebirth/test_rebirth_bot_personalities.py:60-69`).

O backlog correto é integrar suporte/interrupts ao horizonte decisório e à telemetria, não “ensinar o bot a armar traps do zero”.

## 8. Cobertura de keywords e eixos de família

### 8.1 Keywords

Não há keyword com zero portadores no mapa retornado.

Cobertura esparsa:

| Keyword | Portadores | Leitura |
|---|---:|---|
| EXECUTE | 2 | rara e forte; monitorar, não espalhar automaticamente |
| SIEGE | 2 | counter concentrado em dois capstones FIRE |
| THORNS | 2 | concentrada em EARTH |
| ENTRENCH | 3 | concentrada em EARTH |
| SUNDER | 3 | concentrada em SHADOW e dependente de board misto |
| TAUNT | 3 | concentrada em EARTH/lendária |

A concentração é parcialmente intencional: o código registra que TAUNT/EXECUTE e outros overrides fortes devem ser opt-in (`services/rebirth_cards.py:568-587`; `services/rebirth_keywords.py:159-162`).

O problema de cobertura não é apenas “quantas cartas têm a keyword”, mas **se a condição é ativável no arquétipo medido**. SUNDER tem três portadoras e mesmo assim cobertura efetiva zero no probe mono-SHADOW.

### 8.2 Eixos de família

Todas as famílias têm condições registradas, mas a auditoria atual mede presença, não distinção (`services/rebirth_cards.py:639-659`):

- WATER tem eixo exclusivo `high_hp`;
- EARTH tem eixo exclusivo `total_guard`;
- FIRE e SHADOW expõem exatamente `controls_family + low_hp`.

SHADOW tem identidade adicional por dreno/decay/PIERCE, porém seu “eixo de família” não é único na saída de cobertura. Logo, não há família sem eixo, mas há uma lacuna semântica: **cobertura aprovada não significa identidade distinta**.

## 9. Cartas-problema

### 9.1 Dominant

Nenhuma:

```text
DOMINANTES (gate I1): []
```

O gate só promove cartas com flag literal `dominant` (`services/rebirth_balance_lab.py:211-228`). A sensibilidade de 200 partidas também retornou `[]`.

### 9.2 Low-impact

Raio-x de 30:

- `card_046` — Bramblehorn Knight: 12 usos, WR `18,2%`, dano médio `0,67`.

O flag exige uso mínimo, WR ≤ 20% e dano médio ≤ 0,75 (`services/rebirth_balance.py:862-872`). Entretanto, `card_046` deixou de ser flagada na sensibilidade de 200 partidas. Classificação: **sinal instável de amostra, não problema confirmado**.

### 9.3 Unused

No lote de 30, 30 cartas foram marcadas:

- EARTH: `card_051`, `053`, `054`, `056`, `058`, `060`;
- FIRE: `card_011`, `013`, `014`, `015`, `016`, `017`, `018`, `019`;
- SHADOW: `card_071`, `072`, `073`, `074`, `077`, `078`, `079`, `legend_shadow_reaper`;
- WATER: `card_031`, `032`, `034`, `035`, `036`, `037`, `038`, `039`.

Quase todas são evoluídas ou lendária. O flag `unused` é aplicado sempre que `plays == 0`, sem intervalo de confiança ou exposição mínima (`services/rebirth_balance.py:862-866`).

Na sensibilidade de 200 partidas, sobraram apenas sete `unused`:

```text
card_012, card_014, card_032, card_034, card_052, card_053, card_055
```

Classificação: **principalmente artefato de cobertura/evolução do lab**. Não há telemetria humana para confirmar carta morta.

### 9.4 Selection-biased-win-rate

- `card_084` — Bola de Fogo da Arena: 10 usos, WR `80%`, dano médio `3,0` no lote de 30;
- em 200 partidas: 50 usos, WR `86%`, dano médio `3,0`.

O próprio lab trata Fireball como finalizador contextual: ela só é jogada quando existe janela favorável e recebe `selection-biased-win-rate`, não `dominant` (`services/rebirth_balance.py:845-870`). Classificação: **viés conhecido de seleção**, não evidência de carta quebrada.

### 9.5 Dead-hand-risk

Nenhuma carta recebeu `dead-hand-risk` no raio-x ou na sensibilidade de 200. O flag exigiria aparecer morta na mão em pelo menos 40% das partidas (`services/rebirth_balance.py:873-874`).

## 10. Lacunas priorizadas

### P0 — Obter telemetria humana válida

- **Tipo:** lacuna de medição; bloqueia decisões de balance.
- **Impacto:** muito alto.
- **Esforço:** baixo a médio operacional.
- **Evidência:** 0 partidas concluídas e 0 decisões locais; gate exige 500 concluídas.
- **Recomendação:** verificar ingestão no ambiente realmente produtivo, cobertura de `match_finished` e `decision_made`, versão de release e retenção; só avaliar tuning após o gate.
- **Arquivos afetados em trabalho futuro:** `app.py`, `services/rebirth_telemetry.py`, `services/rebirth_live_balance.py`, `tools/rebirth_telemetry_analyzer.py`.

### P1 — Corrigir semântica do round-robin e do relatório de “iniciativa”

- **Tipo:** artefato de medição.
- **Impacto:** muito alto.
- **Esforço:** baixo.
- **Evidência:** espelhos viram 100%, standings incluem espelhos, e lado do simulador é confundido com iniciativa.
- **Recomendação:** excluir espelhos dos standings ou tratá-los com identidades A/B distintas; publicar WR cruzado; renomear a métrica para `side_policy_bias` até existir teste com a mesma política nos dois lados.
- **Arquivos afetados:** `services/rebirth_balance_lab.py`, `tests/rebirth/test_rebirth_balance_lab.py`.
- **Status (2026-06-22):** a inflação por espelhos foi **resolvida** (`32d8bc3`) — `round_robin` agrega só matchups cruzados, diagonal `None`, com teste de regressão. **Pendente:** renomear `INICIATIVA` para `side_policy_bias` e rodar a mesma política nos dois lados antes de lê-la como iniciativa pura.

### P1 — Isolar perfil, dificuldade, deck e regret

- **Tipo:** artefato de medição com efeito direto sobre gameplay.
- **Impacto:** muito alto.
- **Esforço:** médio.
- **Evidência:** perfil altera o seed dos decks; health check chama perfil de dificuldade; regret mistura personalidade e erro injetado; agregações não são cruzadas.
- **Recomendação:** rodar os mesmos decks/seeds para cada perfil/dificuldade; separar `policy_regret` de `mistake_regret`; agregar perfil × dificuldade × arquétipo; não comparar perfis com decks distintos.
- **Arquivos afetados:** `services/rebirth_balance.py`, `services/rebirth_bot.py`, `services/rebirth_telemetry.py`, `services/rebirth_live_balance.py`, `tools/rebirth_gameplay_health.py`.

### P1 — Integrar traps/spells do bot à decisão planejada

- **Tipo:** problema real de profundidade de gameplay.
- **Impacto:** alto.
- **Esforço:** alto.
- **Evidência:** o bot arma traps, porém por heurística fora da busca/dificuldade/regret.
- **Recomendação:** enumerar ações de suporte no horizonte do agente, respeitando orçamento e determinismo; emitir `decision_made` para spell/trap; criar teste end-to-end em que o bot arma e dispara cada classe de trap.
- **Arquivos afetados:** `services/rebirth_bot.py`, `services/rebirth_engine.py`, `app.py`, `tests/rebirth/test_rebirth_reactive_interaction.py`.

### P2 — Validar SHADOW com arquétipos legais e ativáveis

- **Tipo:** risco real de gameplay, hoje ampliado pelo lab.
- **Impacto:** alto.
- **Esforço:** baixo para medir; alto apenas se produção confirmar tuning.
- **Evidência:** WR cruzado derivado `31,3%`; SUNDER impossível no deck mono-SHADOW; payoff `low_hp` tardio.
- **Recomendação:** criar fixtures legais de 30 cartas com 18–22 monstros, suporte e shell misto para SUNDER; repetir pareamentos; comparar com WR/adoção humana. Não alterar números antes disso.
- **Arquivos afetados:** inicialmente `services/rebirth_balance_lab.py` e testes/fixtures; somente depois, se produção confirmar, `services/rebirth_cards.py`/`services/rebirth_keywords.py`.

### P2 — Reduzir risco de ilegibilidade da cadeia sem reduzir profundidade

- **Tipo:** possível problema real de experiência/decisão.
- **Impacto:** médio.
- **Esforço:** médio.
- **Evidência:** `7,59` triggers/turno e cadeia máxima `17`, ambos acima dos limiares do health check.
- **Recomendação:** medir distribuição e origem das cadeias, separar eventos técnicos de decisões significativas e identificar loops de baixa informação. Só depois considerar simplificação de resolução.
- **Arquivos afetados:** `services/rebirth_balance.py`, `tools/rebirth_gameplay_health.py`, event bus/telemetria; nenhuma carta deve ser nerfada por essa métrica isolada.

### P3 — Tornar cobertura e flags sensíveis à exposição

- **Tipo:** lacuna de medição/design.
- **Impacto:** médio.
- **Esforço:** baixo a médio.
- **Evidência:** 30 `unused` em 30 partidas caem para 7 em 200; cobertura de keyword não mede ativabilidade; FIRE e SHADOW passam no gate apesar de compartilharem o mesmo conjunto de condições.
- **Recomendação:** exigir exposição mínima antes de `unused`/`low-impact`, reportar confiança/amostra, auditar condição ativável e eixo exclusivo por família, e manter keywords raras como decisão de design explícita.
- **Arquivos afetados:** `services/rebirth_balance.py`, `services/rebirth_cards.py`, `tools/rebirth_balance_report.py`, testes de cobertura.

## 11. Decisões que este diagnóstico não autoriza

- não autoriza nerf de EARTH;
- não autoriza buff de SHADOW;
- não autoriza espalhar SIEGE/EXECUTE/THORNS apenas para aumentar contagem;
- não autoriza alterar Fireball por WR de seleção;
- não autoriza re-tuning com base no lote de 30;
- não autoriza tratar a amostra SQLite local como produção.

O próximo passo correto é melhorar a régua e coletar evidência humana. Só depois o balance numérico volta à mesa.
