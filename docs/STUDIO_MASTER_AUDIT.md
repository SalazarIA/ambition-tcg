# Ambitionz Rebirth — Studio Master Audit

**Data local:** 2026-05-27
**Branch:** `main` (commit `9e099dd` — pós-bundle v71/v72 + zero skips)
**Escopo:** runtime Rebirth ativo, engine, API Flask, persistência, frontend, PWA/mobile, QA e roadmap.

**Status de verificação automatizada:**

| Suíte | Resultado |
|---|---|
| `.venv/bin/python -m pytest -q` | **1202 passed, 0 skipped** |
| `.venv/bin/python -m pytest -m e2e -q` | **19 passed, 0 skipped** |
| `.venv/bin/python -m pytest -m ""` (tudo) | **1221 passed, 0 skipped, 0 deselected** |
| `tests/rebirth/concurrency/` (Postgres local) | **5 passed** |
| JS — `node tests/js/test_rebirth_audio_chain_dedup.cjs` | **OK (5 asserts)** |
| Live `/health` | **`{"ok":true, "status":"healthy", "schema_version":8}`** |

---

## Veredito Executivo

Ambitionz Rebirth já tem fundação acima de protótipo: engine server-authoritative, command/event log, replay/canonical hash, persistência Postgres/SQLite de teste, produto com conta/coleção/loja/progressão/histórico, PWA e QA automatizado amplo.

O jogo está pronto para **etapa de evolução total**, desde que essa etapa seja tratada como **produto jogável em lapidação**, não como mais uma expansão de superfície.

Prioridade **não é** adicionar páginas. Prioridade é:
- Transformar a arena num loop mais claro, mensurável e escalável.
- Decisões menos confusas, mobile com ação imediata.
- Simulador alinhado ao combate real.
- Telemetria confiável.
- Segurança fechada em todos os comandos mutantes.
- Modularização gradual do frontend.

---

## Pontos Fortes

- **Separação de responsabilidades correta**: [app.py](app.py) faz HTTP; [services/rebirth_engine.py](services/rebirth_engine.py) concentra regra; [services/rebirth_dispatcher.py](services/rebirth_dispatcher.py) é entrada operacional; serializadores isolam contrato público.
- **Base determinística profissional**: command/event, snapshots, canonical hash, replay verification, parity tests.
- **Cobertura larga**: rotas, contratos frontend, segurança, persistência, card set, replay, performance, campanha, mercado, telemetria, concorrência.
- **Identidade visual da arena**: HUD forte, zonas legíveis, cartas com dono evidente, feedback de resultado coerente.
- **Produto em volta do combate existe**: conta, coleção, loadout, shop sem pagamento real, progressão, perfil, histórico, suporte, campanha.

---

## Achados Críticos (P1) — confirmados em código

### P1.1 — `/api/labs/fusion` está fora do escopo CSRF

[app.py:615–628](app.py:615) filtra mutações apenas em `request.path.startswith("/api/rebirth/")`. A rota `/api/labs/fusion` (POST mutante em [app.py:946](app.py:946)) bypassa CSRF completamente.

**Fix:** mover rota para `/api/rebirth/labs/fusion` (preferível, mantém o gate único) **ou** adicionar `/api/labs/` ao filtro.

### P1.2 — Telemetria de abandono ruidosa em auditorias

`/api/rebirth/telemetry` responde 200 com CSRF válido, mas envio em `pagehide` via `fetch(... keepalive)` aparece como `request_failed` quando o browser cancela navegação. Reduz confiança nos sinais de abandono em QA.

**Fix:** rota beacon com token assinado **ou** estratégia que QA não marque como falha (ex.: `navigator.sendBeacon` puro com endpoint dedicado que não exige CSRF).

### P1.3 — Simulador de balance ainda não exercita combate real

`services/rebirth_balance.simulate_balance` chama engine direto, não passa pelo dispatcher. Ajustes de heurística do bot não movem win-rate porque o pipeline simulado diverge do real. Balance numérico parcialmente cego — o que explica por que minhas tentativas de tunar opportunist em sessão anterior produziram resultados contra-intuitivos.

**Fix:** simulador dirigir partidas pelo `dispatch_command` real (mesmas etapas que cliente HTTP).

### P1.4 — Mobile ainda com densidade alta no cockpit

Mão e botões aparecem no primeiro viewport em 390x844, mas o topo está comprimido: nav + carteira + XP + login + HUD competem com a arena. Para mobile, primeira tela precisa respirar mais como jogo nativo.

