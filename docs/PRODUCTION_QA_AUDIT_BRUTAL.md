# Ambitionz Rebirth — Auditoria Brutal de Produção

**Data:** 2026-05-28
**Ambiente:** `https://ambitionzgame.com` (produção real, deploy `ff5b1ca`/`e8924da`)
**Metodologia:** 10 batalhas completas dirigidas via API de produção (guest), edge-probes deliberados, screenshots read-only de todas as rotas, análise de código cruzada com comportamento observado.
**Tom:** QA sênior + game designer + product lead + engenheiro de engine. Sem suavizar.

> **Nota de conformidade:** não criei conta (regra de segurança). As batalhas rodaram como **convidado real** pela mesma API HTTP que o browser usa — comportamento de engine, pacing e transições são produção genuína. Fluxos só-autenticados (save de coleção, progressão persistente, compra) foram avaliados por código + contrato + screenshots.

---

## 🔴 MANCHETE — o bug que para o lançamento

**TODO match de convidado compartilha o MESMO `match_id`: `rebirth-963745ae6ffc`.**

### Reprodução (100% determinística)
```bash
# Sessão A
curl -s -c jarA https://ambitionzgame.com/api/rebirth/csrf
curl -s -b jarA -X POST .../api/rebirth/start -d '{"tutorial":false}'
# → match_id: rebirth-963745ae6ffc, bot: defensive

# Sessão B (cookie totalmente separado)
curl -s -c jarB https://ambitionzgame.com/api/rebirth/csrf
curl -s -b jarB -X POST .../api/rebirth/start -d '{"tutorial":false}'
# → match_id: rebirth-963745ae6ffc, bot: defensive   ← IDÊNTICO
```

### Causa raiz
- [services/rebirth_state.py:33](services/rebirth_state.py:33) — `_match_id(None)` → `sha256("rebirth-default-seed")[:12]` = constante.
- [services/rebirth_state.py:171](services/rebirth_state.py:171) — `game_seed = str(seed if seed is not None else "rebirth-default-seed")`.
- [app.py](app.py) `start_memory_rebirth_match` — guest chama `start_match(seed=None)`.
- [services/rebirth_match_store.py:31](services/rebirth_match_store.py:31) — `MATCH_STORE.save` usa `match_id` como chave do `OrderedDict`.

### Impacto
- **Dois convidados simultâneos colidem.** O segundo `start` sobrescreve o match do primeiro. A próxima ação do primeiro convidado lê/escreve no tabuleiro do segundo → **vazamento de estado entre jogadores + corrupção de partida**.
- Em single-worker (estado atual, `gunicorn -w 1`) isso já acontece. Em multi-worker pioraria.
- É bug de **correção**, **privacidade** (vejo o board de outro player) e **integridade**.

### Por que não apareceu nos testes
- A suíte usa seeds explícitos (`seed="..."`), nunca o caminho `seed=None`.
- O simulador roda matches sequenciais.
- E2E roda um match por vez.
- **Nenhum teste exercita dois convidados concorrentes pelo caminho real de produção.** É exatamente o gap que QA de produção pega e simulação não.

### Fix
`start_memory_rebirth_match` deve gerar seed único por match (`secrets.token_hex(8)` ou `uuid4`). Manter determinismo só onde é pedido (replay/tutorial). +1 teste de concorrência guest.

---

## 🔴 SEGUNDA MANCHETE — variedade de bot = zero para convidados

**Todos os 10 matches enfrentaram só o perfil `defensive`.**

### Causa raiz
- [services/rebirth_bot.py:540](services/rebirth_bot.py:540) — `choose_personality` usa `str(seed or match_id or "rebirth-bot")`. Como `game_seed="rebirth-default-seed"` é truthy, **ignora `match_id`** e sempre computa do mesmo string → sempre `defensive`.
- O simulador (`simulate_balance`) rotaciona `BOT_PERSONALITY_ORDER[index % 3]` explicitamente, então parecia variado nos relatórios. **Produção não rotaciona.**

### Impacto
- Primeira impressão do jogador é monótona: mesmo adversário, mesmo deck, mesma sensação, sempre.
- `aggressive` e `opportunist` — os dois perfis mais interessantes — **nunca aparecem para convidados**.
- Mata variedade percebida exatamente na janela mais frágil de retenção (primeiras sessões).

### Fix
Mesmo fix do seed único resolve os dois bugs de uma vez (seed único → `choose_personality` varia). Alternativamente, `choose_personality` deveria sempre misturar `match_id`.

---

## 1. Problemas de UX

### 1.1 🔴 Onboarding não tem variedade nem progressão de dificuldade percebida
Como convidado, toda partida é defensive com o mesmo deck. Sem `aggressive`/`opportunist`, o jogador novo não sente "estou enfrentando inimigos diferentes". O tutorial (first_duel) usa `novice`, mas a transição pós-tutorial cai direto em defensive eterno.

