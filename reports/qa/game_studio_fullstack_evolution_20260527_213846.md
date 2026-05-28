# Ambitionz Rebirth - Fullstack Game Studio Audit

- Data local: 2026-05-27 21:38 BRT
- Escopo: runtime Rebirth ativo, engine, API Flask, persistencia, frontend, PWA/mobile, QA e roadmap de evolucao
- Status de verificacao: `.venv/bin/python -m pytest -q` -> 1203 passed, 19 deselected, 3 warnings
- Checks adicionais: `py_compile` dos modulos centrais e `node --check` de `rebirth.js`, `service-worker.js`, `pwa.js`, `rebirth_product.js` -> OK

## Veredito Executivo

Ambitionz Rebirth ja tem uma fundacao acima de prototipo: engine server-authoritative, command/event log, replay/canonical hash, persistencia Postgres/SQLite de teste, produto com conta/colecao/loja/progressao/historico, PWA e QA automatizado amplo. O jogo esta pronto para uma etapa de evolucao total, desde que essa etapa seja tratada como **produto jogavel em lapidacao**, nao como mais uma expansao de superficie.

A prioridade nao e adicionar mais paginas. A prioridade e transformar a arena em um loop mais claro, mais mensuravel e mais escalavel: decisoes menos confusas, mobile com acao imediata, simulador alinhado ao combate real, telemetria confiavel, seguranca fechada em todos os comandos mutantes e modularizacao gradual do frontend.

## Evidencia Tecnica

- Suite Rebirth: 1203 testes passando no `.venv`.
- Suite Postgres concorrencia: 5/5 passando no `.venv`.
- Falha fora do `.venv`: `python3 -m pytest -q` do sistema erra 5 testes por `ModuleNotFoundError: No module named 'psycopg'`; nao e falha de produto, e gate rodado no interpretador errado.
- Auditoria visual local/online recente: 12 findings em cada, repetindo `object-fit: cover` na arena e request failed em `/api/rebirth/telemetry`.
- Master game audit recente: 30 screenshots, 26 eventos, 0 severe events, 0 findings finais.
- Duel mechanics audit recente: 15 passos, 0 severe events; confirmou fluxo summon -> bot responde -> ataque -> resultado.

## Pontos Fortes

- A separacao de responsabilidades esta correta: `app.py` faz HTTP; `services/rebirth_engine.py` concentra regra; `services/rebirth_dispatcher.py` vira entrada operacional; serializadores isolam contrato publico.
- A base deterministica e profissional: command/event, snapshots, canonical hash, replay verification e parity tests criam uma trilha de debug que muitos jogos web pequenos nao tem.
- A cobertura e larga: rotas, contratos frontend, seguranca, persistencia, card set, replay, performance, campanha, mercado, telemetria e concorrencia.
- O visual da arena ja possui uma identidade clara: HUD forte, zonas legiveis, cartas com dono evidente, feedback de resultado e tom audiovisual consistente.
- O produto em volta do combate existe: conta, colecao, loadout, shop sem pagamento real, progresso, perfil, historico, suporte e campanha.

## Achados Criticos

### P1 - `/api/labs/fusion` esta fora do escopo CSRF

`protect_rebirth_mutations()` protege apenas paths que comecam com `/api/rebirth/`. A fusao em campo e mutante, mas vive em `/api/labs/fusion`. O frontend envia `X-Rebirth-CSRF`, porem o backend nao exige para essa rota. Isso deve ser fechado antes de qualquer campanha maior ou modo autenticado com valor economico.

### P1 - Telemetria de abandono esta ruidosa nos audits

A rota `/api/rebirth/telemetry` existe e responde 200 com CSRF valido. O finding vem do envio no `pagehide` usando `fetch(... keepalive)`, que tende a ser cancelado por navegacao/fechamento do browser em QA. Isso reduz confianca nos sinais de abandono. A solucao mais limpa e uma rota de beacon com token seguro ou uma estrategia que o auditor nao marque como network failure.

### P1 - Simulador de balance ainda nao mede todo o combate real

Relatorios anteriores apontam que parte da heuristica do bot e ajustes de balance nao movem win rate porque o simulador nao exercita todos os caminhos reais de ataque/dispatcher. Enquanto `simulate_balance` nao dirigir partidas pelo pipeline real, balance numerico continua parcialmente cego.

### P1 - Mobile ainda tem densidade de cockpit alta

A captura 390x844 ja mostra mao e botoes no primeiro viewport, o que e bom. Mas o topo esta muito comprimido: nav, carteira, XP, login e HUD competem com a arena. Para jogo mobile, a primeira tela precisa respirar mais como jogo nativo e menos como site responsivo.

## Achados Importantes

### P2 - Default selection e recomendacao podem discordar

Relatorio de playtest aponta `Best Play` em uma carta enquanto outra pode estar selecionada. Isso e pequeno para jogador experiente, mas grande para primeira sessao. A arena deve selecionar automaticamente a recomendada, ou separar explicitamente "selecionada" de "melhor jogada".

