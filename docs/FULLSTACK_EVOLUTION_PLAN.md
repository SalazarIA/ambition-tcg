# Ambitionz Rebirth — Análise Fullstack Studio Sênior

**Data:** 2026-05-27
**HEAD:** `e8924da` (main)
**Sucessor de:** [STUDIO_MASTER_AUDIT.md](STUDIO_MASTER_AUDIT.md) — esse documento responde "para onde vamos a partir daqui".

---

## 0. Resumo executivo (página única)

Ambitionz Rebirth saiu da fase "validação de protótipo" e está no exato ponto em que um produto vira **studio product**: a fundação está madura, a UI está construída, os testes são reais, a engine é determinística. **O que mudou após o Sprint 1** é que os pontos de segurança e identidade de produto que ainda eram dúvida agora são fechados (CSRF universal, telemetria limpa, docs sincronizadas com o jogo real).

O que falta para "evolução total" **não é mais foundation**. É:

1. **Profundidade de combate**: 270 linhas dentro de uma única função (`resolve_turn`) e uma simulação que não exercita o dispatcher real indicam que a próxima curva é dividir a engine em camadas onde game designer e engenheiro consigam mexer separadamente.
2. **Profundidade de conteúdo**: 103 cartas no catálogo, **apenas 20 com arte bespoke** (`static/assets/rebirth/cards/`). A coleção sente isso. A campanha sente isso. A loja sente isso. Esse é o gargalo de retenção.
3. **Profundidade de produto**: a arena é forte; a primeira sessão não. Mobile cockpit ainda comprimido. Recomendação vs seleção podem discordar. Resultado de clash não tem hierarquia.
4. **Profundidade de operação**: gunicorn `-w 1 --threads 100` + `MATCH_STORE` em memória é configuração single-worker. Sustenta beta fechada com folga; **não sustenta um lançamento aberto** sem reescrever ownership de match state.
5. **Profundidade de balanço**: simulador deterministico OK, mas naïve. Sem telemetria real volumosa, qualquer tuning continua escolha-cega entre opções iguais no dashboard.

**Bar para "evolução total":** três marcos sequenciais (não simultâneos): **Beta-fechada hardening** (Sprint 2-3) → **Produção pública controlada** (Sprint 4-6) → **PvP / live-ops** (Sprint 7+). Marcos não são datas; são portões com critérios de saída explícitos abaixo.

---

## 1. Estado atual — métricas brutas

### 1.1 Código ativo

| Camada | LOC | Comentário |
|---|---|---|
| `services/rebirth_*` | **12 413** | Runtime ativo. 11 módulos. Maiores: `rebirth_persistence.py` 2651, `rebirth_engine.py` 1858, `rebirth_reducers.py` 1078. |
| `app.py` | **1 586** | 80 rotas HTTP. Quase virou demais — candidato a split por blueprint. |
| `static/js/rebirth*.js` | **5 631** | `rebirth.js` 3259 sozinho (62%). |
| `static/css/rebirth.css` | **9 282** | Identidade visual densa. Sustentável agora, peso real depois. |
| `templates/rebirth*.html` | **1 100** | Razoável; modularizado em includes. |
| `tests/rebirth/test_*.py` | **5 728** | **1230 testes verdes**, 0 skip, 0 fail. |

### 1.2 Código zumbi

| Item | Tamanho | Status |
|---|---|---|
| `backups/` | **14 MB** | 12 snapshots históricos do `app.py` (3500-4000 LOC cada). **Zero referência ativa.** |
| `tests/legacy_disabled/` | **256 KB** | 30 arquivos de testes do produto retirado. |
| `services/battle_engine_v2.py` | 2326 LOC | Importado só por `battle_engine_v2_adapter.py` (916 LOC). Cadeia legacy fechada. |
| `services/card_effect_resolver.py` | 774 LOC | Idem. |
| `services/match_engine_facade.py` | 363 LOC | Órfão completo (zero import ativo). |
| `services/arena_clean_state.py` | ? | Órfão. |
| `services/arena_training_actions.py` | ? | Órfão. |
| Catch-all routes legacy | — | `/api/ascension/*`, `/api/beta/*`, `/api/booster/*` retornam 410. **OK como redirect graceful.** 17 rotas retiradas (`/arena`, `/training`, `/collection`, etc.) redirecionam pra `/rebirth`. **OK.** |