### 1.2 🟡 Latência por ação corrói o game feel
Medição real (10 batalhas, ~760 ações):
```
action latency: p50=403ms  p90=497ms  p99=818ms  max=949ms
```
Cada invocar/atacar/passar = ~400ms de espera. Um turno completo (invocar + atacar + passar) = **~1.2s parado**. Em 23 turnos médios, o jogador passa mais tempo esperando round-trip do que decidindo. Para um card game isso é **letárgico**. Causas: Render Starter single-worker + sem otimização de payload + público sem otimização de rede. Mitigação real: otimismo de UI (aplicar ação local antes do ack) + reduzir payload de `public_state` (hoje carrega `heuristic_vector`, `art_*`, `silhouette`, `palette` em cada carta de cada resposta).

### 1.3 🟡 Painel de resultado tem 12 sinais simultâneos
Já documentado em [FULLSTACK_EVOLUTION_PLAN.md](FULLSTACK_EVOLUTION_PLAN.md) §4.3. Confirmo na prática: PRIORIDADE / CADEIA EVENT-xxxxxx / JANELA / LINHA DEFENSIVA / LINHA DE SETUP / CAMPO EQUILIBRADO / MÃO INIMIGA competem com o headline. Jogador novo não sabe onde olhar. `CADEIA EVENT-000001` é jargão de engine vazando pra UI.

### 1.4 🟡 Excesso de informação tática para quem não pediu
A "leitura tática" ("Duelista: 4 ataque / 3 guarda, tempo 14") é ouro para hardcore, ruído para casual. Não há toggle "modo simples / modo analista".

### 1.5 🟢 Estados vazios e erros estão limpos
Coleção/loja/recompensas como visitante mostram CTA claro ("ENTRAR / CADASTRAR"). Edge-probes retornam mensagens semânticas. Esse eixo está bom.

---

## 2. Problemas de Gameplay

### 2.1 🔴 Pacing longo confirmado em produção real
```
turns: avg=23.2  min=23  max=24
```
Real, não simulado. 23 turnos × ~1.2s de latência por turno = **~28s de pura espera de rede por partida**, fora o tempo de decisão. Partidas arrastam.

### 2.2 🟡 Defensive pune o jogador button-masher
Win rate do meu driver (joga naïve: sempre maior atacante, ataca primeiro alvo) contra defensive: **2/10 (20%)**. O simulador reporta 52% porque tem heurística de player mais esperta. **O jogador novo real joga mais perto do meu driver do que do simulador** → defensive vai parecer injustamente difícil para iniciantes. Combinado com a manchete (só defensive), o convidado novo perde ~80% das partidas contra um muro. Isso destrói retenção.

### 2.3 🟡 Decisões de baixo impacto percebido
Fusão e traps existem mas raramente disparam no fluxo guest (deck fixo, sem duplicatas suficientes cedo). O jogador faz invocar→atacar→passar repetidamente. Loop repetitivo sem o tempero das mecânicas avançadas.

### 2.4 🟡 Sem recompensa emocional no fim
Vitória/derrota fecham com painel de resultado denso, sem peso. Não há celebração proporcional (a não ser o finale do first_duel). Vencer a 8ª partida sente igual à 1ª.

### 2.5 (do simulador, validar com telemetria real) Cartas problemáticas
`card_006` Scorchscale Imp dominante (WR 0.71); 6 low-impact; 3 dead-hand; `earth_counter` WR 0.02. Detalhe em [STUDIO_MASTER_AUDIT.md](STUDIO_MASTER_AUDIT.md) §P2.7.

---

## 3. Problemas Visuais

### 3.1 🔴 Badge "BEST PLAY" sobrepõe o título da carta
**Reproduzível 100%** na primeira carta recomendada da mão. Zoom confirma: o texto "BEST PLAY" fica POR CIMA de "CINDER LYNX" → ambos ilegíveis ("CINDER LYN▮ST PLAY").
- Causa: [static/css/rebirth.css:7913](static/css/rebirth.css:7913) — `.rb-recommendation-badge { position:absolute; top:5px; right:5px }`. No mini-card estreito da mão, a largura do badge invade a zona do título.
- Fix: reposicionar (ribbon acima do card, ou canto inferior, ou sobre a gema de custo), ou reduzir para ícone, ou empurrar o título.

### 3.2 🟡 "PROTEGIDO NO TURNO 1" repetido em 2 slots vazios do bot
Os slots vazios da zona do bot exibem "PROTEGIDO NO TURNO 1" — mas estão vazios. Texto confunde: protegido o quê? Slot vazio não deveria comunicar proteção. Parece label de placeholder vazando.

