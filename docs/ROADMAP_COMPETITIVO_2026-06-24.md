# Roadmap Competitivo — Ambitionz Rebirth → concorrente de TCG

**Data:** 2026-06-24 · Autor: Claude (proposta para revisão do dono)
**Status:** rascunho para aprovação — nada aqui foi implementado ainda.

## Tese
Não dá pra "ter mais conteúdo que Hearthstone". O caminho é **diferenciar pelo
ativo que já temos: um engine de regras determinístico com replay**. Isso torna
**ranked assíncrono com ghosts** viável (competitivo sem precisar de população
online simultânea nem netcode) — esse é o diferencial. E **nada disso se prova
sem uma camada de dados** (funil + error tracking), por isso ela vem cedo.

Ordem de prioridade real (minha recomendação):
**Fundação (onboarding + dados) → Keystone (ranked async/ghosts) → Stickiness
(economia/deck/polish) → Live ops.**

## Estado atual — o que JÁ existe (não reconstruir)
| Capacidade | Existe? | Onde |
|---|---|---|
| Engine determinístico + hash canônico + paridade | ✅ | `services/rebirth_dispatcher.py`, `rebirth_engine.py` |
| **Replay de partida** (chave p/ ghosts) | ✅ | `services/rebirth_replay.py` |
| Telemetria (eventos) | ✅ parcial | `services/rebirth_telemetry.py`, `static/js/beta_telemetry.js` |
| Ranking/leaderboard (rota + tela) | ✅ esqueleto | rota `/rebirth/ranking`, `templates/rebirth_ranking.html` |
| Booster + raridade + revelação carta-a-carta | ✅ | `rebirth_product.js`, `/rebirth/shop` |
| Fusão/evolução de cartas | ✅ | `rebirth_engine.resolve_labs_fusion`, evolve_duplicate |
| Coleção com arte (grade) | ✅ | `templates/rebirth_product.html` |
| Arquétipos por elemento (fogo/água/terra/sombra/arcano) | ✅ regra | `rebirth_keywords.py`, `rebirth_cards.py` |
| Missões / progressão (rotas) | ✅ esqueleto | `/rebirth/progression`, `/rebirth/missions` |
| Áudio / FX | ✅ base | `rebirth_audio.js`, `rebirth_fx.js`, `rebirth_boss_fx.js` |
| Deploy pipeline + backup pré-migração | ✅ | `render.yaml`, `tools/ops/backup_before_migrate.py` |
| Schema/migrações | ✅ | `services/rebirth_schema.py` |

**Conclusão:** quase tudo tem base. O trabalho é **fechar loops, comunicar ao
jogador e medir** — não começar do zero.

---

## FASE 0 — Fundação (agora; barato; maior parte eu faço sozinho)