**Total a deletar com confiança:** ~6 000 LOC + 14 MB de backups. Esse é o primeiro item do Sprint 2 — não por preciosismo, e sim porque cada novo dev/Claude tem que pisar nesse mato pra entender o repo.

### 1.3 Catálogo de conteúdo

| Métrica | Valor | Veredito |
|---|---|---|
| Cartas totais | **103** | OK para beta, magro para retenção. |
| Tiers | 1: 60, 2: 40, 3: 3 | Pirâmide saudável. |
| Famílias | FIRE 21, EARTH 21, SHADOW 21, WATER 20, SPELL 10, TRAP 10 | Bem distribuído. |
| Roles | 5 roles × 20 + 3 lendárias | Diversidade real. |
| **Arte bespoke** | **20 / 103** | **DÉBITO MAIOR**. 80% das cartas usam fallback. |

A arte é o que vende o jogo. 20 cartas com arte premium fica desproporcional contra 103 no catálogo — primeira impressão da coleção é "incompleta".

### 1.4 Performance — engine

Microbenchmarks locais (Python 3.9, .venv):

| Operação | p50 | p90 | p99 | max |
|---|---|---|---|---|
| `next_turn()` | 1.05 ms | 1.76 ms | 2.07 ms | 2.22 ms |
| `public_state()` | 0.63 ms | 0.66 ms | 0.73 ms | 0.73 ms |
| `start_match()` | 3.03 ms | 3.26 ms | 3.31 ms | 3.31 ms |

Engine é **excelente**. Não é o gargalo. Postgres write para persistência é o próximo lugar pra olhar quando volume subir.

### 1.5 Performance — produção

| Recurso | TTFB | Total | Tamanho |
|---|---|---|---|
| `GET /rebirth` | 1.20 s | 1.20 s | 20 KB |
| `GET /health` | 0.70 s | 0.70 s | 193 B |
| `GET /static/css/rebirth.css` | 0.39 s | 0.46 s | **233 KB** |
| `GET /static/js/rebirth.js` | 0.31 s | 0.35 s | **162 KB** |

Render Starter plan, single instance: TTFB de 1.2s no /rebirth indica cold start parcial. Bundle de 395 KB (CSS+JS combinados sem gzip) é grande mas defensável. **Sem gzip nem brotli é o quick-win.**

### 1.6 Operação

| Eixo | Estado | Risco |
|---|---|---|
| Concorrência | `gunicorn -w 1 --threads 100` | Single worker. **Vai estourar threads** com 100+ partidas simultâneas. |
| Match state | `MATCH_STORE` (in-memory) + Postgres restore | Single-worker dependent. Multi-worker = match state lost across workers. |
| Schema | v8, migração no boot | Auto-upgrade no `preDeployCommand`. **OK.** |
| Backups | nenhum visível no Render | Render gerencia, mas snapshot manual antes de migração schema-breaking é ausente. |
| Observabilidade | logs stdout via gunicorn | **Sem APM**, sem métricas estruturadas, sem alerting. |
| CSRF | `/api/rebirth/`, `/api/labs/` ambos cobertos (pós-Sprint 1) | **OK.** |
| Rate limiting | apenas em `/api/rebirth/auth/login` | Resto das rotas aberto a brute-force / scrape. |
| Secrets | `SECRET_KEY`, `REBIRTH_ADMIN_TOKEN`, DB URL — todos via env | **OK**, sem secrets commitados. |

### 1.7 Testes — saúde da suíte

```
.venv/bin/python -m pytest -q          → 1206 passed, 19 deselected
.venv/bin/python -m pytest -m e2e -q   → 19 passed, 0 skipped
.venv/bin/python -m pytest -m ""       → 1225 passed total
node tests/js/test_rebirth_audio_chain_dedup.cjs  → OK 5 asserts
```