### 3.3 🟡 Cockpit mobile denso (8 elementos no 1º viewport)
Nav + carteira + XP + login + HUD + zona bot competem antes da mão aparecer. Já em [FULLSTACK_EVOLUTION_PLAN.md](FULLSTACK_EVOLUTION_PLAN.md) §4.2.

### 3.4 🟢 Identidade visual é consistente e forte
Gold-on-dark coerente em todas as 6 rotas. Card panels uniformes. CTA gold reconhecível. Arte do Dreadclaw no hero é premium. **Esse é um ativo real** — o jogo NÃO parece genérico esteticamente.

### 3.5 🟡 Débito de arte: 20/103 cartas com arte bespoke
`static/assets/rebirth/cards/` tem 20 arquivos. 83 cartas usam fallback. A coleção curada (commit `cad0c3e`) camufla, não resolve.

---

## 4. Problemas Técnicos

### 4.1 🔴 Colisão de match_id de convidado (ver Manchete)
State collision + cross-player leak. O bug técnico mais grave do produto hoje.

### 4.2 🔴 Single-worker é teto rígido para o bug acima e para escala
`render.yaml:8` → `gunicorn -w 1 --threads 100`. `MATCH_STORE` ([app.py:71](app.py:71)) e `MATCH_TELEMETRY_CLOCKS` ([app.py:74](app.py:74)) são dicts em memória. Subir para `-w 2` quebra continuidade de match. Detalhe em [FULLSTACK_EVOLUTION_PLAN.md](FULLSTACK_EVOLUTION_PLAN.md) §2.3.

### 4.3 🟡 `public_state` carrega payload pesado por carta
Cada carta no estado serializa `heuristic_vector`, `art`, `art_finish`, `art_key`, `art_status`, `art_version`, `silhouette`, `palette`, `flavor`, `status_affinity`. Em cada resposta de ação. Para uma mão de 5 + campo de 3 + campo bot de 3, isso multiplica. Reduzir o contrato público de carta a runtime (atk/guard/cost/ability/art_key) e deixar metadados estáticos em fetch único reduziria latência (§1.2).

### 4.4 🟡 Defesa anti-injeção é denylist, não allowlist
[app.py:586](app.py:586) — `AUTHORITATIVE_COMBAT_FIELDS = {"exhausted","has_attacked","has_acted"}`. Edge-probe injetando `{damage:9999, winner:"player"}` retornou **HTTP 200** (campos ignorados pela engine, sem efeito — não é exploit vivo). Mas denylist é frágil: nova flag autoritativa esquecida no set vira brecha. Allowlist de campos aceitos é o padrão robusto.

### 4.5 🟢 Edge cases validados corretamente
- `attacker_instance_id="ghost"` → 400 `invalid_attacker`
- `card_id="card_999"` → 400 `invalid_card`
- `match_id="does-not-exist"` → 404 `missing_match`
- CSRF ausente → 403 `csrf_required` (incl. `/api/labs/` pós-Sprint 1)

Validação de input do dispatcher é sólida. Sem 500s não-tratados em ~760 ações.

### 4.6 🟢 Determinismo é production-grade
`canonical_state_hash` + replay + parity. Base de anti-cheat e PvP.

---

## 5. Problemas de Arquitetura

### 5.1 🔴 ~6000 LOC de código zumbi + 14 MB de backups
`services/battle_engine_v2.py` (2326), `battle_engine_v2_adapter.py` (916), `card_effect_resolver.py` (774), `match_engine_facade.py` órfão, `arena_*`/`ascension_*` órfãos, `backups/` 14 MB, `tests/legacy_disabled/` 256 KB. Confunde devs novos, infla superfície de busca. Detalhe em [FULLSTACK_EVOLUTION_PLAN.md](FULLSTACK_EVOLUTION_PLAN.md) §1.2.

### 5.2 🟡 God-objects emergindo
- `rebirth_persistence.py` 2651 LOC / 70 métodos → split por domínio (schema/match/user/economy/telemetry).
- `rebirth_engine.py` `resolve_turn` 270 LOC, `_apply_trap_effect` 210 LOC → quebrar.
- `rebirth.js` 3259 LOC → modularizar.
- `app.py` 1586 LOC / 80 rotas → Blueprints.

### 5.3 🟡 Acoplamento seed → match_id → personality
Um único `seed=None` propaga para 3 comportamentos (match_id, game_seed, personality) e quebra os 3 juntos. Mostra acoplamento implícito: `choose_personality`, `_match_id` e `create_match` deveriam receber fontes de entropia independentes, não derivar tudo do mesmo seed default.

### 5.4 🟢 Separação contrato/regra/transporte está correta
dispatcher → engine → serializer. Preservar.

---

