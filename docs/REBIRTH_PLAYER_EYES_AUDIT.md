# Auditoria "Olhos de Jogador" — 2026-06-11

Contexto: o owner reportou pós-v101 que "não mudou nada" e exigiu testes como
jogador de verdade + crítica honesta. Esta auditoria substitui a validação por
asserts de DOM (que vinha aprovando releases que um humano reprovaria).

## Método (novo padrão de QA deste repo)

1. **Harness `player_eyes.py`** (em /tmp/ambition_qa): Playwright SEM `force`
   — se o clique falha, um humano também falha e vira bug registrado. Partida
   INTEIRA até o fim (não 2 turnos), todas as 13 páginas, mobile + desktop,
   screenshot numerado de cada momento + manifest, captura de console.error /
   pageerror / requestfailed / HTTP≥400.
2. **Leitura visual real**: cada screenshot inspecionada (multimodal), não só
   classes no DOM.
3. **Autópsias dirigidas**: quando o harness travou, scripts de medição
   (getBoundingClientRect + elementFromPoint + probes de API com CSRF) para
   achar a causa-raiz.

Produção verificada antes de tudo: `ambition-tcg.onrender.com` ESTÁ na
v101_VISUAL_UNITY (SW + assets + health ok). O problema não era deploy.

## Bugs que explicam o "jogo sem sentido" (com prova)

### P0.1 — O jogador nunca tem board (design/balance, o pior de todos)
Probe de API, 6 turnos seguidos invocando 1 monstro/turno: **o bot mata
exatamente 1 unidade do jogador por turno, todo turno**. O campo do jogador
oscila entre 0 e 1 unidade a partida inteira; o bot acumula 3. A unidade que
sobrevive está sempre com summoning sickness → o jogador quase nunca tem
atacante pronto → partidas de 19 turnos onde ele só passa a vez e perde.
O balance lab reportava WR 0.47–0.50 porque o script do lab joga otimizado
(multi-play, kill-targeting); um humano casual vive impotência.
`/tmp/ambition_qa/eyes/035_desktop_arena_fim_bot.png` = derrota sem nunca ter
tido 2 unidades vivas.

### P0.2 — Mobile: a mão cobre o campo; invocar tocando o slot é impossível
Autópsia DOM (390×844): campo do jogador y=530 h=114; mão y=561 h=104 —
**a mão está fisicamente sobre os 3 slots**. `elementFromPoint` no centro de
cada slot devolve cartas da mão (`ehEleMesmo: false` nos 3). O harness ficou
65 iterações preso no turno 1 (shots 160–225, todos iguais). O botão INVOCAR
embaixo funciona, mas o alvo visual primário (slot que diz "INVOCAR") não
recebe toque. O e2e passava porque clica o botão, não o slot.
`/tmp/ambition_qa/eyes/900_mobile_autopsia.png`.

### P0.3 — Pós "Encerrar turno", o board às vezes não atualiza
Probe browser: após encerrar o turno 2, o contador seguiu "02" e o board
ficou velho; a invocação seguinte "fez sumir" uma carta (na real o bot já a
tinha matado no servidor — o cliente é que mostrava estado antigo). Para o
jogador: cartas somem/aparecem "do nada" = jogo sem sentido. Race entre cena
do bot (`bot_phase_events`), supressão de popups e `applyState`.

### P0.4 — Desktop: cartas de campo transbordam as células e as fileiras se tocam
Medido: célula de slot 153px de altura, carta de campo 208px → carta do bot
invade a fileira do jogador (sobreposição vertical de 8–16px, zero respiro).
Não existe separação visual entre "lado dele" e "meu lado" (sem linha
central, sem cor por lado). `/tmp/ambition_qa/eyes/021_desktop_arena_t07_inicio.png`.

### P0.5 — Carta de VERSO permanente no campo do bot
Após a cena, sobra uma carta virada (card-back) no slot do bot, sem nome/stats
— o jogador não sabe o que é (`010`, `913`). Provável resto do
`BotTurnDirector.injectSummon` que o re-render não substitui.

### P1.1 — FX de magia cobre a tela inteira
Ao jogar magia: um círculo radial gigante multicolorido cobre o board com um
chip "Carregando" no meio (`026_desktop_arena_t11_magia_alvo.png`). Parece
defeito gráfico, não feitiço.

### P1.2 — Abrir booster não tem reveal
Clique em "ABRIR BOOSTER" → página idêntica, "CARTAS REVELADAS" vazio
(`059`). O momento-dopamina de um TCG não existe.

### P1.3 — Derrota/vitória sem cerimônia
"D E R R O T A" em texto solto sobre o board, sem painel, sem resumo
(turnos/dano/recompensa), sem CTA de revanche em destaque (`035`).

### P1.4 — Tooltip da carta selecionada cobre a própria carta (mobile)
Chip "HOLLOWMARK STALKER / MELHOR..." desenhado sobre a carta da mão
(`170_mobile_arena_t01_carta_sel.png`).

### P2 — Menores, confirmados
- Campanha exige login mas a arena livre não — inconsistente (modal `060`).
- Mão mostra só 3 das 5 cartas no mobile sem indicador de overflow.
- Nav do mobile (2 fileiras + status) come ~25% da tela antes do jogo.
- Nomes truncados em TODAS as cartas de campo ("SCORCHSCAL...").
- Glow `can-act` funciona, mas com P0.1 quase nunca há quem brilhe.
- Zero erros de console — o jogo "funciona"; é inusável por UX, não por crash.

## Crítica honesta (a parte que dói)

- v100/v101 polia a casca (fundo, popups, placas) enquanto o miolo — "eu
  invoco, o bot deleta, repete" — segue quebrado. Por isso o owner não viu
  mudança: a EXPERIÊNCIA não mudou.
- A validação anterior (asserts + screenshots avulsos) aprovava telas que um
  humano reprova em 10 segundos. Este harness é o novo critério de pronto.
- O board desktop continua sem hierarquia: retratos gigantes, 7 caixas
  vazias, mão pequena, tudo com o mesmo peso visual.

## Ficha do que mudar (aguardando aprovação do owner)

**Onda 1 — fazer o jogo fazer sentido (P0):**
1. Balance real: bot não pode limpar o board do jogador todo turno (custo de
   tempo/mana para o bot, agressividade progressiva, proteção de turno 1–3).
   Critério: jogador casual termina partidas com 2+ unidades vivas e vence
   ~50% jogando "normal", não otimizado.
2. Sincronia pós-turno garantida (applyState sempre consistente após a cena;
   eliminar o estado velho na tela).
3. Mobile: mão NUNCA sobre o campo (layout em faixas exclusivas).
4. Desktop: célula do slot = tamanho da carta; respiro + divisor central
   claro entre os lados.
5. Matar o verso fantasma e o FX-círculo gigante.

**Onda 2 — momentos que pagam o jogo (P1):** reveal de booster, telas de
vitória/derrota com resumo+recompensa+revanche, tooltip fora da carta,
overflow da mão visível.

**Onda 3 — coerência de produto (P2):** política única de login, nav mobile
compacta em jogo, nomes legíveis nas cartas.

Artefatos: /tmp/ambition_qa/eyes/ (240+ screenshots), mobile_autopsy.json,
desktop_autopsy.json, player_eyes.py (harness reutilizável).
