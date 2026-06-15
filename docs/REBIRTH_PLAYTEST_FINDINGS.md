# Rebirth — Playtest 10k + jornada (achados e ações)

Data: 2026-06-15 · Catálogo de teste: **100 cartas** comuns/incomuns (as 3
"lendárias" são placeholders de conteúdo futuro — ignoradas aqui).

## Método
- **10.000 partidas** otimizadas no motor real (via dispatcher) + **1.000 casuais**.
- **Jornada de UI** (Playwright, sem `force`): 9 telas + arena + shop, varredura de erros.
- **Economia in-process**: registro → abrir boosters (seed único) → curva de coleção → editar baralho.

## Resultados

### Estável ✅
0 erro de console / page / network em todas as telas. Board casual saudável (P0.1 resolvido).

### Balance (10k)
- **Macro impecável:** WR jogador/bot **49,3% / 50,7%**, 0 cartas nunca usadas, sem stalemate.
- ⚠️ **Falso outlier (lição de método):** `card_084` "Bola de Fogo da Arena" aparecia com WR **0,86** ("dominant"). Testei o nerf (3 mana / 2 de dano): o WR **mal moveu (0,82)** e o macro seguiu **49/51** → é **viés de seleção** (finalizador jogado quando já se está ganhando), **não poder**. Nerf **revertido — nenhuma carta mudou**. O flag "dominant" do `balance_flags` precisa descontar esse viés para finalizadores (TODO de lab).
- 🔵 **Cluster defensivo/EARTH fraco (~0,37–0,42)** — Granite Pactbearer, Mossback Brute, Pele de Pedra, Fortificação Rúnica. **Stat-bump moveu só +0,02** no lab → **a fraqueza é de DESIGN, não de números**: numa corrida a 0 HP não há payoff para defender. Buffs foram revertidos (contradiziam decisões deliberadas do v69 e não funcionavam). **Fix real = win-condition/payoff defensivo** (ver "Profundidade").

### Casual fácil demais — e o motivo é AI, não número
O jogador **casual ganha 0,72** enquanto o otimizado ganha **0,49**. O pior jogador ganhando mais = **o bot perde para agressão ingênua**: ele sobrevaloriza leitura defensiva/tempo e é atropelado por "invoca corpo + bate na cara". **Não é um knob de dificuldade** — é heurística do bot (`rebirth_bot.py`) que precisa aprender a correr/punir board aberto. Tunar às cegas quebraria o 49/51 otimizado; fica como tarefa de AI.

### Economia / coleção
- Começa **25/100**; abrindo boosters (UI manda seed único) **completa as 100**.
- ✅ **Reveal de booster JÁ existe** (`rebirth_product.js`: cada carta vira em sequência). A observação anterior de "sem reveal" era do fluxo de **visitante** (sem login → `auth_required`).
- 🟡 **Robustez:** idempotência do booster depende do **cliente** mandar `seed` (`app.py` open booster). Deveria gerar seed no servidor (mesmo padrão do fix de `match_id`). Sem player-impact hoje (a UI manda `Date.now()`), mas é fragilidade de API.
- ⚠️ Grind longo (~233 boosters p/ a última carta), sem anti-duplicata/pity — relevante só se a coleção de teste precisar fechar rápido.
- ✅ Editor de baralho valida (`invalid_loadout`: exige 30).

### Legibilidade (10k)
- `dead_turn_rate` **0,49** (metade dos turnos sem jogada relevante) e cadeias até **25 eventos**.
- O **display** de cadeia já é amigável (sem jargão "EVENT-000001"; anuncia "sequência de N efeitos"). Capar a cadeia no **motor** (25→15) mudaria comportamento de combate — não é mexido às cegas; entra como tuning de design.

## Feito nesta passada (polish seguro)
- **Coleção conta 100 reais** (template ignora placeholders lendários) → fecha em 100/100.
- **Removido `static/js/booster_opening.js`** (código morto, órfão — o reveal real está no `rebirth_product.js`).
- **Balance:** confirmado que **nenhuma carta precisa de ajuste** (macro 49/51). O "dominant" da fireball era viés de seleção — nerf testado e **revertido**.

## Deferido com justificativa (design/AI — não fix rápido)
| Item | Por que não tunar às cegas |
|---|---|
| Cluster defensivo fraco | Falta payoff de defesa; é a camada de **arquétipos/win-con** (roadmap de profundidade). |
| Bot casual fácil | Heurística de AI perde p/ agressão; mexer arrisca o 49/51 — precisa de trabalho de AI medido. |
| `dead_turn_rate` 0,49 / cadeia 25 | Comportamento do motor; tuning de design, com telemetria humana. |
| Profundidade (stack/resposta, 2º recurso, arquétipos) | Feature de semanas — é o roadmap "partidas complexas", não um ajuste. |

> Princípio mantido (CLAUDE.md / filosofia de balance): mudanças grandes de
> balance/AI só com telemetria humana; o lab serve de regressão, não de verdade final.
