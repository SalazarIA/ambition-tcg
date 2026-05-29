#!/usr/bin/env python3
"""Generate the unified Ambitionz Rebirth production audit PDF.

Merges two independent QA passes (Claude guest-API pass + Codex authenticated
pass), cross-verified against source code, into a single studio-grade report.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, KeepTogether,
)

OUT = "docs/AMBITIONZ_PRODUCTION_AUDIT.pdf"

# Palette — game identity (gold on dark) + severity scale
INK = colors.HexColor("#1a1d23")
GOLD = colors.HexColor("#f4ad26")
GOLD_DK = colors.HexColor("#b06813")
PANEL = colors.HexColor("#0e1115")
MUTED = colors.HexColor("#6b6b6b")
LINE = colors.HexColor("#d8d8d2")
CRIT = colors.HexColor("#d64545")
HIGH = colors.HexColor("#e8833a")
MED = colors.HexColor("#c9a227")
LOW = colors.HexColor("#4a9d5b")
OK = colors.HexColor("#2f8f4e")
WHITE = colors.white

styles = getSampleStyleSheet()


def S(name, **kw):
    base = kw.pop("parent", styles["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


body = S("body", fontName="Helvetica", fontSize=9.5, leading=14, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6)
body_l = S("body_l", parent=body, alignment=TA_LEFT)
h1 = S("h1", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=INK, spaceBefore=14, spaceAfter=8)
h2 = S("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=GOLD_DK, spaceBefore=12, spaceAfter=5)
h3 = S("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=INK, spaceBefore=8, spaceAfter=3)
small = S("small", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED)
mono = S("mono", fontName="Courier", fontSize=8, leading=11, textColor=INK)
cell = S("cell", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=INK)
cell_b = S("cell_b", parent=cell, fontName="Helvetica-Bold")
cell_w = S("cell_w", parent=cell, textColor=WHITE, fontName="Helvetica-Bold")
cover_title = S("cover_title", fontName="Helvetica-Bold", fontSize=34, leading=38, textColor=INK)
cover_sub = S("cover_sub", fontName="Helvetica", fontSize=13, leading=18, textColor=GOLD_DK)


def chip(text, color):
    t = Table([[Paragraph(f"<b>{text}</b>", cell_w)]], colWidths=[22*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    return t


def rule(color=LINE, w=0.8):
    return HRFlowable(width="100%", thickness=w, color=color, spaceBefore=4, spaceAfter=8)


story = []

# ---------- COVER ----------
story.append(Spacer(1, 40*mm))
band = Table([[Paragraph("AMBITIONZ REBIRTH", S("band", fontName="Helvetica-Bold", fontSize=12, textColor=GOLD, leading=14))]], colWidths=[170*mm])
band.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), INK),
    ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))
story.append(band)
story.append(Spacer(1, 8*mm))
story.append(Paragraph("Auditoria Unificada de Produção", cover_title))
story.append(Spacer(1, 3*mm))
story.append(Paragraph("QA Sênior · Game Design · Product · Engine — análise brutal", cover_sub))
story.append(Spacer(1, 12*mm))
story.append(rule(GOLD, 1.5))
meta = [
    ["Data", "2026-05-28"],
    ["Ambiente", "https://ambitionzgame.com (produção real)"],
    ["Build", "main @ ff5b1ca / e8924da"],
    ["Passagens de QA", "Claude (guest via API) + Codex (autenticado) — cruzadas com código-fonte"],
    ["Cobertura", "10 batalhas guest + 10 batalhas autenticadas + campanha completa + todas as rotas"],
    ["Suíte", "1206 fast / 19 e2e / 5 JS asserts — 0 fail"],
]
mt = Table(meta, colWidths=[42*mm, 128*mm])
mt.setStyle(TableStyle([
    ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
    ("FONT", (1, 0), (1, -1), "Helvetica", 9),
    ("TEXTCOLOR", (0, 0), (0, -1), GOLD_DK),
    ("TEXTCOLOR", (1, 0), (1, -1), INK),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
]))
story.append(mt)
story.append(Spacer(1, 10*mm))
verdict = Table([[Paragraph("<b>VEREDITO:</b> Fundação madura, identidade visual forte. <b>NÃO está pronto para mercado global</b> — 2 bugs críticos de integridade de estado (guest) + dificuldade em penhasco + retenção rasa. Go para evolução; No-go para abertura pública até resolver os críticos.", S("v", fontName="Helvetica", fontSize=10, leading=15, textColor=WHITE))]], colWidths=[170*mm])
verdict.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), CRIT),
    ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ("TOPPADDING", (0, 0), (-1, -1), 10),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
]))
story.append(verdict)
story.append(PageBreak())

# ---------- SUMÁRIO EXECUTIVO ----------
story.append(Paragraph("Sumário Executivo", h1))
story.append(rule())
story.append(Paragraph(
    "Este relatório funde duas auditorias independentes de produção. A passagem <b>Claude</b> dirigiu 10 batalhas "
    "completas como <b>convidado</b> pela API HTTP real (sem conta, por conformidade de segurança), com edge-probes "
    "deliberados. A passagem <b>Codex</b> criou conta, jogou a Arena autenticada, rodou 10 batalhas, abriu booster, "
    "completou a campanha inteira e revisou todas as telas autenticadas. Cada achado do Codex foi <b>verificado contra "
    "o código-fonte</b> antes de entrar aqui — 8 de 9 confirmados, 1 plausível.", body))
story.append(Paragraph(
    "A síntese revela o que <b>nenhuma</b> passagem isolada viu: o convidado naïve do Claude venceu apenas "
    "<b>2 de 10</b> contra o muro defensive; o Codex autenticado, jogando com estratégia (evoluir, maior score, menor "
    "guarda), venceu <b>10 de 10</b> — inclusive todos os 10 nós da campanha na primeira tentativa. <b>A dificuldade é "
    "um penhasco, não uma curva:</b> button-mashers apanham, jogadores competentes atropelam, e não existe meio-termo "
    "satisfatório.", body))

story.append(Paragraph("Os dois bloqueadores de lançamento", h2))
crit_tbl = [
    [Paragraph("<b>#</b>", cell_w), Paragraph("<b>Bloqueador crítico</b>", cell_w), Paragraph("<b>Fonte</b>", cell_w)],
    [Paragraph("C1", cell_b), Paragraph("Todo match de convidado compartilha o mesmo <font face='Courier'>match_id rebirth-963745ae6ffc</font>. Dois convidados simultâneos sobrescrevem a partida um do outro e veem o tabuleiro alheio — corrupção de estado + vazamento entre jogadores.", cell), Paragraph("Claude", cell)],
    [Paragraph("C2", cell_b), Paragraph("Convidado enfrenta apenas o perfil <font face='Courier'>defensive</font>, sempre. aggressive/opportunist nunca aparecem. Mata variedade na janela mais frágil de retenção.", cell), Paragraph("Claude", cell)],
    [Paragraph("C3", cell_b), Paragraph("Dificuldade em penhasco: campanha escala HP (18→50), não competência da AI. 10/10 nós vencidos 1ª tentativa com HP cheio, incluindo o boss final.", cell), Paragraph("Codex + síntese", cell)],
]
t = Table(crit_tbl, colWidths=[12*mm, 130*mm, 28*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), CRIT),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#fbeaea"), colors.HexColor("#f7dede")]),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e0b4b4")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(PageBreak())

# ---------- METODOLOGIA ----------
story.append(Paragraph("Metodologia & Cross-Verificação", h1))
story.append(rule())
story.append(Paragraph(
    "Cada achado do Codex (que testou os fluxos autenticados inacessíveis à passagem Claude) foi confirmado ou "
    "refutado lendo o código-fonte responsável. Resultado abaixo.", body))

verif = [
    [Paragraph("<b>Claim do Codex</b>", cell_w), Paragraph("<b>Status</b>", cell_w), Paragraph("<b>Evidência no código</b>", cell_w)],
    ["Campanha sem dificuldade real (HP escala, AI não)", "CONFIRMADO", "bot_hp 18→50 com mesmo perfil de bot; simulação reproduz estrutura"],
    ["CTA da campanha induz replay do nó vencido", "CONFIRMADO", "campaign_payload renderiza nós em ordem; vencido mantém CTA, sem foco no próximo"],
    ["Estado visual inconsistente após resgate diário", "CONFIRMADO", "rebirth_product.js:628 só re-renderiza dashboard, navbar XP é outra fonte"],
    ["IDs internos vazam em telas públicas", "CONFIRMADO", "history_payload passa ledger cru (rebirth_product.py:564)"],
    ["Coleção renderiza magia/armadilha como monstro", "CONFIRMADO", "card_081 SPELL atk=0/grd=0; template renderiza ATK/GRD incondicional + ability_name cru"],
    ["Arena mistura estado jogável com resultado antigo", "CONFIRMADO", "alinha com painel de resultado denso (Claude §1.3)"],
    ["Economia/XP inflada (nível 32 rápido)", "CONFIRMADO", "record_clash_result: 25 XP por clash, dispara por clash não por partida"],
    ["Copy PT-BR sem acentos", "CONFIRMADO", "rebirth_campaign.py: Acolito, Venca, Guardiao, vitoria, Mare..."],
    ["Booster reveal corta a 5ª carta", "PLAUSÍVEL", "observação ao vivo 1280x720; não reproduzido headless"],
]
rows_style = [
    ("BACKGROUND", (0, 0), (-1, 0), INK),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
    ("FONT", (1, 1), (1, -1), "Helvetica-Bold", 8),
]
for i in range(1, len(verif)):
    status = verif[i][1]
    col = OK if status == "CONFIRMADO" else MED
    rows_style.append(("TEXTCOLOR", (1, i), (1, i), col))
t = Table(verif, colWidths=[62*mm, 26*mm, 82*mm])
t.setStyle(TableStyle(rows_style))
story.append(t)
story.append(Spacer(1, 4*mm))
story.append(Paragraph("Taxa de confirmação: 8/9 confirmados, 1 plausível. A passagem Codex foi sólida e tecnicamente confiável.", small))
story.append(PageBreak())


def finding(num, sev, sev_color, title, items):
    block = []
    head = Table([[chip(sev, sev_color), Paragraph(f"<b>{num}. {title}</b>", S("ft", fontName="Helvetica-Bold", fontSize=10.5, textColor=INK, leading=14))]],
                 colWidths=[26*mm, 144*mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    block.append(head)
    for label, text in items:
        block.append(Paragraph(f"<b>{label}:</b> {text}", body_l))
    block.append(Spacer(1, 3*mm))
    return KeepTogether(block)


# ---------- 1. UX ----------
story.append(Paragraph("1. Problemas de UX", h1))
story.append(rule())
story.append(finding("1.1", "ALTO", HIGH, "Onboarding sem variedade nem curva", [
    ("Repro", "Iniciar Arena como convidado N vezes — sempre defensive, mesmo deck."),
    ("Impacto", "Primeira impressão monótona; os perfis mais interessantes nunca aparecem."),
    ("Dono", "rebirth_state.py:171 (seed fixo) + rebirth_bot.py:540 (choose_personality)."),
]))
story.append(finding("1.2", "ALTO", HIGH, "Latência de input corrói o game feel", [
    ("Medição", "p50=403ms, p90=497ms, p99=818ms por ação (produção real, ~760 ações)."),
    ("Impacto", "Turno completo = ~1.2s parado; 23 turnos = ~28s de espera de rede por partida."),
    ("Dono", "Render single-worker + public_state carrega heuristic_vector/art_*/silhouette por carta em cada resposta."),
]))
story.append(finding("1.3", "MÉDIO", MED, "Painel de resultado com 12 sinais simultâneos", [
    ("Detalhe", "PRIORIDADE / CADEIA EVENT-xxxxxx / JANELA / LINHA DEFENSIVA / SETUP / CAMPO / MÃO INIMIGA competem com o headline."),
    ("Codex", "Confirmou: fase PRINCIPAL exibia 'DANO RESOLVIDO' antigo — estado atual e feedback anterior não separados."),
    ("Fix", "Hierarquia: resultado → delta HP/guarda → causa → detalhes em expander. Esconder jargão 'CADEIA EVENT'."),
]))
story.append(finding("1.4", "MÉDIO", MED, "CTA da campanha induz replay do nó já vencido", [
    ("Repro (Codex)", "Após vencer node_01, ele continua no topo com 'Duelar'; próximo nó fica abaixo. Repetiu o nó 01 dez vezes."),
    ("Fix", "Nó vencido → 'Rejogar'; próximo nó available recebe foco/CTA primário."),
]))
story.append(finding("1.5", "BAIXO", LOW, "Estados vazios e mensagens de erro estão limpos", [
    ("Positivo", "Coleção/Loja/Recompensas como visitante mostram CTA claro. Edge-probes retornam mensagens semânticas."),
]))
story.append(PageBreak())

# ---------- 2. GAMEPLAY ----------
story.append(Paragraph("2. Problemas de Gameplay", h1))
story.append(rule())
story.append(finding("2.1", "CRÍTICO", CRIT, "Dificuldade em penhasco (síntese das duas passagens)", [
    ("Dado", "Guest naïve (Claude): 2/10 vitórias vs defensive. Autenticado smart (Codex): 10/10 + campanha 10/10 1ª tentativa."),
    ("Diagnóstico", "Não há curva: iniciante apanha de um muro, competente atropela. A campanha escala HP (18→50), não AI."),
    ("Dono", "rebirth_bot.py (AI/targeting), rebirth_campaign.py (tuning), deck inicial."),
]))
story.append(finding("2.2", "ALTO", HIGH, "Pacing longo confirmado em produção", [
    ("Dado", "avg 23.2 turnos (real, não simulado). Com a latência, partida arrasta."),
]))
story.append(finding("2.3", "ALTO", HIGH, "Economia/XP inflada", [
    ("Repro (Codex)", "10 batalhas + campanha → nível 32. Muitos lançamentos 'xp +25 match_clash' por partida."),
    ("Causa", "record_clash_result (persistence.py:1958): 25 XP + 75 vitória, disparado por CLASH, não por partida. ~20 clashes/match."),
    ("Fix", "Decidir granularidade: recompensar por partida, ou capar XP/clash."),
]))
story.append(finding("2.4", "MÉDIO", MED, "Decisões de baixo impacto + sem recompensa emocional", [
    ("Detalhe", "Fusão/traps raramente disparam no fluxo guest. Loop invocar→atacar→passar repetitivo. Vitória nº8 sente igual à nº1."),
]))
story.append(finding("2.5", "MÉDIO", MED, "Cartas problemáticas (simulação, validar c/ telemetria)", [
    ("Dado", "card_006 Scorchscale Imp dominante (WR 0.71); 6 low-impact; 3 dead-hand; earth_counter WR 0.02 em 633 plays."),
]))
story.append(PageBreak())

# ---------- 3. VISUAL ----------
story.append(Paragraph("3. Problemas Visuais", h1))
story.append(rule())
story.append(finding("3.1", "ALTO", HIGH, "Badge 'BEST PLAY' sobrepõe o título da carta", [
    ("Repro", "Primeira carta recomendada da mão. Zoom confirma 'CINDER LYN▮ST PLAY' ilegível."),
    ("Dono", "rebirth.css:7913 — .rb-recommendation-badge {top:5px;right:5px} invade o título no mini-card estreito."),
]))
story.append(finding("3.2", "ALTO", HIGH, "Coleção renderiza magia/armadilha como monstro", [
    ("Repro (Codex)", "Recarga Arcana aparece como '0 ATK / 0 GRD - DrawTwoCards'."),
    ("Causa", "Template (rebirth_product.html:289/326/344) renderiza ATK/GRD incondicional; ability_name é técnico em inglês (DrawTwoCards)."),
    ("Fix", "Diferenciar card_type no template; localizar ability_name."),
]))
story.append(finding("3.3", "MÉDIO", MED, "Cockpit mobile denso (8 elementos no 1º viewport)", [
    ("Detalhe", "Nav + carteira + XP + login + HUD + zona bot competem antes da mão. Padrão mobile-native pede nav em hamburger."),
]))
story.append(finding("3.4", "MÉDIO", MED, "'PROTEGIDO NO TURNO 1' em slots vazios do bot", [
    ("Detalhe", "Label de proteção aparece em slots sem carta — confunde o que está protegido."),
]))
story.append(finding("3.5", "MÉDIO", MED, "Débito de arte: 20/103 cartas com arte bespoke", [
    ("Detalhe", "static/assets/rebirth/cards/ tem 20 arquivos. 83 cartas usam fallback. Coleção curada camufla, não resolve."),
]))
story.append(finding("3.6", "BAIXO", LOW, "Identidade visual é consistente e forte (positivo)", [
    ("Positivo", "Gold-on-dark coerente nas 6 rotas. Card panels uniformes. O jogo NÃO parece genérico esteticamente."),
]))
story.append(PageBreak())

# ---------- 4. TÉCNICO ----------
story.append(Paragraph("4. Problemas Técnicos", h1))
story.append(rule())
story.append(finding("4.1", "CRÍTICO", CRIT, "Colisão de match_id de convidado", [
    ("Repro", "2 sessões guest (cookies separados) → match_id idêntico rebirth-963745ae6ffc."),
    ("Causa", "rebirth_state.py:33 _match_id(None) constante; MATCH_STORE.save usa match_id como chave."),
    ("Impacto", "State collision + cross-player leak. O bug técnico mais grave hoje."),
    ("Fix", "Seed único por match guest (secrets.token_hex). +teste de 2 guests concorrentes. Resolve C1 e C2 juntos."),
]))
story.append(finding("4.2", "CRÍTICO", CRIT, "Single-worker é teto rígido", [
    ("Detalhe", "render.yaml: gunicorn -w 1. MATCH_STORE e MATCH_TELEMETRY_CLOCKS são dicts em memória. -w 2 quebra continuidade."),
    ("Fix", "Extrair match store para backend compartilhado (Redis/Postgres-rehydrate)."),
]))
story.append(finding("4.3", "ALTO", HIGH, "public_state carrega payload pesado por carta", [
    ("Detalhe", "Cada carta serializa heuristic_vector/art_*/silhouette/palette/flavor em cada resposta. Contribui à latência §1.2."),
]))
story.append(finding("4.4", "MÉDIO", MED, "Update parcial de XP após resgate diário", [
    ("Repro (Codex)", "Navbar foi a 5200/5500, card 'Perfil de progressão' ficou 5175/5500."),
    ("Causa", "rebirth_product.js:628 só re-renderiza [data-rebirth-progression-dashboard]; navbar XP é outra fonte não sincronizada."),
]))
story.append(finding("4.5", "MÉDIO", MED, "Defesa anti-injeção é denylist, não allowlist", [
    ("Detalhe", "app.py:586 só rejeita {exhausted,has_attacked,has_acted}. {damage,winner} passou (HTTP 200, ignorado pela engine — não é exploit vivo). Allowlist é o padrão robusto."),
]))
story.append(finding("4.6", "BAIXO", LOW, "Validação de input + determinismo sólidos (positivo)", [
    ("Positivo", "Edge cases → invalid_attacker/invalid_card/missing_match/csrf_required. 0 erros 500 em ~760 ações. canonical_state_hash + replay + parity production-grade."),
]))
story.append(PageBreak())

# ---------- 5. ARQUITETURA ----------
story.append(Paragraph("5. Problemas de Arquitetura", h1))
story.append(rule())
story.append(finding("5.1", "MÉDIO", MED, "~6000 LOC de código zumbi + 14 MB de backups", [
    ("Detalhe", "battle_engine_v2 (2326), card_effect_resolver (774), arena_*/ascension_* órfãos, backups/ 14MB, tests/legacy_disabled/."),
    ("Impacto", "Confunde devs novos, infla superfície de busca."),
]))
story.append(finding("5.2", "MÉDIO", MED, "God-objects emergindo", [
    ("Detalhe", "persistence.py 2651 LOC/70 métodos; engine resolve_turn 270 LOC, _apply_trap_effect 210 LOC; rebirth.js 3259 LOC; app.py 80 rotas."),
    ("Fix", "Split por domínio; quebrar funções gigantes; Blueprints; modularizar JS com frontend contract test como trava."),
]))
story.append(finding("5.3", "MÉDIO", MED, "IDs internos vazam pra UI (acoplamento payload↔view)", [
    ("Repro (Codex)", "Recompensas/Perfil/Histórico exibem card:card_040, booster_card, match_clash, hashes de match."),
    ("Causa", "history_payload passa ledger cru (rebirth_product.py:564). Falta camada de apresentação que traduza ledger→humano."),
]))
story.append(finding("5.4", "MÉDIO", MED, "Acoplamento seed → match_id → personality", [
    ("Detalhe", "Um seed=None propaga pra 3 comportamentos e quebra os 3 juntos. Fontes de entropia deveriam ser independentes."),
]))
story.append(finding("5.5", "BAIXO", LOW, "Separação contrato/regra/transporte correta (positivo)", [
    ("Positivo", "dispatcher → engine → serializer. Ativo arquitetural a preservar."),
]))
story.append(PageBreak())

# ---------- 6. SENSAÇÃO GERAL ----------
story.append(Paragraph("6. Sensação Geral do Produto", h1))
story.append(rule())
sens = [
    [Paragraph("<b>Pergunta</b>", cell_w), Paragraph("<b>Resposta brutal</b>", cell_w)],
    ["Parece divertido?", "Parcialmente. Combate tem ossatura boa, mas guest enfrenta muro repetitivo com 1.2s/turno de espera."],
    ["Parece moderno?", "Esteticamente sim. Em responsividade de input, não — latência mata o 'snappy'."],
    ["Parece profissional?", "Visualmente sim. Sob o capô, colisão de match_id é amadora pra um produto 'pronto'."],
    ["Parece genérico?", "NÃO. Identidade visual distinta e premium é o maior trunfo."],
    ["Jogador entende o objetivo?", "Sim ('zere o HP do bot'). Mecânicas secundárias (fusão/traps/chains) não."],
    ["Existe retenção?", "Frágil. Sem loop diário com payoff, sem variedade de bot, sem curva. Campanha é o único gancho e exige conta."],
    ["Identidade forte?", "Visual sim. Mecânica/narrativa não — bots são perfis, não rivais."],
    ["Pronto pra mercado global?", "NÃO. Colisão guest + single-worker + latência + débito de arte + retenção rasa."],
    ["Principal fraqueza hoje?", "Colisão de match_id de convidado — corrompe partidas concorrentes e vaza estado."],
    ["O que destruiria retenção?", "2 convidados colidindo numa demo viral; ou novato perdendo 8/10 contra o mesmo muro."],
    ["O que mais afasta novatos?", "Latência de input + monotonia de adversário + parede de dificuldade na 1ª sessão."],
]
t = Table(sens, colWidths=[52*mm, 118*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), INK),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f6f6f2"), WHITE]),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 8.5),
    ("FONT", (1, 1), (1, -1), "Helvetica", 8.5),
    ("TEXTCOLOR", (0, 1), (0, -1), GOLD_DK),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(PageBreak())

# ---------- 7. PRIORIDADES ----------
story.append(Paragraph("7. Prioridades de Correção", h1))
story.append(rule())


def prio_block(label, color, rows):
    data = [[Paragraph(f"<b>{label}</b>", cell_w), ""]]
    for n, txt in rows:
        data.append([Paragraph(f"<b>{n}</b>", cell_b), Paragraph(txt, cell)])
    t = Table(data, colWidths=[10*mm, 160*mm])
    style = [
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 1), (-1, -1), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 3*mm)])


story.append(prio_block("CRÍTICO — bloqueia qualquer abertura", CRIT, [
    ("1", "Seed único por match de convidado — corrige colisão de match_id E variedade de bot de uma vez. +teste de 2 guests concorrentes."),
    ("2", "Multi-worker readiness — extrair MATCH_STORE para backend compartilhado antes de escalar workers."),
    ("3", "Curva de dificuldade — campanha/AI precisam ameaçar de verdade (escalar competência, não só HP)."),
]))
story.append(prio_block("ALTO — bloqueia retenção", HIGH, [
    ("4", "Latência de input — UI otimista + enxugar payload de public_state. Alvo: ação percebida < 100ms."),
    ("5", "Badge 'BEST PLAY' sobrepondo título (rebirth.css:7913)."),
    ("6", "Coleção: spell/trap como monstro + ability_name técnico (rebirth_product.html)."),
    ("7", "XP por clash inflado — decidir granularidade da recompensa (persistence.py:1958)."),
    ("8", "Cockpit mobile denso."),
]))
story.append(prio_block("MÉDIO — qualidade de produto", MED, [
    ("9", "Hierarquizar painel de resultado; esconder jargão CADEIA EVENT; separar resultado antigo do estado atual."),
    ("10", "CTA da campanha: foco no próximo nó, 'Rejogar' no vencido."),
    ("11", "Update parcial de XP no resgate diário (sincronizar navbar + card)."),
    ("12", "IDs internos vazando em Recompensas/Perfil/Histórico — camada de apresentação do ledger."),
    ("13", "Acentos PT-BR em nomes de campanha + ability_name."),
    ("14", "Débito de arte 20→52 cartas."),
    ("15", "Allowlist anti-injeção; label 'PROTEGIDO' em slot vazio; booster 5ª carta."),
]))
story.append(prio_block("BAIXO — higiene técnica", LOW, [
    ("16", "Deletar ~6000 LOC zumbi + 14 MB backups."),
    ("17", "Split de god-objects (persistence, engine, rebirth.js, app.py)."),
    ("18", "Refatorar resolve_turn / _apply_trap_effect."),
]))
story.append(Spacer(1, 4*mm))
story.append(rule(GOLD, 1.2))
story.append(Paragraph(
    "<b>Go/No-Go.</b> Go para evolução total: sim. No-go para monetização ou campanha pública forte até resolver "
    "os 3 CRÍTICOS. A fundação é sólida; o que falta é profundidade e fechar a integridade de estado do convidado.",
    body))

# ---------- APÊNDICE ----------
story.append(PageBreak())
story.append(Paragraph("Apêndice — Dados Brutos", h1))
story.append(rule())
story.append(Paragraph("A. Claude — 10 batalhas guest via API de produção", h3))
raw = """finished=10/10   turns avg=23.2 (min 23, max 24)   outcomes: player=2 bot=8
todos os 10 = perfil defensive   action latency: p50=403ms p90=497ms p99=818ms max=949ms
edge cases: invalid_attacker OK | invalid_card OK | missing_match OK | csrf OK
authoritative_injection -> HTTP 200 (ignorado pela engine; denylist fragil)
harness: tools/qa/qa_production_battle_driver.py"""
for line in raw.split("\n"):
    story.append(Paragraph(line, mono))
story.append(Spacer(1, 4*mm))
story.append(Paragraph("B. Codex — passagem autenticada", h3))
raw2 = """conta criada; Arena UI 1 batalha (derrota turno 18); Arena API 10/10 vitorias
campanha 10/10 nos 1a tentativa (incl. node_10_gray_king); booster 5 cartas persistidas
colecao 35 possuidas / 33 unicas; console sem erros relevantes"""
for line in raw2.split("\n"):
    story.append(Paragraph(line, mono))
story.append(Spacer(1, 6*mm))
story.append(rule())
story.append(Paragraph("Documentos relacionados: STUDIO_MASTER_AUDIT.md · FULLSTACK_EVOLUTION_PLAN.md · PRODUCTION_QA_AUDIT_BRUTAL.md", small))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20*mm, 12*mm, "Ambitionz Rebirth — Auditoria Unificada de Produção · confidencial")
    canvas.drawRightString(190*mm, 12*mm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(20*mm, 15*mm, 190*mm, 15*mm)
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=20*mm, rightMargin=20*mm,
                        title="Ambitionz Rebirth — Auditoria Unificada de Produção", author="QA Studio Pass")
doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=footer)
print(f"PDF gerado: {OUT}")