| Tipo | Count | Comentário |
|---|---|---|
| Unit / integration | ~1180 | Cobertura larga. |
| Contract (frontend) | ~25 | Excelente — segura selectors via HTML/JS. |
| E2E (Playwright) | 19 | Cobertura crítica, mobile + desktop. |
| Concurrency (Postgres) | 5 | Race conditions em mercado. |
| Catalog parametrized | 103 × N | Catálogo é fonte de verdade testada. |

**Pontos cegos:**
- Sem testes que dirijam `simulate_balance` pelo dispatcher real (P1.3 do audit anterior).
- Sem teste de fim-a-fim do flow de fusão pela UI.
- Sem teste de PWA cache invalidation.
- Sem teste de carga (load testing). Nem existia infra pra isso.

---

## 2. Arquitetura — análise crítica

### 2.1 O que está certo e deve ser preservado

1. **Separação contrato/regra/transporte** — `services/rebirth_engine.py` é regra pura, `services/rebirth_dispatcher.py` é o ponto único de mutação, `services/rebirth_serializers.py` molda o contrato público. Esse padrão **é o ativo arquitetural mais valioso** do repo.
2. **Determinismo formal** — `canonical_state_hash` + replay verification + parity tests permitem reconstruir qualquer partida. Essa é base de PvP, esports, suporte ao cliente, anti-cheat. Não muitos jogos web pequenos têm isso.
3. **Schema-driven persistence** — `services/rebirth_schema.py` central, migrations idempotentes, auto-upgrade no boot. Render deploy é seguro.
4. **Tests-as-contract** — `test_rebirth_frontend_contract.py` é a peça que evita drift entre back e front. Já segurou várias mudanças.

### 2.2 Onde a próxima dor virá

**`services/rebirth_engine.py`** — 1858 LOC, 52 funções. As cinco maiores:

| Função | LOC | Linha | Severidade |
|---|---|---|---|
| `resolve_turn` | **270** | 1115 | 🔴 Refatoração obrigatória antes de novas mecânicas. |
| `_apply_trap_effect` | **210** | 676 | 🔴 Trap system encapsulado mal. |
| `next_turn` | 96 | 1762 | 🟡 OK por enquanto. |
| `declare_attack` | 82 | 1649 | 🟡 OK. |

`resolve_turn` faz: matching de cards → clash resolution → damage application → ability trigger → event emission → side-effects. **Tudo num só lugar.** Game designer não consegue ajustar resolução de clash sem ler 270 linhas. Engenheiro novo não consegue inserir nova mecânica sem temer regressão.

**`services/rebirth_persistence.py`** — 2651 LOC, 70 métodos. Está virando "god class". Candidato a split por responsabilidade:
- `RebirthSchemaRepo` (schema lifecycle)
- `RebirthMatchRepo` (match persistence)
- `RebirthUserRepo` (auth, sessions)
- `RebirthEconomyRepo` (wallet, market, transactions)
- `RebirthTelemetryRepo` (telemetry events)

Hoje tudo está num só. Conflito de merge garantido conforme escala.

**`static/js/rebirth.js`** — 3259 LOC. Já segura o produto. Próxima leva de features paga juros se não modularizar:
- `RebirthApi` + `RebirthStore` → módulo próprio
- Renderers (cartas, campo, resultado) → módulos
- `RebirthTactics`, `RebirthCombatMotion` → módulos com testes JS pequenos
- Frontend contract test continua sendo a trava

**`app.py`** — 1586 LOC com 80 rotas. Quando passar de ~100 rotas, divisão em Flask Blueprints vira obrigatório.

### 2.3 Single-worker — o teto invisível

`render.yaml` line 8:
```yaml
startCommand: gunicorn -w 1 --threads 100 --bind 0.0.0.0:$PORT app:app
```

`MATCH_TELEMETRY_CLOCKS` ([app.py:74](app.py:74)) e `MATCH_STORE` ([app.py:71](app.py:71)) são **dicionários Python em memória**. Funciona com 1 worker.

Crescer para `-w 2` quebra:
- Partida iniciada no worker A não aparece no worker B.
- Telemetry clocks não compartilham entre workers.
- Cache local de bot decisions inconsistente.

