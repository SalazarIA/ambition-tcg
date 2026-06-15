# P0.1 — Revalidação "jogador nunca tem board" (Top10 #6)

Data: 2026-06-15 · Lab casual via dispatcher real, 150 partidas (3 perfis de bot)

## Bug original (auditoria olhos-de-jogador, 2026-06-11)

O jogador casual nunca tinha board: o bot matava 1 unidade/turno, presença de
board oscilava entre 0 e 1, e o WR casual real era ~0,17 — impotência. O lab
otimizado mascarava isso reportando WR ~0,47.

## Estado atual (revalidado)

| Métrica | Valor | Meta de saúde | Veredito |
|---|---|---|---|
| Board presence (casual) | **1,96** | >= 1,0 | ✅ resolvido |
| Player WR (casual) | **0,70** | 0,40–0,60 | ⚠️ acima do teto |
| Turnos médios | 12,0 | — | ok |
| Unfinished | 0,7% | baixo | ok |

Por perfil: defensivo WR 0,64 / presença 1,82 · agressivo 0,72 / 1,97 ·
oportunista 0,74 / 2,08.

## Conclusão

- **P0.1 está resolvido**: o jogador casual mantém ~2 unidades vivas e vence a
  maioria — o oposto da impotência original (a Onda 1.1 levou o WR de 0,17→0,71).
- **Overshoot**: o WR casual (0,70) está acima do teto de saúde (0,60). O bot
  ficou fácil demais para o casual. É um **ajuste de tuning** (deixar o bot
  pressionar um pouco mais para cair em 0,55–0,60), não mais um P0.
- O "30→0" observado na sessão manual era o *script* de QA jogando mal, não o
  baseline casual — confirmado pelos números acima.

## Guard-rail

`tests/rebirth/test_p01_casual_board.py` trava o piso (board presence >= 1,0 e
WR >= 0,40 por perfil), impedindo regressão silenciosa à impotência. O ajuste do
teto (0,60) deve ser feito com telemetria humana, conforme a política de balance.
