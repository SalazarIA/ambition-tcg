# Ambitionz Rebirth — Fechamento do backlog P2/P3 (sessão autônoma)

**Data:** 2026-06-24
**Branch:** `feat/p2-p3-finish` → merge em `main` (deploy)
**Cache-bust:** `v116_PROFILE_PICKER` → **`v117_SHOWCASE_POLISH`** (4 pontos)
**Suíte rápida:** verde — **1448 passed, 5 skipped**
Verificação: Playwright (1440×900), leitura de screenshots, server local 8123.

Continuação de `BACKLOG_IMPLEMENTATION_2026-06-24.md`. Aqui finalizo P2 e P3.

## Entregue nesta etapa (verificado)

### ✅ P2.2 — Linha conectora da campanha
As silhuetas dos nós agora são ligadas por uma **linha vertical dourada** (jornada),
desenhada atrás das silhuetas (z entre o fundo do card e a silhueta) — robusta
porque a coluna da silhueta tem largura fixa (centro ~68px). Desktop (`min-width:760px`).
`static/css/rebirth.css`.

### ✅ P2.3 — Leque de pacotes na Loja
O herói do booster ("Pacote de 5 cartas") era um único verso com espaço morto.
Agora há um **leque de 3 pacotes** (dois pseudo-pacotes angulados atrás do
principal) — mais atrativo e preenche o vão, mantendo a identidade dark+gold.
`static/css/rebirth.css`.

### ✅ P3.1 — `playability_audit.py` reescrito sobre `rebirth_*`
A versão antiga checava a arena retirada (`arena_clean_v48.*`, `arena_sound.js`,
`/api/retention/event`, `style.css`) e falhava/crashava por engano. Reescrito para
validar **rotas e assets reais** (`/`, `/rebirth`, `/rebirth/shop|collection|deck-builder|
campaign|profile|progression`, SW, manifest) + um contrato leve da arena (inclui o
marcador do novo `#rebirth-avatar-overlay`). **RESULT=PASS.** `tools/playability_audit.py`.

## Status do restante

- **P2.3 (resto):** landing/perfil e estados-vazios da loja ("cartas reveladas",
  "mercado: nenhuma oferta") são funcionais; deixar mais cheios é **design pass**
  subjetivo — recomendo fazer com o seu olho, não às cegas. Não forcei pra não
  arriscar piorar telas que já estão on-brand.
- **P3.1 (resto):** ainda há ~11 dev-tools que citam a arena antiga em strings
  (não crasham; fora da CI): `reward_profile_audit`, `arena_sound_vfx_audit`,
  `arena_sync_audit`, `audit_files`, `fix_beta_core_v111`, `arena_visual_feedback_audit`,
  `qa/qa_ux_review`, `qa/qa_ascension_frontend_contract`, `qa/qa_routes_flow`,
  `qa/qa_production_flow`. Recomendo uma **limpeza revisada** (triagem fix/retire)
  em PR próprio — mass-delete não supervisionado é arriscado.
- **P3.2 — grafo de dependências:** entregue na etapa anterior (`docs/REBIRTH_DEPENDENCY_GRAPH.md`).
- **P3.3 — split de `rebirth_persistence`/`rebirth_engine`:** **não feito por design** —
  você mesmo marcou "não antes — risco > ganho hoje"; é refactor grande, impróprio
  para rodar não supervisionado com auto-deploy. Fica para um PR dedicado e revisado.

## Resumo do backlog inteiro
P1.1 ✔️ já existia · P1.2 ✔️ já existia · P1.3 ✅ feito (foto de perfil) ·
P2.1 ✅ · P2.2 ✅ · P2.3 ✅ (loja; resto = design pass) ·
P3.1 ✅ (playability_audit; resto = limpeza revisada) · P3.2 ✅ · P3.3 ⏸️ adiado por decisão.