Solução não é trivial. Tem que escolher entre:
- **Sticky sessions** (Render permite via cookie hash) — paliativo, não resolve cold restart.
- **Match state em Redis** — sério, custa um service extra.
- **Sempre rehidrata do Postgres** — possível porque tudo já é commando/event log; só falta o read path estar otimizado.

Para "evolução total" o caminho é o terceiro: extrair `MATCH_STORE` para `services/rebirth_match_cache.py` com backend pluggável (memória, Redis, Postgres-only) e treinar o app pra rehidratar sob demanda. Já vimos isso funcionar em `restore_match_from_persistence`.

---

## 3. Game design — mecânicas e profundidade

### 3.1 Estado dos perfis de bot (pós-tuning Sprint 0/1)

Simulação N=200, `simulate_balance`:

| Perfil | Player WR | Bot WR | Janela alvo | Status |
|---|---|---|---|---|
| Defensive | 0.42 | 0.58 | 0.40-0.60 | ✅ |
| Aggressive | 0.48 | 0.52 | 0.35-0.55 | ✅ |
| Opportunist | 0.30 | 0.68 | 0.40-0.60 | ⚠️ saiu pra cima da janela |
| **Spread** | 0.18 | — | <0.30 | ✅ |

Opportunist está ligeiramente brutal — mas atenção: P1.3 do audit anterior diz **o simulador não exercita combate real**. Confiar numericamente só após telemetria real volumosa.

### 3.2 Catálogo — cartas problemáticas (mesma simulação)

**Dominant** (a corrigir):
| Card | Plays | WR |
|---|---|---|
| `card_006` Scorchscale Imp | 479 | **0.71** |

**Low-impact** (a buffar ou reformular):
| Card | Plays | WR |
|---|---|---|
| `card_001` Cinder Lynx | 128 | 0.00 |
| `card_002` Ashen Brawler | 159 | 0.02 |
| `card_042` Rootwall Tender | 356 | 0.06 |
| `card_061` Duskwisp Thief | 286 | 0.01 |
| `card_062` Hollowmark Stalker | 345 | 0.02 |

**Dead-hand** (nunca jogadas em 200 partidas):
- `card_084` Bola de Fogo da Arena
- `card_086` Fortificação Rúnica
- `card_090` Drenagem Sombria

**Ability suspeita**: `earth_counter` — 633 plays, win_rate 0.02. Provável trade suicida na escolha.

Esses números são input para Sprint 3 (balance honesto).

### 3.3 Profundidade vertical — onde o jogador "para de crescer"

A campanha tem 10 nós (`services/rebirth_campaign.py:_CAMPAIGN_NODES`). Após batê-los, o que sobra:
- Arena livre contra 3 perfis de bot (com o mesmo deck).
- Booster aleatório (3 comuns + 2 incomuns).
- Mercado entre jogadores (depende de critical mass).

**Não há**:
- Daily/weekly missions ativas com payoff visível.
- Drafting / sealed deck / arena ranqueada.
- Achievement com identidade narrativa.
- Sistema de "mestrar" cards (xp por carta).
- Replay / spectator de partida boa.

Para retenção pós-tutorial isso é o gargalo real. Não falta engine — falta **loop diário**.

### 3.4 Profundidade horizontal — variedade de partida

Hoje uma partida típica é:
1. Você invoca → bot responde.
2. Você ataca → resolve.
3. Repete ~22 turnos.
4. Alguém chega a 0 HP.

Mecânicas que existem mas têm **pouco peso percebido**:
- Fusão (Laboratório) — só é gatilhada se você tem 2 duplicatas. Acontece talvez 30% das partidas (sem telemetria real).
- Evolução de carta — depende de duplicatas.
- Trap cards — 10 no catálogo, raramente vistas (sub-jogadas pela mão do simulador, talvez por jogadores também).
- Spell instant — 10 no catálogo, similar.

**Hipótese de design**: o jogo é tactical TCG mas o jogador médio percebe como "duelo monocrático com algum tempero". Para "evolução total", **destacar fusão e traps** é o melhor ROI de game feel sem aumentar catálogo.

---

## 4. UX — primeira sessão até retenção

### 4.1 Funil teórico (ainda não medido com telemetria)

