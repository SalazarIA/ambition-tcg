# Rebirth Visual Unity (v101)

Atualizado: 2026-06-10 · Branch: `feat/visual-unity` · Suíte: 1313 passed · E2E: 19 passed (2×)

Origem: feedback direto do owner pós-v100 — "balões um em cima do outro,
páginas diferentes visualmente, jogo sem sentido". Três frentes, cada uma
validada com playthrough Playwright real + amostragem de DOM.

## 1. Disciplina de balões (um canal de feedback por vez)

- `showActionPopup` agora tem árbitro: **não dispara** enquanto o banner de
  turno está na tela, enquanto a cena do bot roda, nem nos 900ms seguintes
  (a cena já narrou tudo com floats/lunges). A própria cena usa `force`.
- Invocação **não gera mais balão** — a carta aparecendo no slot É o feedback.
- Resultado de ação só vira balão quando há dano de herói (`heroSwing > 0`);
  troca de unidades fala por floats e HP.
- Popup reposicionado para o terço inferior (`bottom: 30%`); o banner de
  turno é dono exclusivo do topo. Geometricamente impossível sobrepor.
- Na mira, o badge de risco some (`.is-choosing-attack … .rb-risk-badge`):
  o chip de preview de dano é a única voz sobre o alvo.
- **Prova**: amostrador a 120ms durante a cena do bot — 0/50 amostras com
  dois canais visíveis simultaneamente.

## 2. Identidade única (todas as páginas no mesmo mundo)

- O céu/ruínas/lua/estrelas da arena (F24) agora é o fundo fixo de **todas**
  as páginas `rb-home-page` (home, campanha, coleção, loja, deck builder,
  progressão, ranking, billing) via `body::before` — mesmo data-URI, zero
  request extra.
- Títulos de página com a mesma voz tipográfica da arena: display font +
  gradiente dourado.
- Receita única de painel (moldura dourada sobre madeira escura — a mesma
  da mesa e do sheet de mulligan) aplicada a `rb-product-panel`, `rb-product-card`,
  shelf da coleção, drawer do catálogo, balance lab, feedback e tracks.
- CTAs primários = botão-medalhão dourado da arena; secundários = madeira
  escura com borda dourada.
- **Campanha**: lista de texto virou trilha de encontros — placas com
  medalhão-silhueta (glifo + acento por nó via `--node-accent`), numeral de
  etapa, selo/cadeado, próximo nó pulsando, bloqueados dessaturados.

## 3. Clareza de jogo (o board responde "o que eu posso fazer?")

- Monstros prontos para agir pulsam verde (`.can-act`, calculado com a
  mesma regra da engine: sem sickness, sem exaustão, fase choose).
- Cartas jogáveis na mão têm borda viva; impagáveis ficam dessaturadas.
- Durante a cena do bot o botão de turno vira **"Turno inimigo…"**
  (desabilitado) e volta sozinho — a espera tem nome.

## Contratos respeitados

- Sem `backdrop-filter` / `drop-shadow` / `offsetWidth` (guards de teste).
- Template segue com "Encerrar turno" (pins de contrato); o swap de label é
  só runtime durante a cena.
- SW `v101_VISUAL_UNITY` renova caches no deploy (pin atualizado no teste
  de contrato + regex de limpeza).

## Validação

1. Playthrough Playwright real (desktop 1440×900 + mobile 390×844):
   mulligan → invocação sem balão → glow de prontidão no turno 2 → mira
   sem badge de risco → cena do bot com botão explicando a espera.
2. Amostragem de DOM a 120ms provando zero sobreposição de balões.
3. Screenshots das 6 páginas de produto nos dois viewports com o fundo único.
4. Suíte 1313 passed; E2E 19 passed 2× seguidas.
