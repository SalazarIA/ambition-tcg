# Rebirth Arena Feel (v100) — Onda A + Onda B

Atualizado: 2026-06-10 · Branch: `feat/arena-feel` · Suíte: 1313 passed · E2E: 19 passed

Origem: testes reais de UX (playthrough Playwright desktop+mobile com
screenshots por momento) que encontraram 3 bloqueadores de input e um board
visualmente vazio. Referências de craft: padrões de TCG AAA (seta de ataque,
mulligan como decisão, turno do inimigo encenado).

## Onda A — Input & crash (bugs que faziam o jogo parecer quebrado)

| Bug | Causa | Fix |
| --- | --- | --- |
| Armar QUALQUER trap travava a partida (botões mortos, F5 obrigatório) | `result.outcome "Trap Armed"` virava classe CSS `is-trap armed` → exceção em `classList.add` derrubava o render | `cssToken()` sanitiza qualquer string do servidor antes de virar classe |
| Cliques "engolidos" após cada jogada (3 de 4 cartas da mão inclicáveis) | `#result-panel` (z-index 76) sobrepunha a mão com `pointer-events: auto` | Painel inteiro `pointer-events: none` (botões internos seguem clicáveis) |
| Mobile quase injogável (239 cliques sem sair do turno 2) | Painel + coach + chip de mulligan + FAB de som cobrindo mão/campo | Painel sem hit-area, FAB no topo, mulligan virou tela própria, slots 112px |

## Onda B — O board virou um board

- **Tela de mulligan** (estilo decisão de TCG): mão inicial em cartas grandes,
  "Trocar mão" / "Manter mão", backdrop dispensa, não aparece no primeiro
  duelo guiado (o tutorial conduz).
- **Arena central larga** (era 460-522px encostada à esquerda → até 880px
  centrada), mesa com anel rúnico + respiração de luz, slots vazios viram
  altares discretos, cartas de campo 150×212 com nome/ATK/GRD legíveis.
- **Seta de ataque** SVG curva do atacante ao ponteiro com fluxo animado;
  alvos válidos pulsam (TAUNT restringe igual à engine); **preview de dano**
  no hover/tap: `-X`, `☠` quando mata, "Escudo absorve" quando SHIELD.
- **Turno do bot encenado** (`bot_phase_events` no next-turn): invocações
  surgem no slot com pop, ataques fazem lunge no alvo real, dano flutua,
  HP tica em tempo real, armadilha/magia anunciadas — passos de 300-620ms,
  tap pula a cena, `prefers-reduced-motion` desliga.
- **Números de dano flutuantes** também nos ataques do jogador.
- **Coluna de comando** à direita (Invocar + Encerrar Turno em medalhão
  dourado) sob o retrato inimigo — fora dos slots, perto do fluxo de jogo.
- **Ticker de combate** no canto superior esquerdo da arena (o antigo painel
  central que disputava espaço com a mão).

## Contratos respeitados

- Guards de performance: sem `backdrop-filter`/`drop-shadow`/`offsetWidth`
  (verificados por teste); overlay usa opacidade, seta usa caminho-sombra.
- Alvo de toque mobile ≥112px nos slots; IDs/âncoras do tutorial e dos
  testes v67 intactos; SW `v100_ARENA_FEEL` renova caches no deploy.

## Como foi validado

1. Playthroughs Playwright reais (sem `force=True`) em 1440×900 e 390×844:
   mulligan → invocação em slot escolhido → seta+preview → clash com floats →
   cena do bot → trap SEM soft-lock (era 100% reproduzível antes).
2. Screenshots de prova em cada estado (FINAL_desktop_*/FINAL_mobile_*).
3. Suíte completa 1313 passed; E2E 19 passed (2× seguidas); teste JS de áudio ok.