```
Landing /              → 100% (todos chegam)
↓ entrar na Arena
/rebirth (tutorial)    → ?%   (não sabemos quantos confirmam)
↓ primeira jogada
First duel completed   → ?%   (chave da retenção)
↓ segunda sessão
Voltam no dia seguinte → ?%   (zero medição)
```

**Gap crítico:** D1/D7 retention não está sendo medida. O analyzer de telemetria (`tools/rebirth_telemetry_analyzer.py`) lê por bot_profile, não por user_id × dia. Esse é o **primeiro relatório a ser construído antes de tocar em pacing**.

### 4.2 Cockpit mobile — observação concreta

Captura recente em 390×844: nav + carteira + XP + login + HUD competem com a arena. Eight elements no primeiro viewport contra a área de jogo.

Padrão mobile-game-native:
- Nav em hamburger dentro da arena.
- HP + Mana + Turno no HUD compacto.
- Mão + 3 slots ocupam ≥60% da tela.
- Login/perfil em modal opt-in.

Custo: **~3 dias de CSS** + 1 dia de teste E2E em viewport mobile. Alto ROI.

### 4.3 Resultado de clash — hierarquia

Hoje no painel direito vejo:
- "AGUARDANDO" / status corrente
- "Monte seu campo." headline
- Sub-headline tática
- PRIORIDADE: JOGADOR
- CADEIA EVENT-000001
- JANELA FECHADA
- LINHA DEFENSIVA: "tende a absorver primeiro e punir ataques fracos"
- LINHA DE SETUP: "Duelista: 4 ataque / 3 guarda, tempo 14"
- CAMPO EQUILIBRADO: "HP, mão e baralho estão próximos"
- MÃO INIMIGA: "5 cartas ocultas"
- Histórico
- Ações secundárias

**Doze sinais simultâneos.** Para player experiente isso é riqueza; pra jogador novo é ruído. Necessário hierarquizar:

```
HEADLINE (resultado, 1 linha grande)
↓
DELTA (HP/guarda mudou em quanto)
↓
CAUSA (qual ability/efeito disparou)
↓
DETAILS (em expander/tooltip — chain, prioridade, janela)
```

### 4.4 Best Play vs seleção

Já citado no audit anterior. `static/js/rebirth.js:783` renderiza badge "BEST PLAY". `selectedInstanceId` é independente. Sprint 2.

---

## 5. Operação, observabilidade, segurança

### 5.1 O que cobre hoje

- ✅ HTTPS via Render
- ✅ CSRF universal (pós-Sprint 1)
- ✅ Rate limit em login
- ✅ Schema migrations idempotentes
- ✅ Sessions HttpOnly + SameSite
- ✅ X-Content-Type-Options, X-Frame-Options
- ✅ Service worker controlado (denylist conservadora)
- ✅ Secrets via env

### 5.2 O que está faltando

- ❌ **Rate limit em endpoints de jogo**. `/api/rebirth/start` aberto = bot scraper pode minerar match seeds.
- ❌ **Audit log de admin**. Apenas `admin_audit_log` table existe; views/relatórios não.
- ❌ **Backup automatizado de Postgres antes de migration**. Hoje rola pre-deploy migration sem rollback plan.
- ❌ **Alerting**. Render notifica deploy fail; saúde do schema, error rate, queue depth — ninguém vigia.
- ❌ **APM / structured logging**. Logs stdout via gunicorn — não dá pra correlacionar request_id, user_id, match_id.
- ❌ **CSP (Content Security Policy)** — não vi configurado. Sem CSP, qualquer XSS via card name vira problema (improvável mas barato de fechar).
- ❌ **Rate limit em telemetria beacon**. Endpoint pode ser inundado.
- ❌ **DB pool size config explícito** para `psycopg`.

---

## 6. A Evolução Total — três marcos sequenciais

### 🎯 Marco 1 — Beta Fechada Hardening (Sprints 2-3, ~4-6 semanas)

**Objetivo:** entregar uma versão que sustente **100-500 usuários beta-key** durante 30 dias sem degradar.

