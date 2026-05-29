#!/usr/bin/env python3
"""Generate the Ambitionz Rebirth art direction & density audit PDF.

Studio-level art audit covering every public surface in production:
landing, arena, campaign, collection, shop, progression, profile.
Pairs visual findings with their structural causes in code (tokens,
typography, density patterns) and outputs prescriptions per page.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, KeepTogether,
)

OUT = "docs/AMBITIONZ_ART_DIRECTION_AUDIT.pdf"

# Game palette as anchor
INK = colors.HexColor("#0a0c10")
PANEL = colors.HexColor("#1a1d23")
GOLD = colors.HexColor("#f4ad26")
GOLD_DK = colors.HexColor("#b06813")
CYAN = colors.HexColor("#58d6ff")
LINE = colors.HexColor("#d8d8d2")
MUTED = colors.HexColor("#6b6b6b")
CRIT = colors.HexColor("#d64545")
HIGH = colors.HexColor("#e8833a")
MED = colors.HexColor("#c9a227")
LOW = colors.HexColor("#4a9d5b")
OK = colors.HexColor("#2f8f4e")
WHITE = colors.white
SOFTBG = colors.HexColor("#f7f6f1")

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


def chip(text, color, w=22*mm):
    t = Table([[Paragraph(f"<b>{text}</b>", cell_w)]], colWidths=[w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def rule(color=LINE, w=0.8):
    return HRFlowable(width="100%", thickness=w, color=color, spaceBefore=4, spaceAfter=8)


def section(label, sev_color, title, items):
    block = []
    head = Table(
        [[chip(label, sev_color, w=24*mm), Paragraph(f"<b>{title}</b>", S("st", fontName="Helvetica-Bold", fontSize=10.5, textColor=INK, leading=14))]],
        colWidths=[28*mm, 142*mm],
    )
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    block.append(head)
    for label_text, body_text in items:
        block.append(Paragraph(f"<b>{label_text}:</b> {body_text}", body_l))
    block.append(Spacer(1, 3*mm))
    return KeepTogether(block)


story = []

# ---------------- COVER ----------------
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
story.append(Paragraph("Direção de Arte &amp; Densidade", cover_title))
story.append(Spacer(1, 3*mm))
story.append(Paragraph("Auditoria de todas as superfícies — diagnóstico e prescrição", cover_sub))
story.append(Spacer(1, 12*mm))
story.append(rule(GOLD, 1.5))
meta = [
    ["Data", "2026-05-29"],
    ["Build em produção", "main @ 69e593e (v77_EMAIL_VERIFY-1)"],
    ["Superfícies auditadas", "/  ·  /rebirth  ·  /rebirth/campaign  ·  /rebirth/collection  ·  /rebirth/shop  ·  /rebirth/progression  ·  /rebirth/profile"],
    ["Evidência", "Capturas reais de produção + leitura de tokens, tipografia e densidade no código"],
    ["Sistema atual", "9 368 LOC CSS · 34 font-sizes únicos · 4 famílias tipográficas · 70 usos do clip-path \"rb-cut\""],
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
verdict = Table([[Paragraph(
    "<b>VEREDITO:</b> Identidade visual existe e tem mérito — gold-on-dark, tipografia romana, paleta enxuta. "
    "Mas o produto inteiro foi construído como <b>um único template repetido sete vezes</b>, sem hierarquia, "
    "sem escala tipográfica sistematizada, e com a Arena rodando entre dois extremos: tabuleiro vazio + "
    "painel lateral de debug. Para sair de \"protótipo\" para \"jogo\", a correção é estrutural — não cosmética.",
    S("v", fontName="Helvetica", fontSize=10, leading=15, textColor=WHITE))]], colWidths=[170*mm])
verdict.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), CRIT),
    ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ("TOPPADDING", (0, 0), (-1, -1), 10),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
]))
story.append(verdict)
story.append(PageBreak())

# ---------------- DIAGNÓSTICO CENTRAL ----------------
story.append(Paragraph("Diagnóstico central — três problemas estruturais", h1))
story.append(rule())
story.append(Paragraph(
    "Tudo que parece \"pequeno bug visual\" no jogo decorre de três causas estruturais. Resolver cada "
    "página individualmente sem atacar essas três só multiplica patch.", body))

diag = [
    [Paragraph("<b>#</b>", cell_w), Paragraph("<b>Problema estrutural</b>", cell_w), Paragraph("<b>Sintomas visíveis</b>", cell_w)],
    [Paragraph("D1", cell_b),
     Paragraph("Não existe <b>escala tipográfica</b>. Há 34 font-sizes únicos no CSS (de 5px a 96px). Componentes inventam tamanho por si.", cell),
     Paragraph("Hierarquia chapada; o olho não é guiado; títulos competem com sub-labels; mini-labels gold espalhados sem peso consistente.", cell)],
    [Paragraph("D2", cell_b),
     Paragraph("O mesmo <b>template é replicado em 6 rotas</b> (mini-label + título serif + subtitle + CTA pill + grade de stats). Sem hierarquia entre páginas.", cell),
     Paragraph("Coleção, Loja, Recompensas, Perfil, Campanha parecem a mesma página com texto trocado. Falta personalidade por rota.", cell)],
    [Paragraph("D3", cell_b),
     Paragraph("A <b>identidade signature</b> (corner cut \"rb-cut\") está aplicada 70× — em <i>tudo</i>. Quando todo painel tem o mesmo recorte, o recorte deixa de significar algo.", cell),
     Paragraph("Sem contraste entre painel-principal e painel-secundário; tudo lê como \"caixa\", nada lê como \"foco\".", cell)],
]
t = Table(diag, colWidths=[10*mm, 75*mm, 85*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), INK),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SOFTBG, WHITE]),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(Spacer(1, 6*mm))
story.append(Paragraph(
    "<b>A Arena tem um quarto problema, exclusivo dela:</b> tabuleiro vazio competindo com painel direito sobrecarregado. "
    "Vácuo no centro + painel-debug à direita = sensação de \"harness de engenheiro\", não jogo. É D4.", body))
story.append(PageBreak())

# ---------------- DIREÇÃO PROPOSTA ----------------
story.append(Paragraph("Direção proposta — fundação para todas as páginas", h1))
story.append(rule())
story.append(Paragraph(
    "Antes de prescrever página por página, esta é a fundação que dita todas as decisões abaixo.", body))

story.append(Paragraph("Paleta — manter, com regras", h2))
pal = [
    [Paragraph("<b>Cor</b>", cell_w), Paragraph("<b>Token</b>", cell_w), Paragraph("<b>Uso permitido</b>", cell_w)],
    ["Ink (preto profundo)", "--rb-ink #07090c", "Fundo da página. Único."],
    ["Panel", "--rb-panel rgba(14,17,21,.96)", "Caixas de conteúdo. Único."],
    ["Gold", "--rb-gold #f4ad26", "Foco do jogador, marca, CTA primário, indicador de progresso."],
    ["Cyan", "--rb-cyan #58d6ff", "Bot. Estado neutro/informativo. Stats secundários."],
    ["Red", "--rb-red #ff735f", "Dano, derrota, perigo. NUNCA decorativo."],
    ["Green", "--rb-green #78f2aa", "Vitória, status positivo, validação."],
    ["Ivory text", "--rb-text #f4f3ef", "Corpo de texto."],
    ["Muted", "--rb-muted #a9aaa8", "Subtítulos, legendas, metadados."],
]
t = Table(pal, colWidths=[40*mm, 55*mm, 75*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), INK),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SOFTBG, WHITE]),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
    ("FONT", (1, 1), (1, -1), "Courier", 8),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(Spacer(1, 2*mm))
story.append(Paragraph("<b>Regra dura:</b> nenhuma cor nova sem entrar nesta tabela. Variações são alpha (0.05/0.12/0.32/0.64) — não tons novos.", small))

story.append(Paragraph("Escala tipográfica — substituir os 34 tamanhos", h2))
story.append(Paragraph(
    "Modular scale 1.250 (\"major third\"), 8 tamanhos cobre tudo. Banir font-size literal fora desta tabela.", body))
ts = [
    [Paragraph("<b>Token</b>", cell_w), Paragraph("<b>px</b>", cell_w), Paragraph("<b>Uso</b>", cell_w)],
    ["--fs-3xs", "10", "Tags, badges, micro-rótulos UPPERCASE."],
    ["--fs-2xs", "12", "Captions, metadados, helper text."],
    ["--fs-xs", "13", "Corpo secundário em painéis densos."],
    ["--fs-sm", "15", "Corpo principal."],
    ["--fs-md", "18", "Sub-headlines, valores em destaque."],
    ["--fs-lg", "24", "H3 de cards, números pequenos de stats."],
    ["--fs-xl", "36", "H2 de seção, números grandes (HP, XP)."],
    ["--fs-display", "56", "H1 de rota, herói, identidade."],
]
t = Table(ts, colWidths=[32*mm, 18*mm, 120*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), INK),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SOFTBG, WHITE]),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("FONT", (0, 1), (0, -1), "Courier", 8),
    ("FONT", (1, 1), (1, -1), "Helvetica-Bold", 9),
    ("FONT", (2, 1), (2, -1), "Helvetica", 8.5),
    ("ALIGN", (1, 1), (1, -1), "CENTER"),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(Spacer(1, 2*mm))
story.append(Paragraph(
    "Famílias: <b>1 display serif</b> (Cinzel — já está e combina), <b>1 sans condensed</b> para mini-labels UPPERCASE "
    "(já está — Arial Narrow), <b>1 sans body</b> (NOVO — substituir Georgia/Times nos corpos de texto, "
    "que são pesados e datados em tela). Recomendação: <b>Inter</b> ou <b>system-ui</b> nativo. <b>Reduz de 4 famílias para 3.</b>", body))

story.append(Paragraph("Profundidade &amp; identidade — destacar o rb-cut, não banalizar", h2))
story.append(Paragraph(
    "Hoje o corte-octogonal está em 70 painéis. Solução: <b>3 níveis de painel</b> hierarquizados, "
    "e só o nível 1 usa o corte signature.", body))
levels = [
    [Paragraph("<b>Nível</b>", cell_w), Paragraph("<b>Borda</b>", cell_w), Paragraph("<b>Identidade</b>", cell_w), Paragraph("<b>Uso</b>", cell_w)],
    ["Hero (1)", "rb-cut + linha gold 1.5px + glow gold soft", "ALTA — assinatura.", "Card-herói (Dreadclaw na home; carta jogada em foco na arena; boss da campanha)."],
    ["Painel (2)", "Borda 1px line + cantos 4px (não octogonais)", "Média — sólido.", "Painéis de conteúdo: dashboard de stats, formas, listas."],
    ["Surface (3)", "Sem borda visível, só elevação por contraste de fundo (+5% lighten)", "Baixa — substrato.", "Slots, células de grid, fundos passivos."],
]
t = Table(levels, colWidths=[22*mm, 50*mm, 38*mm, 60*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), INK),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SOFTBG, WHITE]),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
    ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 8.5),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(Spacer(1, 2*mm))
story.append(Paragraph(
    "Resultado prático: ao olhar uma página, o jogador sabe imediatamente onde está o <b>herói</b> "
    "(a coisa importante), o <b>conteúdo</b> e o <b>substrato</b>. Hoje, tudo é \"painel\".", body))

story.append(Paragraph("Densidade — regras de respiração", h2))
story.append(Paragraph(
    "<b>R1.</b> Toda página tem um único H1 display e um único CTA primário gold. Nada mais é gold-pill.<br/>"
    "<b>R2.</b> Stats nunca em grade de 4 ou 6 mostrando todos com mesmo peso. Hierarquia: 1 stat grande, 2-3 médios, resto tabela.<br/>"
    "<b>R3.</b> Nenhuma mini-label UPPERCASE solta sem âncora visual. Mini-label sempre próxima ao seu valor, com gap fixo.<br/>"
    "<b>R4.</b> Painel só vira \"caixa com borda\" quando é um agrupamento real de informação. Lista de stats numa página não precisa ser caixa.<br/>"
    "<b>R5.</b> A Arena divide o viewport: <b>tabuleiro 75%</b>, painel lateral <b>25%</b>, max. 5 sinais simultâneos.",
    body))
story.append(PageBreak())

# ---------------- POR SUPERFÍCIE ----------------
story.append(Paragraph("Por superfície — diagnóstico e prescrição", h1))
story.append(rule())

# Landing
story.append(section("LANDING /", LOW, "Identidade premium funciona, falta sustentação", [
    ("Funciona", "Tipografia romana grande, Dreadclaw como herói, divisão hero/card limpa. É a melhor superfície hoje."),
    ("Falha", "Abaixo do hero a página vira lista de tabs (ARENA / COLEÇÃO / ECONOMIA) com mesmo peso visual — perde momentum."),
    ("Prescrição", "Hero como está. Substituir as tabs por <b>três cenas</b> com art keyframe (combate / coleção iluminada / mercado de cartas). Cada uma com 1 frase + 1 CTA. Largura cheia, scroll vertical."),
]))

# Arena
story.append(section("ARENA /rebirth", CRIT, "Vazio + debug — o pior estado visual do produto", [
    ("Funciona", "HUD topo é claro (VOCÊ / TURNO / BOT), código de cor gold/cyan funciona, slots INVOCAR têm boa afordância."),
    ("Falha 1", "<b>Vácuo preto</b> no terço esquerdo e centro. Tabuleiro deserto para um TCG."),
    ("Falha 2", "<b>Sobreposição de carta</b> na zona do bot — o focus card monta por cima do slot."),
    ("Falha 3", "<b>Texto truncado</b> em todas as cartas em campo (\"MISTCAL...\", \"M... Recu PV...\"). Sem leitura = sem jogo."),
    ("Falha 4", "Painel direito é <b>analista pago</b>: CADEIA ATIVA · N EFEITOS, LINHA DE SETUP, TEMPO 14, MÃO INIMIGA. 12 sinais simultâneos."),
    ("Falha 5", "Jargão de motor: \"liderar por 13 de tempo\", \"cadeia · 7 efeitos\", \"janela fechada\" — vocabulário de engine."),
    ("Prescrição A — tabuleiro", "Moldura de mesa com textura sutil substituindo o void preto. Slots maiores (cartas em campo precisam de leitura à distância). Foco em <b>3 ações por lado</b> com fôlego."),
    ("Prescrição B — painel", "<b>Modo simples por padrão:</b> headline do resultado + delta de HP + causa principal. Modo analista atrás de toggle (player sênior pede)."),
    ("Prescrição C — bug fixes", "z-index entre slot-card e focus-card; CSS overflow do mini-card pra texto completo ou tooltip; \"ZONA DO BOT\" e \"SUA ZONA\" como banners persistentes integrados, não etiquetas flutuantes."),
]))

# Campaign
story.append(section("CAMPANHA /rebirth/campaign", HIGH, "Lista de SQL, não jornada", [
    ("Funciona", "Acentos corretos (Acólito, Vença), CTA do próximo nó destacado, modifiers visíveis."),
    ("Falha", "Cada um dos 10 bosses é uma <b>linha de texto idêntica</b>. Sem arte, sem atmosfera, sem diferenciação visual entre fogo/terra/sombra/água. \"Acólito da Brasa\" e \"Rei Cinzento\" se parecem 100% pra quem não lê."),
    ("Prescrição", "Cada nó vira <b>card horizontal com silhueta do boss</b> (sequência de gradiente por elemento + ícone vetorial 64×64), nome em display, modifiers como pills tematizadas pelo elemento. Nó <i>completed</i> ganha selo gold + escala reduzida; nó <i>locked</i> grayscale + cadeado. Mantém o que existe de texto; só ganha presença visual."),
]))

# Collection
story.append(section("COLEÇÃO /rebirth/collection", MED, "Stats gigantes engolem a coleção", [
    ("Funciona", "Coleção curada (shelves temáticas) que vem depois é a melhor parte. Cards com arte real são premium."),
    ("Falha", "A primeira viewport é 4 stats gigantes (POSSUÍDAS 30 / ÚNICAS 29 / BARALHO 30 / EVOLUÇÕES 43) ocupando o espaço todo. \"Minha Coleção\" deveria mostrar CARTAS primeiro, não números."),
    ("Prescrição", "Inverter: hero compacto (título + 1 stat grande, ex. \"30 de 103 reveladas\") + barra de progresso inline. Stats individuais vão pra uma linha discreta abaixo. Imediatamente: <b>fileira de cartas mais recentes / mais usadas</b> antes de qualquer outra seção."),
]))

# Shop
story.append(section("LOJA /rebirth/shop", HIGH, "Vende como engenheiro, não como gacha", [
    ("Funciona", "Booster Rebirth (direita) com gema vermelha e \"Grátis na beta\" em gold tem peso visual real."),
    ("Falha 1", "Texto literal: <b>\"O backend sorteia 3 comuns e 2 incomuns antes da interface revelar o resultado\"</b>. Isso é fala de programador na vitrine de venda."),
    ("Falha 2", "Cinco caixinhas vazias com a palavra \"COMUM\" escrita 3 vezes é o ANTÍLOGO de um pacote de cartas. Zero antecipação."),
    ("Prescrição", "Trocar a vitrine por <b>uma única arte de booster pack</b> em primeiro plano (mesmo que stock art temporário) com glow gold + texto \"3 comuns · 2 incomuns garantidos\". Microcopy: \"Cada booster revela 5 cartas determinísticas — abertura sorteada no servidor\". Remover \"backend\" do vocabulário da vitrine."),
]))

# Progression
story.append(section("RECOMPENSAS /rebirth/progression", MED, "Stats repetidos = redundância visual", [
    ("Funciona", "Estrutura de níveis clara, CTA \"Jogar por XP\" no lugar certo."),
    ("Falha", "A página mostra a MESMA stat duas vezes em peso diferente: \"NÍVEL 1 / XP 0/500 / VITÓRIAS 0 / CLASHES 0\" no topo, e logo abaixo \"VITÓRIAS 0 / CLASHES 0 / BOOSTERS 0\" outra vez. Eco visual sem informação nova."),
    ("Prescrição", "Top da página é <b>uma barra de XP gigante</b> com a temporada (presence visual) + nível atual + próxima recompensa. Stats individuais entram como tabela compacta abaixo. Extrato fica como histórico (já está bom). Sem grades duplicadas."),
]))

# Profile
story.append(section("PERFIL /rebirth/profile", MED, "Cópia carbono do template — nenhuma personalidade", [
    ("Funciona", "Layout limpo, CTA \"Abrir Coleção\" sensato."),
    ("Falha", "É <i>idêntico</i> a Recompensas e Coleção em estrutura. Não tem identidade do jogador (avatar, frase, equipado, conquistas) — só replica a grade de stats. Pra autenticado, isso é decepcionante: a página \"sobre você\" não mostra você."),
    ("Prescrição", "Estrutura própria: <b>avatar grande (ou inicial estilizada) + nome + título de temporada</b> à esquerda; <b>3 conquistas em destaque</b> com selo; <b>carta favorita ou mais jogada</b> grande à direita; controles de conta (sair, mudar senha, email) numa seção secundária. Remover a grade de stats redundante — esse dado já vive em Recompensas."),
]))

story.append(PageBreak())

# ---------------- BUGS REPRODUZÍVEIS ----------------
story.append(Paragraph("Bugs visuais confirmados em produção", h1))
story.append(rule())
bugs = [
    [Paragraph("<b>#</b>", cell_w), Paragraph("<b>Bug</b>", cell_w), Paragraph("<b>Localização</b>", cell_w), Paragraph("<b>Sev</b>", cell_w)],
    [Paragraph("B1", cell_b), Paragraph("Focus card sobrepondo slot na zona do bot — clipa identidade da carta jogada", cell), Paragraph("Arena, zona bot esquerda", cell), Paragraph("ALTO", S("sev", textColor=HIGH, fontName="Helvetica-Bold", fontSize=8.5))],
    [Paragraph("B2", cell_b), Paragraph("Texto truncado em cartas em campo (\"MISTCAL...\", \"M... Aplic qu...\")", cell), Paragraph("Arena, todas as cartas em campo", cell), Paragraph("ALTO", S("sev", textColor=HIGH, fontName="Helvetica-Bold", fontSize=8.5))],
    [Paragraph("B3", cell_b), Paragraph("Badge BEST PLAY ainda aparenta duplicado na primeira carta da mão (verificar cache pós-v77)", cell), Paragraph("Arena, primeira carta da mão recomendada", cell), Paragraph("MÉDIO", S("sev", textColor=MED, fontName="Helvetica-Bold", fontSize=8.5))],
    [Paragraph("B4", cell_b), Paragraph("\"CADEIA ATIVA · 1 EFEITO\" mostrando antes de qualquer jogada", cell), Paragraph("Arena, painel resolution-strip", cell), Paragraph("MÉDIO", S("sev", textColor=MED, fontName="Helvetica-Bold", fontSize=8.5))],
    [Paragraph("B5", cell_b), Paragraph("\"ZONA DO BOT\" e \"SUA ZONA\" como etiquetas flutuantes, mal posicionadas", cell), Paragraph("Arena, divisores", cell), Paragraph("MÉDIO", S("sev", textColor=MED, fontName="Helvetica-Bold", fontSize=8.5))],
    [Paragraph("B6", cell_b), Paragraph("\"5 CARTAS\" label órfã abaixo da mão sem ligação visual com nada", cell), Paragraph("Arena, contador de mão", cell), Paragraph("BAIXO", S("sev", textColor=LOW, fontName="Helvetica-Bold", fontSize=8.5))],
    [Paragraph("B7", cell_b), Paragraph("Vocabulário de motor (\"backend\", \"liderar por 13 de tempo\", \"cadeia\")", cell), Paragraph("Loja + Arena", cell), Paragraph("ALTO", S("sev", textColor=HIGH, fontName="Helvetica-Bold", fontSize=8.5))],
]
t = Table(bugs, colWidths=[10*mm, 85*mm, 55*mm, 20*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), INK),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SOFTBG, WHITE]),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)

# ---------------- BACKLOG ----------------
story.append(Paragraph("Backlog priorizado", h1))
story.append(rule())


def prio(label, color, rows):
    data = [[Paragraph(f"<b>{label}</b>", cell_w), ""]]
    for n, txt in rows:
        data.append([Paragraph(f"<b>{n}</b>", cell_b), Paragraph(txt, cell)])
    t = Table(data, colWidths=[10*mm, 160*mm])
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 1), (-1, -1), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([t, Spacer(1, 3*mm)])


story.append(prio("CRÍTICO — sem isso, o resto é maquiagem", CRIT, [
    ("F1", "<b>Escala tipográfica</b> em 8 tokens (--fs-3xs..--fs-display); ban literal font-size. Substitui os 34 atuais."),
    ("F2", "<b>3 níveis de painel</b> (Hero/Painel/Surface); rb-cut só no Hero. Atualizar componentes para uma das três camadas."),
    ("F3", "<b>Arena — reset do painel direito.</b> Modo simples por padrão (headline + delta + causa). Modo analista atrás de toggle."),
    ("F4", "<b>Arena — texto integral em cartas em campo</b> (overflow + tooltip ou card maior). Sem leitura = sem jogo."),
    ("F5", "<b>Arena — moldura de mesa</b> substituindo o vácuo preto. Mesmo que sutil, dá presença ao tabuleiro."),
]))
story.append(prio("ALTO — destrava personalidade por superfície", HIGH, [
    ("F6", "<b>Campanha</b> com silhueta + cor por boss. 10 nodes deixam de ser linhas idênticas."),
    ("F7", "<b>Loja</b> com arte de booster (mesmo stock temporário) + reescrever copy sem \"backend\"."),
    ("F8", "<b>Perfil</b> com identidade própria (avatar + título + carta favorita + 3 conquistas). Remover grade de stats redundante."),
    ("F9", "Banir jargão de motor da UI: \"liderar por N de tempo\", \"cadeia · N efeitos\", \"janela fechada\" — substituir por linguagem de jogador."),
    ("F10", "Bug B1 (focus card sobrepondo slot do bot)."),
    ("F11", "Bug B7 (vocabulário backend na vitrine)."),
]))
story.append(prio("MÉDIO — polimento de leitura", MED, [
    ("F12", "Coleção: inverter prioridade (cartas antes dos stats)."),
    ("F13", "Recompensas: barra de XP gigante + remover grade duplicada."),
    ("F14", "Bug B3 (BEST PLAY badge — verificar cache pós-v77; se persistir, refinar posicionamento)."),
    ("F15", "Bug B4 (CADEIA ATIVA quando ainda não há cadeia)."),
    ("F16", "Bugs B5+B6 (labels flutuantes integrados aos contêineres)."),
]))
story.append(prio("BAIXO — higiene", LOW, [
    ("F17", "Substituir 4ª família (Georgia/Times) por system-ui/Inter em corpos de texto."),
    ("F18", "Reduzir as 9 368 linhas de CSS removendo declarações órfãs após F1+F2."),
]))

story.append(Spacer(1, 4*mm))
story.append(rule(GOLD, 1.2))
story.append(Paragraph(
    "<b>Ordem de ataque recomendada:</b> F1 + F2 primeiro (uma semana). Depois F3-F5 (Arena salva primeiro porque é a página onde o jogador passa 90% do tempo). "
    "Depois F6-F11 abrem personalidade nas outras rotas. F12-F18 são limpeza contínua. <b>Marco visual:</b> ao terminar F1-F5 o jogo deixa de parecer protótipo.",
    body))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20*mm, 12*mm, "Ambitionz Rebirth — Direção de Arte & Densidade · confidencial")
    canvas.drawRightString(190*mm, 12*mm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(20*mm, 15*mm, 190*mm, 15*mm)
    canvas.restoreState()


doc = SimpleDocTemplate(
    OUT, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=20*mm, rightMargin=20*mm,
    title="Ambitionz Rebirth — Direção de Arte & Densidade", author="Studio Art Direction Pass",
)
doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=footer)
print(f"PDF gerado: {OUT}")
