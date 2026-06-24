# Ambitionz Rebirth — Revisão Completa do Game (sessão autônoma)

**Data:** 2026-06-24
**Autor:** Claude (Opus 4.8), sessão autônoma autorizada pelo dono
**Branch:** `chore/game-review-pass` (sem deploy — para revisão e merge pelo dono)

> Pedido do dono: revisar a arquitetura "em todas as linhas" e melhorar; caçar
> brechas e coisas não feitas e corrigir; jogar e inspecionar em busca de
> melhorias de mecânica, lógica, visual e atratividade; trabalhar até o limite
> de uso e deixar tudo registrado neste relatório.

---

## 0. Decisões autônomas registradas

1. **Sem deploy não supervisionado.** Tudo nesta sessão vai para a branch
   `chore/game-review-pass` + PR. O Render só faz deploy de `main`, então nada
   cai em produção sem a revisão do dono.
2. **Sem re-tuning de balance especulativo.** A memória do projeto é explícita:
   balance é decidido por **telemetria de produção**, não por simulação de lab
   (ver `ambitionz_v107_balance_baseline`). Ajustes de número de carta/keyword
   ficam como *recomendação* na §6, nunca commit às cegas.
3. **Suíte rápida verde após cada mudança** (regra do CLAUDE.md). Baseline e
   estado final desta sessão: **1448 passed, 5 skipped, 23 deselected**.
4. **Mudança aplicada é só a de altíssima confiança e verificável** — remoção de
   tooling morto que crasha no import (§5). Não toquei no código de regras do
   jogo: ele está saudável e mexer às cegas, sem o dono, seria irresponsável.

---

## 1. Sumário executivo

**O game está maduro, estável e visualmente sólido — não é protótipo.** Núcleo
de regras determinístico (event-sourcing, hash canônico, modelo de prioridade de
efeitos em camadas, validação de paridade e invariantes), ~20k linhas de serviços
`rebirth_*`, 70 arquivos de teste, 1448 testes verdes, e quase zero dívida textual
(TODO/FIXME) no produto.

Inspeção de runtime (Playwright, viewport 1440×900 e 1900×980):
- **Todas as superfícies** (landing, arena, loja, coleção, deck builder, campanha,
  perfil, recompensas) carregam **sem erro de console, sem pageerror e sem scroll
  horizontal**.
- **Partida de 40 turnos** dirigida via UI: **zero erros** de console/runtime — a
  engine aguenta interação intensa sem quebrar.
- **In-game com tabuleiro cheio**: layout firme, cartas grandes e legíveis,
  avatares discretos, comandos organizados (resultado do redesign da sessão
  anterior, v115/v116).

Conclusão honesta: **não há "arquitetura ruim" para refazer nem bug aberto óbvio
para corrigir.** O retorno marginal está em (a) **higiene de tooling** (feito,
§5), (b) **polimento de atratividade/UX** (recomendações verificáveis, §6) e
(c) **balance por telemetria** (não-lab, §6). Foi nisso que a sessão focou.

---

## 2. Revisão de arquitetura

### 2.1 Pontos fortes (preservar)
- **Pipeline de comando determinístico** (`services/rebirth_dispatcher.py`):
  `COMMAND → VALIDATE → BUILD_EVENT_STACK → RESOLVE_EFFECTS → REDUCER_PHASE →
  EMIT_EVENTS → PERSIST_SNAPSHOT`, com prioridade de efeitos em 6 camadas
  (Replacement → Interrupts/Traps → Reactive → Active → Passive →
  Delayed/Expiration). Entrada única e autoritativa (`dispatch_command`).
- **Determinismo verificável:** `finalize_canonical_state_hash`,
  `DeterministicParityRunner` e `validate_rebirth_state` (invariantes) plugáveis
  por flag no próprio dispatch. Raro e muito valioso num TCG.
- **Separação de responsabilidades clara:** engine (orquestra), reducers (mutam),
  effects (keywords), state/schema (modelo), serializers (payload), persistence
  (DB + mercado), bot (IA), balance/live_balance.
- **Contrato de erro de persistência** mapeado
  (`RebirthPersistenceError(code="database_write_failed")`) — parte do contrato
  de teste; preservar.

### 2.2 Observações (recomendações, não urgências)
- **Módulos grandes:** `rebirth_persistence.py` (3214 linhas) e
  `rebirth_engine.py` (2555) são os maiores. Não estão ruins; se continuarem
  crescendo, dividir por domínio (persistence → `_market`/`_profile`/`_match_store`).
  Refator grande = risco alto sem ganho imediato → fazer só sob demanda.