**Critérios de saída:**
- D1 retention medida (mesmo que ruim).
- 0 crashes não-tratados em produção em 1 semana.
- `simulate_balance` exercita o dispatcher real.
- Mobile cockpit limpo (3 elementos competindo no primeiro viewport, não 8).
- 50% das cartas do catálogo com arte bespoke (52/103).
- Backup automatizado pre-migration.
- Rate limit em todas as rotas mutantes.

**Sprints:**

**Sprint 2 — Game Feel & Onboarding** (2 semanas)
- Auto-selecionar carta recomendada na primeira sessão (ou tornar divergência explícita).
- CTA primária state-driven 100% (microcopy muda por estado).
- Hierarquizar painel de resultado (headline → delta → causa → details).
- Mobile cockpit: nav em hamburger, HP/mana/turno compactos, mão + 3 slots = 60% da tela.
- Preview de risco do clash antes do ataque (já tem `RebirthTactics.selectedAttackRisk`).

**Sprint 3 — Balance Honesto** (2 semanas)
- Alinhar `simulate_balance` ao dispatcher real (P1.3 do audit).
- Tunar `card_006` Scorchscale Imp (dominante).
- Buffar/refazer 6 cartas low-impact + 3 dead-hand (`card_001`, `card_002`, `card_042`, `card_061`, `card_062`, `card_011`, `card_084`, `card_086`, `card_090`).
- Investigar `earth_counter` ability (WR 0.02 em 633 plays).
- Watchlist automática em CI (PR que tira carta da janela alerta).

### 🎯 Marco 2 — Produção Pública Controlada (Sprints 4-6, ~6-8 semanas)

**Objetivo:** abrir para público geral com infra que aguenta 1k-5k DAU.

**Critérios de saída:**
- D7 retention medida.
- Multi-worker funcional (`-w 2+`) sem perda de match state.
- 80% do catálogo com arte bespoke.
- Loop diário ativo (daily quests visíveis, recompensa visível).
- Alerting em error rate > 1% / 5min.
- APM funcional (request_id, user_id, match_id correlacionados).

**Sprints:**

**Sprint 4 — Engine Modular & Multi-Worker** (3 semanas)
- Refatorar `resolve_turn` (270 → ≤80 LOC por função).
- Refatorar `_apply_trap_effect` (210 → ≤80 LOC).
- Extrair `MATCH_STORE` para backend pluggável; usar Redis em prod.
- Migrar para `-w 2` em Render starter+ ou Standard.
- Modularizar `static/js/rebirth.js` em RebirthApi/RebirthStore/Renderers (mantendo frontend contract test como trava).
- Deletar zombie code: `battle_engine_v2*`, `card_effect_resolver`, `arena_*` órfãos, `backups/`, `tests/legacy_disabled/`.

**Sprint 5 — Conteúdo & Live-loop** (2-3 semanas)
- Daily quests no fluxo (api + UI + claim ledger).
- Sistema de mastery por carta (XP, tier de fluência).
- Achievement narrativos (não apenas count-based).
- Boss da campanha ganha narrativa (cutscene curta antes do duelo + frase de derrota).
- Spectator/replay público de partidas boas (já temos `replay_match`).

**Sprint 6 — Operação & Observabilidade** (1-2 semanas)
- Structured logging (request_id propagado).
- Sentry ou similar (free tier OK).
- Backup automatizado Postgres pre-deploy.
- Rate limit em todas rotas mutantes.
- CSP, security headers extras.
- Status page pública (`/status`).
- Load test (k6 / Locust) — definir SLO de p95 < 500ms.

### 🎯 Marco 3 — PvP & Live-Ops (Sprints 7+, contínuo)

**Objetivo:** transformar Rebirth em produto live com retenção semanal.

**Critérios de saída — opcionais, escolha-se um por trimestre:**
- Async PvP funcional (ghost replay).
- Ranqueada com seasons.
- Eventos temporários com balanço próprio.
- Spectator com chat e betting (free, gameplay-only).
- Marketplace player-driven com taxas.