**Fix:** colapsar nav em hambúrguer dentro da arena, esconder XP/carteira nessa rota, manter só HUD + indicador de turno + ação principal.

### P1.5 — Discrepância "100 vs 103 cartas" exposta ao jogador *(supplement)*

[services/rebirth_product.py:159](services/rebirth_product.py:159) hardcoda `{"label": "Cartas", "value": "100 no catálogo"}`. Catálogo real (`services.rebirth_cards.catalog_payload()`) tem **103 cartas**. O shell na home, no nav e em docs aparece "100" — discrepância visível.

**Fix:** ler `len(catalog_payload())` em vez de hardcode.

---

## Achados Importantes (P2)

### P2.1 — Default selection vs. "Best Play" pode divergir

`BEST PLAY` badge é renderizado em [static/js/rebirth.js:783](static/js/rebirth.js:783) na carta marcada como `recommended`, mas a seleção corrente pode estar em outra carta. Pequeno para experiente, grande para primeira sessão.

**Fix:** auto-selecionar `recommendedCard()` no novo turno **ou** copy explícita do tipo "Sua seleção · Recomendada: X".

### P2.2 — Microcopy da CTA precisa acompanhar estado

Quando a ação muda entre invocar/atacar/resolver/passar, texto auxiliar precisa mudar junto.

### P2.3 — Resultado de clash tem ruído operacional

Painel comunica bem o headline, mas cadeia `event-*`, prioridade, janela, log e detalhes competem pelo mesmo foco. Hierarquia ideal: **resultado → delta HP/guarda → causa principal → detalhes dobrados**.

### P2.4 — Documentação com drift histórico

[docs/PRODUCT_DECISION_LOG.md:9](docs/PRODUCT_DECISION_LOG.md:9) ainda fala em "one-card" duel. A arena atual tem 3 slots por lado.

### P2.5 — Frontend ativo grande demais pra próxima etapa

- [static/js/rebirth.js](static/js/rebirth.js): **3247 linhas**
- [static/css/rebirth.css](static/css/rebirth.css): **9282 linhas**

Ainda sustentável porque os contratos estão fortes, mas próxima leva de features paga juros. Modularizar por fatias: API/store, renderer de cartas, input, tactics, motion, onboarding.

### P2.6 — i18n: acentos faltando em mensagens de erro *(supplement)*

- [app.py:883](app.py:883): `"Informe um no valido da campanha."` → `"um nó válido"`
- [app.py:886](app.py:886): `"Este encontro da campanha nao existe."` → `"não existe"`
- [services/rebirth_serializers.py:125](services/rebirth_serializers.py:125): `"aguardando acao"` → `"aguardando ação"` (esse vai pra UI)

### P2.7 — Cartas problemáticas detectadas em simulação (N=200) *(supplement)*

| Card | Plays | WR | Flag |
|---|---|---|---|
| `card_006` Scorchscale Imp | 479 | **0.71** | **dominant** |
| `card_001` Cinder Lynx | 128 | 0.00 | low-impact |
| `card_002` Ashen Brawler | 159 | 0.02 | low-impact |
| `card_042` Rootwall Tender | 356 | 0.06 | low-impact |
| `card_061` Duskwisp Thief | 286 | 0.01 | low-impact, dead-hand-risk |
| `card_062` Hollowmark Stalker | 345 | 0.02 | low-impact |
| `card_084` Bola de Fogo da Arena | 0 | — | **unused, dead-hand-risk** |
| `card_086` Fortificação Rúnica | 0 | — | **unused, dead-hand-risk** |
| `card_090` Drenagem Sombria | 0 | — | **unused, dead-hand-risk** |

`earth_counter` ability: 633 plays, win_rate = **0.02**. Provavelmente trade suicida.

Aviso: estas métricas vêm do simulador atual — ver P1.3. Validar com telemetria real (`tools/rebirth_telemetry_analyzer.py`) antes de tunar.

### P2.8 — `max_chain_events = 16` ainda acima do alvo 15

Health gate em [tools/rebirth_gameplay_health.py:33](tools/rebirth_gameplay_health.py:33) aceita até 15. Simulação atual: 16. Pequena legibilidade pendente.

### P2.9 — Pacing por perfil teve regressão sutil *(supplement)*

Em N=200, `opportunist` caiu de player_win 0.40 → **0.30** (alvo mínimo 0.40). Spread global ainda OK (0.175), mas opportunist está saindo do envelope.