### 0.1 Onboarding impecável (#1)
- **Escopo:** turno protegido bloqueia **todo dano de face** (ataque **e** BURST/entrada),
  com a copy do tutorial batendo; **mão do 1º duelo roteirizada** (determinística,
  não seed por usuário); 2–3 dicas contextuais ("isto é Provocar", "detonação =
  dano de entrada"). Hoje o BURST só está suprimido no 1º duelo (paliativo).
- **Já existe:** proteção de turno 1 (ataque), supressão parcial de BURST.
- **Esforço:** P–M · **Risco:** baixo (escopado ao tutorial) ·
- **Depende de:** 0.2 pra *provar* (funil).
- **Entrega:** **auto-deploy** (eu faço).
- **Aceite:** % que conclui a 1ª partida ≥ 85%; 0 eventos de "dano na face no turno
  protegido" no 1º duelo.

### 0.2 Camada de dados (núcleo do #7) — O DESTRAVADOR
- **Escopo:** (a) **error tracking** (ex.: Sentry) backend+frontend; (b) **funil de
  1ª sessão** (carregou → 1ª partida → 1ª vitória → retorno D1) sobre a telemetria
  que já existe; (c) **dashboard de balance** (winrate por arquétipo/dificuldade)
  a partir dos eventos de fim de partida.
- **Já existe:** telemetria de eventos; falta agregação/visualização e crash logs.
- **Esforço:** M · **Risco:** baixo (observabilidade, não muda gameplay) ·
- **Depende de:** decisão de **ferramenta** (Sentry? Plausible/PostHog? custo).
- **Entrega:** **PR revisado** (toca chaves/segredos e talvez serviço pago → §decisão).
- **Aceite:** dashboard que responde "o 1º-5min está impecável?" e "qual arquétipo
  está quebrado?" sem rodar lab.

> **Por que primeiro:** sem 0.2 você não consegue afirmar "5 min impecável", nem
> tunar balance (que viemos adiando "pra telemetria"), nem operar live ops.

---

## FASE 1 — Keystone: Ranked assíncrono + Ghosts + Season 0 (#2 + semente #6)

### 1.1 Ghosts (oponentes assíncronos)
- **Escopo:** ao terminar partidas, **persistir deck + (opcional) replay** do
  jogador; o "matchmaking" assíncrono escolhe um **ghost** de faixa de ELO parecida
  e a IA pilota aquele deck (ou re-executa decisões via replay). Sem rede em tempo real.
- **Por que viável aqui e não em outros jogos:** engine determinístico + `rebirth_replay`.
- **Esforço:** G · **Risco:** médio (schema novo: decks públicos/ghosts, ELO) ·
- **Depende de:** 0.2 (precisa medir), schema.
- **Entrega:** **PR revisado** (schema + matchmaking + anti-abuso básico).

### 1.2 Ladder / ELO + Season 0
- **Escopo:** rating por jogador, divisões, reset/recompensa de temporada. Reusa a
  tela de ranking existente.
- **Esforço:** M–G · **Risco:** médio · **Depende de:** 1.1.
- **Entrega:** **PR revisado**.
- **Aceite:** um visitante consegue subир de divisão enfrentando ghosts; ladder
  reseta e premia no fim da Season 0.

> **Decisão sua:** confirmamos **async-ghosts** (recomendado) e **adiamos PvP
> real-time** até haver população? (PvP real-time = netcode + anti-cheat + MM +
> custo de servidor; não recomendo agora.)

---

## FASE 2 — Stickiness (economia, deckbuilding, polish)

### 2.1 Loop de economia (#3)
- **Escopo:** recompensa **diária**, **pó/crafting** (desmanchar repetidas → criar
  o que falta), progressão de nível com **cosmético**, "primeira vitória do dia".
  Fechar: jogar → ganhar → abrir → melhorar → voltar.
- **Já existe:** booster, fusão/evolução, coleção.
- **Esforço:** M–G · **Risco:** médio (schema de moeda/inventário; **anti-exploit**) ·
- **Entrega:** **PR revisado** + **decisão de produto** (preços, se há compra real).

### 2.2 Deckbuilding claro (#4) — alto ROI, barato
- **Escopo:** **rótulos de arquétipo** (Aggro Fogo, Controle Água/Terra, Sombra
  Pierce…), **decks-modelo prontos** por arquétipo, dica de curva/sinergia no builder.
  A regra já existe; falta linguagem de jogador.
- **Esforço:** P–M · **Risco:** baixo (conteúdo/UI) · **Entrega:** **auto-deploy** (eu faço).
- **Aceite:** jogador novo monta um deck coerente em < 2 min escolhendo um arquétipo.

### 2.3 Polish audiovisual (#5)
- **Escopo:** elevar **hit, summon, vitória/derrota, pack opening, evolução** —
  som + impacto + recompensa visual.
- **Já existe:** `rebirth_audio/fx`.
- **Esforço:** M (iterativo) · **Risco:** baixo–médio · **Entrega:** **auto-deploy**,
  mas **preciso de você no loop** (áudio/juice não dá pra validar headless).

---

## FASE 3 — Live ops (#6)
- **Escopo:** Season N, **missões semanais**, **eventos limitados**, **patch notes**
  de balance, **recompensas cosméticas**. Pega carona no ladder (Fase 1) e na
  economia (2.1).
- **Esforço:** M–G contínuo · **Risco:** médio · **Entrega:** **PR revisado** + cadência.
- **Aceite:** um jogador tem motivo pra voltar **toda semana**.

---

## Confiabilidade industrial (#7) — corre em paralelo
0.2 entrega o núcleo (erros + funil + balance). O resto vira **rotina**:
- Replay/debug de partida (já temos replay) → ferramenta de suporte.
- Backups (já há `backup_before_migrate`) → agendar/validar restore.
- Pipeline de release com cache-bust (já fazemos) → checklist + smoke automatizado na CI.
- **Esforço:** M distribuído · **Entrega:** PR revisado.

---

## Calls estratégicos (resumo)
1. **Async-ghosts, não PvP real-time.** Diferencia pelo engine; sem buraco de população/netcode.
2. **Dados antes de tunar.** 0.2 é pré-requisito de tudo (inclusive "5 min impecável").
3. **Onboarding medido**, não só consertado.
4. **Fechar loops > criar conteúdo.** Quase tudo tem base; o gap é loop + comunicação + medição.

## O que eu faço sozinho vs. com você
- **Auto-deploy (eu):** 0.1 onboarding, 2.2 deckbuilding, 2.3 polish (com seu olho).
- **PR revisado (schema/backend):** 0.2 dados, 1.1/1.2 ranked, 2.1 economia, 3 live ops.
- **Decisão de produto (sua):** ferramenta de analytics/erros (custo), se há compra
  real/preços, confirmar async-ghosts vs PvP real-time, escopo da Season 0.

## Recomendação de início
Começar pela **Fase 0** (0.1 onboarding eu faço já em auto-deploy; 0.2 dados como
PR revisado assim que você escolher a ferramenta). Em paralelo, posso adiantar
**2.2 deckbuilding** (barato, auto-deploy) enquanto você decide a ferramenta de dados.

### 3 decisões que destravam o resto
1. Ferramenta de **analytics/error tracking** (Sentry + PostHog? algo grátis? self-host?).
2. **Async-ghosts confirmado** e PvP real-time adiado?
3. Tem **monetização real** no horizonte (preços/IAP) ou economia é só progressão?