**Pré-requisitos técnicos (sem isso não começa):**
- Reconnect durável (refresh não perde partida).
- Payload determinístico assinável (anti-cheat).
- `canonical_state_hash` já garante metade disso.
- Liveness check entre clientes.
- Matchmaking (mesmo que naïve por ELO).
- Live config separada do código (balance hot-swap).

---

## 7. Mapa de Riscos

| Risco | Probabilidade | Impacto | Mitigação atual | Gap |
|---|---|---|---|---|
| Single-worker estoura em pico | Média | Alto | `-w 1 --threads 100` | Sem fallback. Sprint 4. |
| Catálogo com 80% sem arte derruba retenção | Alta | Alto | Coleção curada (cad0c3e) esconde gap | Não resolve, só camufla. Sprint 5. |
| Balance simulator desalinhado leva a tuning ruim | Alta | Médio | Telemetria via analyzer | Sem volume real ainda. Sprint 3. |
| Postgres migration falha em prod | Baixa | Alto | Auto-migration no boot | Sem backup automatizado pre-deploy. Sprint 6. |
| Bot scraper minera match seeds | Média | Médio | CSRF | Sem rate limit no /api/rebirth/start. Sprint 6. |
| Engine refactor introduz regressão | Média | Alto | 1230 testes | Cobertura larga mas não 100%. Trabalhar com feature flag. |
| Crescimento de `rebirth.js` paga juros | Alta | Médio | Frontend contract test | Sem modularização. Sprint 4. |
| Zombie code confunde devs novos | Alta | Médio | — | Limpar. Sprint 4. |

---

## 8. Trajetória recomendada — em uma página

### Próximos 30 dias

1. **Sprint 2 inicia**: Game Feel + Onboarding + Mobile cockpit.
2. Em paralelo: scripting de daily quests no backend (sem UI ainda).
3. Em paralelo: pipeline de arte para destravar 30 cartas adicionais.
4. **Critério de saída**: build com D1 retention medida + cockpit mobile aceitável + auto-select de carta recomendada em primeira sessão.

### 60-90 dias

5. Sprint 3 (balance honesto) + Sprint 4 (engine modular + multi-worker).
6. Migração para Render Standard (ou plano superior) com Redis.
7. Limpeza completa do zombie code.
8. **Critério de saída**: build com `-w 2+` rodando, 50% catálogo com arte, dispatcher-aligned simulator.

### 90-180 dias

9. Sprint 5 (conteúdo + live loop) + Sprint 6 (ops + observability).
10. Abertura pública controlada com beta keys.
11. **Critério de saída**: D7 retention medida, alerting funcional, 1k DAU sustentável.

### 180+ dias

12. Marco 3 (PvP / Live-Ops).

---

## 9. Apêndice — checklist de prontidão por marco

### Beta Fechada (Marco 1)
- [ ] D1 retention dashboard
- [ ] Auto-select recommended card
- [ ] Mobile cockpit refinado
- [ ] `simulate_balance` via dispatcher
- [ ] 50% arte bespoke (52/103)
- [ ] Backup automatizado pre-deploy
- [ ] Rate limit em rotas mutantes
- [ ] Tunar `card_006` + 6 low-impact + 3 dead-hand

### Produção Pública (Marco 2)
- [ ] D7 retention dashboard
- [ ] Multi-worker (`-w 2+`) com Redis match store
- [ ] 80% arte bespoke
- [ ] Daily quests no fluxo
- [ ] APM + structured logging
- [ ] CSP + security headers extras
- [ ] Status page pública
- [ ] Zombie code deletado (battle_engine_v2 + arena_* órfãos + backups/)

### PvP / Live-Ops (Marco 3)
- [ ] Reconnect durável
- [ ] Async PvP (ghost replay)
- [ ] Ranqueada com seasons
- [ ] Live config separada de código
- [ ] Anti-cheat via canonical state hash

---

**Conclusão.** A foundation está madura, o produto está construído, os testes são reais. Para "evolução total" o caminho não é mais adicionar páginas — é **aprofundar três eixos: experiência de primeira sessão, profundidade de combate (mecânica + arte) e infra para múltiplos workers**. Os 3 marcos acima dão pra fazer em 6 meses com disciplina, ou em 12 com folga. Não é foundation faltando. É produção rotineira de profundidade.