---

## Riscos de Produção

- Rodar testes com `python3` do sistema mascara estado real (system tem 3.9, falta `psycopg`). Gate oficial: **`.venv/bin/python`**.
- `/health` depende de schema Postgres correto; migrações automáticas no boot mitigam, mas precisam virar gate explícito.
- Guest match ainda é memória-only; autenticado reidrata, mas reconnect durável ainda não é multiplayer-grade.
- Service worker/PWA OK, mas cache agressivo de API de jogador vira bug de conta — denylist conservadora.
- Marketplace tem concorrência testada, mas monetização real exige outro nível de receipt validation, antifraude, suporte.

---

## Roadmap de Evolução Total

### Sprint 1 — Hardening de RC (alta prioridade, escopo cirúrgico)

- [ ] CSRF em `/api/labs/fusion` (mover ou ampliar filtro).
- [ ] Telemetria de abandono via `sendBeacon` com endpoint dedicado.
- [ ] Padronizar comandos de QA para `.venv/bin/python` (README + scripts).
- [ ] Corrigir docs antigas ("one-card duel" → "três slots").
- [ ] Corrigir hardcode "100 no catálogo" → `len(catalog_payload())`.
- [ ] Corrigir acentos em mensagens de erro (`app.py:883/886`, `rebirth_serializers.py:125`).
- [ ] Re-executar pytest + e2e + UI audit + produção smoke.

### Sprint 2 — Game Feel + Primeira Sessão

- [ ] Auto-selecionar carta recomendada (ou tornar divergência explícita).
- [ ] CTA primária + helper copy 100% state-driven.
- [ ] Preview de risco do clash antes do ataque.
- [ ] Reduzir metadados visíveis de chain no painel de resultado; detalhes em expander.
- [ ] Refinar mobile cockpit: nav menor em arena, ação primária sempre evidente.

### Sprint 3 — Balance Honesto

- [ ] Alinhar `simulate_balance` ao dispatcher real.
- [ ] Rodar partidas determinísticas por perfil com métricas de turno, dano, dead turns, comeback, evolução/fusão.
- [ ] Watchlist de cartas dominante / morta / habilidade sem impacto.
- [ ] Alimentar balance lab com telemetria real de partida autenticada.

### Sprint 4 — Modularização sem quebrar

- [ ] Extrair `RebirthApi` e `RebirthStore` para módulo próprio.
- [ ] Extrair render de cartas/campo/resultado sem alterar selectors públicos.
- [ ] Extrair `RebirthTactics` e `RebirthCombatMotion` com testes JS pequenos.
- [ ] Manter `tests/rebirth/test_rebirth_frontend_contract.py` como trava de contrato.

### Sprint 5 — Conteúdo e Retenção

- [ ] Campanha de 10 encontros → arcos com tutorialização de mecânicas.
- [ ] Arte bespoke pros cards mais usados.
- [ ] Missões de domínio: vencer com família, vencer por fusão, sobreviver com 1 HP, etc.
- [ ] Identidade narrativa pros bots (rivais, não apenas perfis mecânicos).

### Sprint 6 — Multiplayer/Live Ops

- [ ] Reconnect durável + payload determinístico assinável **antes** de PvP.
- [ ] Começar por async rival/ghost replay antes de realtime.
- [ ] Observabilidade: match funnel, abandono por turno, cards played, result cause.
- [ ] Live config de balance com versionamento + rollback.

---

## Go / No-Go

**Go para evolução total: SIM.**

**No-go para monetização ou campanha pública forte antes de resolver:**

1. CSRF da rota `/api/labs/fusion` (P1.1).
2. Telemetria de abandono ruidosa (P1.2).
3. Simulador de balance desalinhado ao combate real (P1.3).
4. Onboarding/mobile com densidade alta (P1.4).
5. Discrepância "100 vs 103 cartas" exposta ao jogador (P1.5).
6. Docs antigas contradizendo a identidade atual (P2.4).

---

## Evidências em Disco

- Screenshots desta sessão: capturas read-only via Safari em `/`, `/rebirth`, `/rebirth/campaign`, `/rebirth/collection`, `/rebirth/shop`.
- Telemetria simulada: `simulate_balance(matches=200)` — cards stats, ability stats, profile spread.
- API smoke: `curl` direto contra `https://ambitionzgame.com` (`/health`, `/api/rebirth/csrf`, `/api/rebirth/start` com CSRF) — todos OK.