- **Imports tardios (lazy) dentro de funções** quebram ciclos
  (engine ↔ effects ↔ dispatcher). Funciona, mas sinaliza acoplamento circular.
  Documentar o grafo de dependências evita regressões futuras.
- **21 `except Exception`** em `services/`+`app.py` — dentro do razoável; a maioria
  reembrulha em erro de domínio. Auditado por amostragem, sem swallow silencioso
  preocupante.

---

## 3. Brechas e "coisas não feitas" encontradas

### 3.1 Tooling órfão da arquitetura antiga (PRINCIPAL — CORRIGIDO em §5)
A migração da arena antiga (`battle_engine_v2`, `arena_training_actions`, `models`,
`arena_payload`, sockets) para `rebirth_*` deixou **~27% do diretório `tools/`
órfão**: **34 scripts** importavam módulos já removidos e **crashavam no import**.
Confirmado que **nenhum** deles é referenciado por CI, deploy (`render.yaml`),
código vivo (`app.py`/`services/`) ou testes — a CI usa só os tools `rebirth_*`/
`ops/*`. Efeito colateral perigoso: auditorias que "passavam" por engano ou
quebravam, mascarando regressões.

### 3.2 Higiene de código (boa)
- Apenas **3** marcadores TODO/FIXME no produto — todos **falsos positivos**
  ("TODO o excedente" = português). Dívida textual ~zero.
- **5 testes skipped** = apenas gating de Postgres local (testcontainers); **não**
  são features inacabadas.

### 3.3 Resíduo de arquitetura antiga em assets/rotas (sem impacto ao jogador)
`tools/playability_audit.py` aponta assets/endpoints inexistentes
(`arena_clean_v48.*`, `arena_sound.js`, `/api/retention/event`, etc.). Confirmado:
**não são referenciados em template vivo** — é a própria auditoria que está
desatualizada (parte do tooling órfão da §3.1).

---

## 4. Achados de play-test (mecânica · lógica · visual · atratividade)

Método: Playwright sem `force`, leitura de screenshots (padrão "olhos-de-jogador"
do projeto), 1440×900 e 1900×980, service worker bloqueado.

### 4.1 Estabilidade (forte)
- 8 superfícies: **0 erros de console, 0 pageerror, 0 overflow horizontal**.
- Partida de 40 turnos dirigida por UI (mulligan → invocar → atacar → encerrar):
  **0 erros**. Tabuleiro lota corretamente (3+3), sem sobreposição de fileiras.