## 6. Sensação Geral do Produto

| Pergunta | Resposta brutal |
|---|---|
| **Parece divertido?** | Parcialmente. O combate tem ossatura boa, mas o convidado novo enfrenta um muro defensive repetitivo com 1.2s de espera por turno. Diversão fica refém de pacing + variedade. |
| **Parece moderno?** | Sim esteticamente. Não em responsividade de input (latência alta mata a sensação "snappy" que jogos modernos têm). |
| **Parece profissional?** | Visualmente sim. Sob o capô, a colisão de match_id é amadora — é o tipo de bug que não pode existir num produto que se diz pronto. |
| **Parece genérico?** | **Não.** Identidade visual é distinta e forte. Esse é o maior trunfo. |
| **Jogador entende o objetivo?** | Razoavelmente — "reduza o HP do bot a 0" é claro. As mecânicas secundárias (fusão, traps, chains) não. |
| **Existe retenção?** | **Frágil.** Sem loop diário com payoff, sem variedade de bot, sem progressão de dificuldade percebida. A campanha de 10 nós é o único gancho real, e exige conta. |
| **Identidade forte?** | Visual sim. Mecânica/narrativa ainda não — bots são perfis, não rivais. |
| **Pronto para mercado global?** | **Não.** Bloqueadores: colisão de estado guest, single-worker, latência, débito de arte, retenção rasa. |
| **Principal fraqueza hoje?** | A colisão de match_id de convidado — corrompe partidas concorrentes e vaza estado entre jogadores. |
| **O que destruiria retenção?** | Dois convidados colidindo numa demo viral; ou o novo player perdendo 8 de 10 contra o mesmo muro defensive. |
| **O que mais afasta novos jogadores?** | Latência de input + monotonia de adversário + parede de dificuldade na primeira sessão. |

---

## 7. Prioridades de Correção

### 🔴 CRÍTICO (bloqueia qualquer abertura)
1. **Seed único por match de convidado** — corrige colisão de `match_id` (§Manchete, [rebirth_state.py:171](services/rebirth_state.py:171)) **e** variedade de bot de uma vez. +teste de 2 convidados concorrentes.
2. **Multi-worker readiness** — extrair `MATCH_STORE` para backend compartilhado antes de escalar workers (§4.2).

### 🟠 ALTO (bloqueia retenção)
3. **Latência de input** — UI otimista + enxugar payload de `public_state` (§1.2, §4.3). Alvo: ação percebida < 100ms.
4. **Variedade + curva de dificuldade do bot** pós-tutorial (já resolvido em parte pelo fix #1; adicionar progressão real).
5. **Badge "BEST PLAY" sobrepondo título** ([rebirth.css:7913](static/css/rebirth.css:7913)) — bug visual reproduzível.
6. **Cockpit mobile** denso (§3.3).

### 🟡 MÉDIO (qualidade de produto)
7. Hierarquizar painel de resultado; esconder jargão `CADEIA EVENT-xxxxxx` (§1.3).
8. Label "PROTEGIDO NO TURNO 1" em slots vazios (§3.2).
9. Débito de arte 20→52 cartas (§3.5).
10. Allowlist anti-injeção em vez de denylist (§4.4).
11. Loop diário com payoff visível (retenção).
12. Balance de cartas (§2.5) — após telemetria real.

### 🟢 BAIXO (higiene técnica)
13. Deletar ~6000 LOC zumbi + 14 MB backups (§5.1).
14. Split de god-objects (§5.2).
15. Refatorar `resolve_turn`/`_apply_trap_effect` (§5.2).

---

## Apêndice — dados brutos das 10 batalhas

```
Battle  1 [defensive]: FIN winner=player turns=24 (summon=16 atk=23)
Battle  2 [defensive]: FIN winner=bot    turns=23 (summon=20 atk=18)
Battle  3 [defensive]: FIN winner=bot    turns=23
Battle  4 [defensive]: FIN winner=bot    turns=23
Battle  5 [defensive]: FIN winner=bot    turns=23
Battle  6 [defensive]: FIN winner=player turns=24
Battle  7 [defensive]: FIN winner=bot    turns=23
Battle  8 [defensive]: FIN winner=bot    turns=23
Battle  9 [defensive]: FIN winner=bot    turns=23
Battle 10 [defensive]: FIN winner=bot    turns=23

AGGREGATE: finished=10/10  turns avg=23.2  outcomes player=2 bot=8
action latency: p50=403ms p90=497ms p99=818ms max=949ms
edge cases: invalid_attacker✓ invalid_card✓ missing_match✓ csrf✓
            authoritative_injection→200 (ignorado, denylist frágil)
```

Harness: [tools/qa/qa_production_battle_driver.py](tools/qa/qa_production_battle_driver.py).
