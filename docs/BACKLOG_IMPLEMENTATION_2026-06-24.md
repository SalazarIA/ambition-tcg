# Ambitionz Rebirth — Implementação do backlog P1–P3 (sessão autônoma)

**Data:** 2026-06-24
**Branch:** `feat/backlog-atratividade` (PR para revisão — sem deploy automático)
**Cache-bust:** `v115_PROFILE_AVATARS` → **`v116_PROFILE_PICKER`** (4 pontos)
**Suíte rápida:** verde — **1448 passed, 5 skipped** (antes e depois)

Verificação: Playwright sem `force` salvo onde houve animação contínua (pulso do
retrato), leitura de screenshots (padrão "olhos-de-jogador"), 1900×980 e 1440×900,
service worker bloqueado. **0 erros de console/página** nas telas tocadas.

---

## Resumo honesto

Ao implementar o backlog, **descobri que boa parte já estava feita** — minha
revisão anterior superestimou as lacunas porque inspecionou só estados iniciais e
recortes de viewport (não páginas inteiras nem estados pós-interação). Corrijo
isso abaixo com evidências. As entregas **genuinamente novas** desta sessão são
**P2.1**, **P1.3** e **P3.2**.

---

## Entregue (novo, verificado)

### ✅ P2.1 — Polish do overlay de vitória
- Rótulos do resumo agora legíveis (eram `--rb-muted` + `--fs-3xs`): cor
  `rgba(236,222,190,.82)`, 11px, peso 600. Agora lê-se "TURNOS 9 · SEU HP 23 ·
  HP DO BOT 0 · RECOMPENSA".
- Título "Vitória/Derrota" mais presente ao assentar (`opacity 0.25 → 0.4`).
- Verificado injetando o estado de vitória e capturando. `static/css/rebirth.css`.

### ✅ P1.3 — Foto de perfil (MVP)
- Clicar no **círculo do herói** (já era o avatar desde v116) abre um overlay com
  **10 avatares-preset** (2 heróis + 8 artes de carta), em grade circular.
- A escolha **aplica na hora** no círculo da arena e **persiste** (localStorage,
  por dispositivo) — confirmado após reload.
- Reabilitei `pointer-events` no retrato do **jogador** (o emblema-link que
  roubava cliques agora é `display:none`, então é seguro) e adicionei acesso por
  teclado (`role=button`, `tabindex`, Enter/Espaço).
- `templates/rebirth.html` (overlay), `static/js/rebirth.js` (`RebirthAvatar`),
  `static/css/rebirth.css` (grade).
- **Fase 2 (decisão de produto):** persistência por **conta** + **upload/import**
  de imagem exigem coluna no schema + endpoint + storage/segurança. O modelo já
  está pronto para receber uma URL custom além dos presets.

### ✅ P3.2 — Grafo de dependências dos serviços
- `docs/REBIRTH_DEPENDENCY_GRAPH.md`: camadas, **DAG sem ciclos no load**, e a
  razão de cada **import lazy** (quebra-ciclos: `dispatcher`⇄`invariants/parity`,
  `state`⇄`serializers`, etc.) + regra para novos imports. Gerado por análise AST.

---

## Já existia (correção da revisão anterior — não reconstruí)

### ✔️ P1.1 — Grade de artes na Coleção (JÁ IMPLEMENTADA)
A coleção **já renderiza grade de artes** (`<img src="{{ card.art }}">`,
`templates/rebirth_product.html` linhas ~349–394; `attach_art_profile` dá
`static/img/cards/baralho/N.webp`). Evidência: a página tem **164 imagens / 4
prateleiras** (ex.: "NÚCLEO DO BARALHO" com cartas full-art). Minha screenshot
anterior era só-viewport e cortou a grade abaixo da dobra.
→ Polish possível (ver Pendências): silhuetas/versos nas seções **bloqueadas**
(evoluções/lendárias) que hoje são vazios escuros.

### ✔️ P1.2 — Abertura de booster animada (JÁ IMPLEMENTADA)
O fluxo já tem **revelação carta-a-carta escalonada** (`static/js/rebirth_product.js`:
`--reveal-delay = index*120ms`, classe `rb-booster-reveal`) + classes de
**raridade** por carta (`is-<rarity>`). Só aparece **após** clicar "abrir booster"
(por isso a screenshot do estado inicial parecia estática).
→ Polish possível: "leque de pacotes" antes da abertura (flourish menor).

### ✔️ P2.2 — Mapa de campanha (JÁ É UM PATH, não lista crua)
`templates/rebirth_campaign.html` já usa `.rb-campaign-path` com `.rb-campaign-node`
+ `.rb-campaign-silhouette`, `.rb-campaign-glyph`, selo de vitória e cadeado por
status (cleared/next/locked).
→ Polish possível: linha conectora explícita entre nós para leitura de "jornada".

---

## Pendências (recomendações, com escopo)

- **P2.3 — Telas-vitrine menos vazias:** preencher seções bloqueadas da Coleção
  com silhuetas/versos; "leque de pacotes" na Loja; linha conectora na Campanha;
  reduzir espaço morto em landing/perfil. (Visual, baixo risco, iterável.)
- **P1.3 fase 2 — Conta + upload:** schema (coluna `avatar`) + endpoint
  `POST /api/rebirth/profile` + storage de upload + validação. Exige decisão de
  produto (onde guardar imagens; limites; moderação).
- **P3.1 — Concluir limpeza de tooling:** o PR de revisão removeu 33 dev-tools
  mortos; falta revisar/atualizar `tools/playability_audit.py` (assume assets/rotas
  da arena antiga) e reescrever auditores úteis sobre `rebirth_*`.
- **P3.3 — Split de `rebirth_persistence`/`rebirth_engine`:** explicitamente
  adiado (risco > ganho hoje).

---

## Como revisar / publicar
- Este PR (`feat/backlog-atratividade`) traz P2.1 + P1.3 + P3.2 + cache-bust.
- **Merge dispara deploy** (Render, de `main`). O bump `v116_PROFILE_PICKER`
  garante que CSS/JS/template novos cheguem ao jogador (invalida o cache do SW).
- Após o merge, a foto de perfil aparece ao clicar no círculo do herói na arena.
