# Rebirth Performance Study (v103) — metodologia de estúdio

Atualizado: 2026-06-11 · Branch: `feat/perf-study`
Pedido do owner: "polir arquitetura/engine, tempo de resposta, e analisar
precisamente como um estúdio profissional".

## Metodologia

Três camadas de medição, sempre em percentis (p50/p95/p99/max), nunca média
solta — bancada em `/tmp/ambition_qa/perf_bench.py` + `perf_client.py`:

1. **Engine pura (in-process)**: ms por comando real jogando partidas
   inteiras (start/play_card/declare_attack/next_turn) + custo e tamanho da
   serialização pública.
2. **HTTP real**: latência por endpoint e bytes (JSON cru e NO FIO com gzip)
   ao longo de partidas completas.
3. **Cliente (Playwright + Performance APIs)**: tempo-até-jogável,
   transferência por tipo de asset, input delay (Event Timing), long tasks,
   duração de frame (rAF) durante a cena do bot.

Produção ganhou **Server-Timing** em toda resposta — qualquer DevTools de
jogador vira ferramenta de profiling de produção.

## Baseline → Depois (dev local, SQLite)

### Engine (ms, in-process)
| comando | p50 antes | p95 antes | p50 depois | p95 depois | budget CI |
| --- | --- | --- | --- | --- | --- |
| start_match | 1.95 | 2.11 | 2.06 | 3.48 | — |
| play_card | 0.11 | 0.14 | 0.12 | 0.20 | — |
| declare_attack | 1.09 | 2.25 | 1.15 | 2.64 | p95 < 25 |
| next_turn | 2.23 | 4.16 | 2.44 | 5.34 | p95 < 40 |
| public_state (serialize) | 1.30 | 1.56 | 1.09 | 1.75 | — |

A engine já era saudável — o problema não estava aqui.

### Payload por ação do jogador (o gargalo real)
| endpoint | JSON antes | JSON depois | **fio (gzip) depois** | redução no fio |
| --- | --- | --- | --- | --- |
| start | 9.9 KB | 9.9 KB | **3.3 KB** | −67% |
| play-card | 27.0 KB | 23.0 KB | **3.8 KB** | −86% |
| attack | 29.3 KB | 26.7 KB | **3.9 KB** | −87% |
| next-turn | 42.9 KB | 35.2 KB | **4.2 KB** | **−90%** |

Em rede móvel (~1 MB/s útil), next-turn caiu de ~43ms de transferência para
~4ms — por clique, todo clique.

### Página da arena (cliente)
| métrica | antes | depois |
| --- | --- | --- |
| transferência total | 1 231 KB | ~700 KB (imagens −527 KB) |
| maiores assets | 3 JPG = 839 KB | 3 WebP = 312 KB |
| tempo-até-jogável (local) | 524 ms | mantém |
| input delay p95 | 5.2 ms | mantém (excelente) |
| long task máx (boot) | 298 ms | mantém (alvo futuro) |

## O que mudou (e por quê)

1. **Estado público emagrecido** (`rebirth_serializers.py`):
   - `player.field`/`bot.field` eram a MESMA lista dos slots repetida — só
     `player_field`/`bot_field` (o que o front lê) viajam agora (`pop`, sem
     deepcopy extra).
   - Eventos públicos sem cartas embutidas (`MONSTER_SUMMONED.card` ~1.2KB,
     `CARDS_DRAWN.cards` ~1.7KB): o front só lê ids/mensagens; replay/reducer
     usam as tabelas `match_events`, intocadas. `bot_phase_events` (a cena)
     continua cru — o diretor precisa da carta.
   - Validação de contrato só no que ENTRA no payload (mão/campo/traps);
     deck e descarte inteiros eram ~35 validações por request para virar
     dois counts.
2. **Transporte**: `flask-compress` (gzip/brotli, min 1KB) para JSON/HTML/
   CSS/JS/SVG + `SEND_FILE_MAX_AGE_DEFAULT=30d` (estáticos têm `?v=versão`;
   o service worker é servido por rota própria `no-cache`, não preso).
3. **Imagens dimensionadas para o uso**: retratos de herói e paisagem da
   arena de JPG cheio para WebP no tamanho de exibição (839→312 KB).
4. **Observabilidade**: header `Server-Timing: app;dur=…` em toda resposta.

## Contratos de regressão (CI)

`tests/rebirth/test_v103_performance_budget.py`:
- p95 in-process: attack < 25ms, next_turn < 40ms (folga 5x+ sobre baseline
  para CI compartilhada; estourar = regressão real de algoritmo).
- Estado público < 40KB cru e < 10KB gzip.
- Shape: sem `side.field` duplicado, eventos públicos sem `card`/`cards`.
- Resposta da API com `Content-Encoding: gzip` e `Server-Timing` presentes.

## Próximos alvos (medidos, ainda não atacados)

- Long task de boot ~300ms (parse/execução inicial do rebirth.js 4.6k linhas
  — candidato a split por página).
- Frames da cena do bot p95 ~34ms no headless (verificar em devices reais
  via Server-Timing + Performance API antes de otimizar).
- CSS 15k linhas (~87KB gzip): purga de blocos legados FATES/v6x não usados.
