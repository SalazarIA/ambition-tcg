# Rebirth AAA Pass (v99) — P0/P1/P2 em um branch

Atualizado: 2026-06-10 · Branch: `feat/aaa-pass` · Suíte: 1313 passed

Origem: auditoria completa de 2026-06-10 (leitura integral do código + 500
partidas reais via API + browser desktop/mobile), que apontou o jogo como
"correto, porém raso, fácil e pesado". Este passe ataca as três frentes.

## Regras de jogo (o que mudou para o jogador)

| Antes | Agora |
| --- | --- |
| Deck custom comprava NA ORDEM do loadout; mão inicial idêntica em toda partida | Shuffle determinístico por seed para todo deck, com garantia de abertura jogável (1+ monstro custo ≤2) |
| Sem mulligan | Mulligan único antes da primeira ação (`POST /api/rebirth/mulligan`, botão "Trocar mão") |
| Invocou, atacou no mesmo turno | Summoning sickness; **RUSH (Investida)** existe de verdade |
| 7 de 8 keywords eram texto morto na UI | LIFESTEAL, SHIELD, PIERCE, EXECUTE ligadas no combate; TAUNT vale para o bot também; BURST/TAUNT/EXECUTE em lendárias + tier-2 escolhidos; tier 1 é baseline limpo (keyword = recompensa de evolução) |
| Fusão dava "BREAKTHROUGH" cosmético (overflow 2 era universal) | Fusão concede **PIERCE real** (overflow integral no herói); breakthrough universal segue capado em 2 |
| Shadow Reaper não fazia nada (ready apagava o exhaust) | Exhaust sobrevive ao ready e expira só depois de o bot agir |
| Partida acabava em "exaustão" súbita se QUALQUER lado zerasse as cartas | Fadiga incremental (1, 2, 3… por turno com deck vazio) + teto de segurança de 120 turnos |
| Traps disparavam dos dois lados em qualquer combate | Trap revela apenas quando o DONO é atacado (inclusive ataque direto) |
| Magia não tinha alvo | Magia de dano pode mirar unidade inimiga (`target_instance_id`) |
| Atacar travava o turno (sem desenvolver depois) | Fase principal fluida até encerrar o turno |
| Sinergias K2 nunca avaliadas | `synergy` avaliada no clash; 8 cartas com sinergia + rótulo na UI |
| Custos de magia silenciosamente capados em 2 | Custos honram as definições (StoneSkin/TidalRenewal = 3) |
| Sem escolha de slot ao invocar; display remapeava posições | Clique no slot escolhe a posição; display = posição lógica (adjacência de fusão legível) |

Versões: `rebirth_*_v99` (engine/card set/ruleset/reducer) — replays antigos
são incompatíveis por definição (as regras mudaram).

## Bot e dificuldade

- Multi-invocação com orçamento por perfil (defensivo/oportunista 2, agressivo 1)
  e orçamento de ataques por perfil (defensivo 1, oportunista 1, agressivo 2).
- "Board-first": suporte nunca consome a mana da invocação do turno.
- Pontos cegos modelados: `water_tide`, `fire_surge`, `earth_fortify`,
  `water_guard`, `earth_bulwark`; TAUNT respeitado no targeting; RUSH do bot
  ataca no turno da invocação; sickness entendida pela heurística.
- Lab recalibrado (jogador simulado joga sob as regras novas: espera sickness,
  multi-joga, respeita taunt, targeting de kill): winrate do jogador ~0,47-0,50
  agregado; por perfil dentro de 0,40-0,60 com spread ≤0,35.

## Infra e performance

- `RebirthRepository` cacheado por destino (antes: um engine SQLAlchemy NOVO
  com pool próprio por chamada, várias por request).
- `ensure_schema` valida uma vez por instância (antes: toda operação).
- `upsert_match_history` delta: eventos/comandos novos via watermark (antes:
  re-INSERT do histórico inteiro a cada ação — O(n²)).
- Catálogo (103 cartas, ~200KB) fora do match; runtime persistido magro
  (sem snapshots/eventos/comandos embutidos — eventos voltam das tabelas
  `match_events`/`match_commands` na rehidratação): snapshot por partida caiu
  de ~375KB para ~86KB e o upsert por ação deixou de reescrever histórico.
- Partida NÃO persiste no start → fim das partidas-fantasma no histórico.
- `?limit=abc` clampado (era 500); seed reutilizada não colide mais com a
  partida anterior; webhook de billing devolve 500 em `credit_failed` (retry
  do Stripe); reducer de `ENERGY_REFRESHED` honra `energy_ramp` por lado.

## Frontend

- Mulligan, escolha de slot, alvo de magia por clique, sickness visível
  (dessaturação + "Zzz" + mensagens), badges de keyword nas cartas de campo,
  linha de sinergia no textbox.
- Unsplash removido (fallback local) e fora do CSP; SW `v99_AAA_RULES_PASS`.
- Mobile: overflow do onboarding zerado, mão sem clipe, nav compacta.

## Faxina (P2)

- ~57k linhas deletadas: arena3d (`static/dist` + `frontend/`),
  `arena_clean_v48`, família `ambitionz_*`, `style.css` (11,6k linhas →
  `legal.css` mínima), engine duplicada `services/rebirth/`, `game/`,
  `models.py`, `sockets/`, `routes/`, serviços legados (economy*, card_stats,
  beta_telemetry, reward_tuning, admin/, database/, security/), 48 templates
  órfãos e tools de QA do BE2/arena.

## Backlog consciente (não entrou neste branch)

1. Modularização dos arquivos gigantes (`rebirth.js` ~4k, `rebirth.css` ~14k
   com 975 `!important`, `rebirth_persistence.py` ~3k, `app.py` ~2,4k) — plano
   da Fase 3 do roadmap; mexer nisso junto com a mudança de regras dobraria o
   risco do branch.
2. CSP sem `unsafe-inline` (exige nonces nos templates).
3. Arte bespoke além das 13 cartas originais; habilidades únicas por carta
   (hoje 4 templates por família); segunda família de mecânicas.
4. Cap de snapshots no match vivo em memória (MATCH_STORE).
