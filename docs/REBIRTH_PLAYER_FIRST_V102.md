# Rebirth Player First (v102) — as 3 ondas da auditoria

Atualizado: 2026-06-11 · Branch: `feat/three-waves`
Origem: docs/REBIRTH_PLAYER_EYES_AUDIT.md (owner: "não mudou nada; testem
como jogadores de verdade e sejam críticos"). Cada item abaixo nasceu de um
bug provado por partida real e fecha com critério verificável.

## Onda 1 — o jogo faz sentido

### Balance: o board do jogador existe (P0.1)
- `profile_attack_policy` (rebirth_bot.py): personalidade de alvo por perfil
  — aggressive caça face, opportunist remove só ameaças grandes, defensive
  é muralha que abre linhas do turno 5+, novice é sparring. Clemência nos
  turnos 1–2: a única unidade do jogador não é removida (letal ignora tudo).
- Ritmo de reposição: 1 invocação/turno para todos os perfis (opportunist
  compensa com 2 ataques).
- Lab CASUAL novo (`simulate_casual_balance`): joga como humano normal.
  Baseline 0.175 de WR e presença de board 1.34 → **0.708 / 1.94**. Lab
  tático intacto: 0.517, spread 0.2 (contratos v71/v73/v74 verdes).
- Contrato novo `test_v102_casual_health` impede regressão silenciosa.

### Sincronia pós-turno (P0.3)
- `nextTurn`: o estado do servidor entra SEMPRE (`applyState` em finally),
  mesmo que a cena do bot lance exceção. Era a causa do contador preso em
  "02" e das cartas "sumindo do nada".
- `injectSummon` só substitui altar vazio (não rouba o lugar de carta viva).

### Mobile jogável (P0.2)
- Nav de jogo em UMA linha (selo + abas roláveis + entrar); identidade, XP e
  carteira só nas telas de produto. `--rb-mobile-nav-height` 92→52px real.
- Action bar deixou de ser sticky: era ela que flutuava sobre os 3 slots de
  invocação (toque morto). Sobreposição campo/mão: 83px → 0.
- Pulso do slot de invocação por LUZ (box-shadow), não por scale: alvo
  geometricamente estável para dedo, automação e assistive tech.
- Prova: invocar TOCANDO O SLOT funciona sem `force` nos dois viewports.

### Desktop honesto (P0.4, P0.5, P1.1)
- Célula do grid = carta (208px) com respiro e divisor rúnico central entre
  o lado do bot e o do jogador.
- O "verso fantasma" era o overlay `#bot-card` virando placeholder
  face-down permanente — agora só existe quando carrega informação real.
- A runa gigante sobre o board: o botão JOGAR sequestrava o clique para
  FUSÃO quando havia par fusível. Prioridade corrigida (intenção explícita
  primeiro), cinemática contida (220/320px, overlay 0.62) e cleanup em
  `finally` — o disco nunca mais congela na tela.

## Onda 2 — momentos que pagam o jogo

- **Fim de partida com cerimônia**: painel central com resumo (turnos, HP,
  recompensa quando houver) + "Jogar de novo" e "Continuar" clicáveis; o
  texto-impacto assenta e o painel fica. Contratos preservados: overlay
  segue `pointer-events: none` (botões são exceção), reduced-motion zera
  transições de curtain/text.
- **Booster com reveal**: as cartas viram uma a uma (stagger 120ms,
  perspective flip; reduced-motion desliga). O grid instantâneo morreu.

## Onda 3 — coerência

- Nav mobile compacta durante o duelo (acima).
- Nomes de carta no campo com ellipsis legível.
- Campanha para visitante: o botão explica ("Criar conta p/ jogar" +
  title sobre progresso salvo) em vez de um "Entrar" seco.

## Verificação (o juiz)

`/tmp/ambition_qa/player_eyes_v2.py` joga partidas completas (desktop +
mobile, zero `force`) e aprova/reprova por critério: invocar tocando o
slot, turno sempre avança, board do jogador ≥2 em algum momento, sem verso
fantasma, runa só quando pedida, fim com cerimônia, zero erros de console.
Suíte completa + e2e 2× antes do merge. SW `v102_PLAYER_FIRST`.