### 4.2 Tela de fim de partida (a queixa original do dono) — JÁ RESOLVIDA
A 1ª screenshot do dono (painel "VITÓRIA" estreito quebrando linha + dois botões
"ENCERRADO") era **anterior** ao redesign v115/v116. Estado atual no desktop:
- O `.rb-result-panel` (painel estreito que sobrepunha o tabuleiro) **fica oculto
  no desktop**; a cerimônia de fim é o **overlay premium** `#rebirth-finale-overlay`
  (cortina/scrim escurece o board + painel central com resumo e 2 botões "Jogar de
  novo / Continuar"). Confirmado injetando o estado de vitória e capturando.
- Os "dois ENCERRADO" sumiram (comandos reorganizados na sessão anterior).
→ **Nada a corrigir aqui agora.** Observações menores de polish em §6.

### 4.3 Oportunidades de atratividade/visual (recomendações — §6)
Tudo funcional, mas as telas-vitrine são **escuras e esparsas** (muito espaço
vazio), o que reduz o "uau" para um jogador novo:
- **Coleção (visitante):** mostra texto/estatística, **não uma grade de artes de
  carta**. Numa TCG, ver as cartas como arte é o principal gancho emocional.
- **Loja:** o booster é um único verso de carta estático; falta encenação (leque
  de pacotes, brilho, animação de abertura como isca).
- **Campanha:** nós em lista vertical; um "mapa de jornada" visual engaja mais.
- **Perfil:** mostra um emblema/escudo, **não um avatar de foto de perfil** — é
  exatamente onde mora a feature de troca de foto que o dono pediu (o círculo
  clicável já existe na arena desde v116; falta a UI de seleção/upload + storage).
- **Overlay de vitória:** os rótulos do resumo (Turnos/Seu HP/HP do bot) usam
  `--fs-3xs` + `--rb-muted` (pouco legíveis); e o título "Vitória" cai para
  opacity 0.25 ao assentar (decisão de design — "o painel vira dono da cena").
  Deixar o número com rótulo um pouco mais legível aumentaria a clareza do prêmio.

---

## 5. Correções aplicadas nesta sessão

### 5.1 Remoção de 33 dev-tools mortos (arquitetura antiga)
Removidos os scripts que importavam módulos já deletados (`models`,
`arena_training_actions`, `battle_engine_v2`, `arena_payload`, `sockets`) e por
isso **crashavam no import** — zero perda funcional. Mantido
`tools/qa/card_art_manifest_check.py` (tem import guardado por `try/except`, pode
ainda ter uso). Lista removida:

```
tools/arena_breakage_scan.py, arena_card_art_layout_audit.py,
arena_card_stats_audit.py, arena_contract_audit.py, arena_events_audit.py,
arena_payload_audit.py, arena_real_match_audit.py, audit_database.py,
balance_snapshot.py, card_visual_unification_audit.py, deck_inventory_audit.py,
engine_contract_audit.py, inventory_migration_audit.py, match_telemetry_report.py,
preflight.py, start_training_action_audit.py,
tools/qa/{balance_watchlist, battle_balance_sim, build_audit_pdf,
qa_arena_matrix_flow, qa_arena_systems_audit, qa_backend_flow, qa_battle_engine_v2,
qa_battle_gauntlet, qa_be2_adapter, qa_be2_website_agent, qa_browser_flow,
qa_browser_full_match_flow, qa_deck_inventory_flow, qa_economy_flow,
qa_pvp_socket_flow, qa_socket_flow, qa_training_stress}.py
```

**Verificação:** CI (`.github/workflows/rebirth-closed-beta-qa.yml`) usa só tools
`rebirth_*`/`ops/*` — todos intactos e com parse OK. Suíte rápida **verde
(1448 passed)** após a remoção. Nada vivo referencia os removidos (só este
relatório e release notes históricas).

### 5.2 Este relatório
`docs/GAME_REVIEW_2026-06-24.md`.

> Nenhuma mudança no código de regras/serviços do jogo foi feita: ele está
> saudável e mexer às cegas, sem o dono presente e com deploy automático de
> `main`, seria irresponsável. As ideias de produto vão como backlog (§6).

---

## 6. Backlog priorizado (recomendações para o dono decidir)

### P1 — Atratividade do jogador novo (maior ROI percebido)
1. **Grade de artes na Coleção** (logada e, em versão "teaser", para visitante):
   mostrar as cartas como arte, não só números. É o gancho nº 1 de uma TCG.
2. **Encenação de abertura de booster** na Loja: leque de pacotes, brilho de
   raridade, animação de revelação carta a carta. Hoje é estático.
3. **Feature de foto de perfil** (o dono pediu): UI de seleção (avatares padrão +
   upload/import), persistência por usuário, e exibir o avatar no círculo da arena
   (já clicável) e no Perfil. *Requer decisão de produto sobre storage/upload.*

### P2 — Polish de momento
4. **Overlay de vitória:** rótulos do resumo mais legíveis; considerar manter o
   título "Vitória" um pouco mais presente (opacity ~0.4 em vez de 0.25).
5. **Mapa de campanha** visual (nós conectados) no lugar da lista vertical.
6. **Telas-vitrine menos vazias** (landing/loja/perfil): preencher o espaço morto
   com arte/cards em destaque mantendo a identidade dark-fantasy.

### P3 — Saúde técnica (sem urgência)
7. **Concluir a limpeza de tooling:** revisar/atualizar `playability_audit.py` e os
   demais auditores que ainda assumem a arena antiga; ou reescrevê-los sobre
   `rebirth_*`. (33 já removidos nesta sessão.)
8. **Documentar o grafo de dependências** dos `rebirth_*` para justificar os
   imports lazy e prevenir ciclos novos.
9. **Dividir `rebirth_persistence.py`/`rebirth_engine.py`** por domínio se
   continuarem crescendo (não antes — risco > ganho hoje).

### P4 — Balance (SOMENTE via telemetria de produção)
10. Não re-tunar no lab. Acompanhar winrate por arquétipo na telemetria; o baseline
    saudável documentado é casual ~53%. Mudanças de número entram só com sinal de
    produção (ver memória `ambitionz_meta_recenter_k3` / `ambitionz_v107_balance_baseline`).

---

## 7. Como validar / próximos passos para o dono
- Revisar este PR (branch `chore/game-review-pass`): contém só este relatório + a
  remoção de tooling morto. **Merge é seguro** (não altera o jogo; CI e suíte verdes).
- Escolher itens do §6 para a próxima rodada. O de maior impacto percebido e que
  você já sinalizou é a **foto de perfil + grade de coleção**.
- Servidor de QA local: `PORT=8123` + Playwright (ver memórias
  `rebirth_visual_qa_playwright` e `arena_desktop_layout_cascade`).