### P2 - Microcopy da CTA precisa acompanhar o estado real

Quando a acao muda entre invocar, atacar, resolver e passar turno, o texto auxiliar precisa mudar junto. Isso e uma das formas mais baratas de aumentar entendimento sem mexer em regra.

### P2 - Resultado de clash ainda tem ruido operacional

O painel de resultado comunica bem o headline, mas `cadeia event-*`, prioridade, janela, log e detalhes competem pelo mesmo foco. Para jogador, a hierarquia ideal e: resultado, delta de HP/guarda, causa principal, detalhes dobrados.

### P2 - Documentacao de produto tem drift historico

`README.md` e `REBIRTH_RELEASE_STATUS.md` descrevem a arena atual de tres slots. `PRODUCT_DECISION_LOG.md` e `REBIRTH_GAMEPLAY_CORE.md` ainda falam em "one card / one decision / one clash". Isso precisa ser resolvido para a equipe nao construir em cima de uma fantasia antiga.

### P2 - Frontend ativo esta grande demais para a proxima etapa

`static/js/rebirth.js` tem 3247 linhas e `static/css/rebirth.css` tem 9282. Ainda e sustentavel porque os contratos estao fortes, mas a proxima leva de features vai pagar juros se nao modularizar por fatias: API/store, renderer de cartas, input, tactics, motion, onboarding.

## Riscos De Producao

- Rodar testes com `python3` do sistema mascara o estado real; gate oficial deve usar `.venv/bin/python` ou ambiente CI fechado.
- `/health` depende do schema Postgres correto; migracoes automaticas no boot mitigam Render, mas precisam seguir como gate explicito.
- Guest match ainda e memoria-only; autenticado reidrata runtime state, mas reconnect duravel ainda nao e multiplayer-grade.
- Service worker/PWA esta bom, mas qualquer cache agressivo de API de jogador pode virar bug de conta; a denylist deve continuar conservadora.
- Marketplace/economia ja tem concorrencia testada, mas qualquer monetizacao real exige outro nivel de receipt validation, antifraude e suporte.

## Roadmap De Evolucao Total

### Sprint 1 - Hardening de RC

1. Exigir CSRF em `/api/labs/fusion` ou mover a rota para `/api/rebirth/labs/fusion`.
2. Reprojetar telemetria de abandono para nao gerar requestfailed em QA.
3. Padronizar comandos de QA para `.venv/bin/python`.
4. Atualizar docs antigas que ainda descrevem "one-card duel".
5. Reexecutar: pytest completo, e2e, UI audit local/online, production smoke.

### Sprint 2 - Game Feel e Primeira Sessao

1. Auto-selecionar carta recomendada ou explicar a divergencia.
2. Tornar CTA primaria e helper copy 100% state-driven.
3. Adicionar preview de risco do clash antes do ataque.
4. Reduzir metadados visiveis de chain no resultado e deixar detalhes sob expansao.
5. Refinar mobile cockpit: nav menor em arena, acao primaria sempre evidente.

### Sprint 3 - Balance Honesto

1. Alinhar `simulate_balance` ao dispatcher real.
2. Rodar partidas deterministicas por bot profile com metricas de turno, dano, dead turns, comeback, uso de evolucao/fusao.
3. Criar thresholds de watchlist para carta dominante, carta morta, habilidade sem impacto.
4. Alimentar balance lab com telemetria real de partida autenticada.

### Sprint 4 - Modularizacao Sem Quebrar

1. Extrair `RebirthApi` e `RebirthStore` para modulo proprio.
2. Extrair render de cartas/campo/resultado sem alterar selectors publicos.
3. Extrair `RebirthTactics` e `RebirthCombatMotion` com testes JS pequenos.
4. Manter `tests/rebirth/test_rebirth_frontend_contract.py` como trava de contrato.

### Sprint 5 - Conteudo e Retencao

1. Evoluir campanha de 10 encontros para arcos com tutorializacao de mecanicas.
2. Expandir arte bespoke dos cards mais usados.
3. Criar missoes de dominio: vencer com familia, vencer por fusao, sobreviver com 1 HP, etc.
4. Dar identidade aos bots como rivais, nao apenas perfis mecanicos.

### Sprint 6 - Multiplayer/Live Ops

1. So iniciar PvP depois de reconnect duravel e payload deterministico assinavel.
2. Comecar por async rival/ghost replay antes de realtime.
3. Adicionar observabilidade: match funnel, abandono por turno, cards played, result cause.
4. Separar live config de balance com versionamento e rollback.

## Go / No-Go

Go para evolucao total: sim.

No-go para monetizacao ou campanha publica forte antes de resolver:

- CSRF da rota labs/fusion.
- Telemetria de abandono ruidosa.
- Simulador de balance desalinhado ao combate real.
- Onboarding/mobile com densidade alta.
- Docs antigas contradizendo a identidade atual.

