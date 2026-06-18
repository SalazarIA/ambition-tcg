#!/usr/bin/env python3
"""Build the current Ambitionz Rebirth game-status PDF report."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.utils import ImageReader


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "AMBITIONZ_RELATORIO_ANDAMENTO_GERAL_20260615.pdf"
SHOT_DIR = Path("/tmp/rebirth-visual-current")

INK = colors.HexColor("#111318")
PANEL = colors.HexColor("#20242c")
GOLD = colors.HexColor("#f4ad26")
GOLD_DARK = colors.HexColor("#9b6716")
LINE = colors.HexColor("#d9d2c3")
SOFT = colors.HexColor("#f7f3ea")
WHITE = colors.white
GREEN = colors.HexColor("#2f8f4e")
BLUE = colors.HexColor("#2e74b5")
ORANGE = colors.HexColor("#d97924")
RED = colors.HexColor("#b93d3d")
GRAY = colors.HexColor("#666666")

styles = getSampleStyleSheet()


def style(name: str, **kwargs) -> ParagraphStyle:
    base = kwargs.pop("parent", styles["Normal"])
    return ParagraphStyle(name, parent=base, **kwargs)


BODY = style("Body", fontName="Helvetica", fontSize=9.2, leading=13.2, textColor=INK, spaceAfter=5)
BODY_L = style("BodyLeft", parent=BODY, alignment=TA_LEFT)
SMALL = style("Small", fontName="Helvetica", fontSize=7.8, leading=10.5, textColor=GRAY)
CELL = style("Cell", fontName="Helvetica", fontSize=7.8, leading=10.4, textColor=INK)
CELL_B = style("CellBold", parent=CELL, fontName="Helvetica-Bold")
CELL_W = style("CellWhite", parent=CELL, fontName="Helvetica-Bold", textColor=WHITE)
H1 = style("H1", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=INK, spaceBefore=8, spaceAfter=6)
H2 = style("H2", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=GOLD_DARK, spaceBefore=7, spaceAfter=4)
H3 = style("H3", fontName="Helvetica-Bold", fontSize=10, leading=12.5, textColor=INK, spaceBefore=4, spaceAfter=2)
COVER_TITLE = style("CoverTitle", fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=INK)
COVER_SUB = style("CoverSub", fontName="Helvetica", fontSize=12.5, leading=17, textColor=GOLD_DARK)
CENTER = style("Center", parent=BODY, alignment=TA_CENTER)


def p(text: str, s: ParagraphStyle = BODY_L) -> Paragraph:
    return Paragraph(text, s)


def rule(color=LINE, thickness=0.8):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceBefore=4, spaceAfter=7)


def status_chip(text: str, color) -> Table:
    t = Table([[p(f"<b>{text}</b>", CELL_W)]], colWidths=[25 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def table(rows, widths, header=True, row_colors=True) -> Table:
    converted = []
    for row in rows:
        converted.append([item if hasattr(item, "wrap") else p(str(item), CELL) for item in row])
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), PANEL))
        commands.append(("TEXTCOLOR", (0, 0), (-1, 0), WHITE))
    if row_colors and len(rows) > 1:
        commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SOFT]))
    t.setStyle(TableStyle(commands))
    return t


def image_block(path: Path, max_w: float, max_h: float):
    reader = ImageReader(str(path))
    iw, ih = reader.getSize()
    scale = min(max_w / iw, max_h / ih)
    return Image(str(path), width=iw * scale, height=ih * scale)


def finding(title: str, tone, lines: list[tuple[str, str]]):
    block = [Table([[status_chip(title.split(" ", 1)[0], tone), p(f"<b>{title}</b>", CELL_B)]], colWidths=[28 * mm, 142 * mm])]
    block[-1].setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    for label, text in lines:
        block.append(p(f"<b>{label}:</b> {text}", BODY_L))
    block.append(Spacer(1, 2 * mm))
    return KeepTogether(block)


def build() -> None:
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Ambitionz Rebirth - Relatorio de Andamento Geral",
        author="Codex",
    )
    story = []

    # Cover
    story.append(Spacer(1, 28 * mm))
    band = Table([[p("AMBITIONZ REBIRTH", style("Band", fontName="Helvetica-Bold", fontSize=12, textColor=GOLD, leading=14))]], colWidths=[174 * mm])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(band)
    story.append(Spacer(1, 8 * mm))
    story.append(p("Relatorio de Andamento Geral do Game", COVER_TITLE))
    story.append(Spacer(1, 3 * mm))
    story.append(p("Roadmap completo, visual, engine, arquitetura, programacao, maturidade industrial e deploy web/iOS/Android", COVER_SUB))
    story.append(Spacer(1, 8 * mm))
    story.append(rule(GOLD, 1.5))
    meta = [
        ["Data da analise", "15/06/2026"],
        ["Workspace", str(ROOT)],
        ["Produto ativo", "Ambitionz Rebirth, runtime Flask/Python server-authoritative"],
        ["Base analisada", "README, docs oficiais, git, codigo, testes, screenshots Playwright, health de producao"],
        ["Veredito curto", "Fundacao forte de closed beta; ainda nao e public beta industrial/comercial ate gates externos e telemetria humana passarem."],
    ]
    story.append(table(meta, [38 * mm, 136 * mm], header=False))
    story.append(PageBreak())

    # Executive summary
    story.append(p("Resumo Executivo", H1))
    story.append(rule())
    story.append(p(
        "Ambitionz Rebirth saiu do estagio de prototipo e hoje tem uma fundacao tecnica real: engine deterministica em Python, "
        "estado autoritativo no servidor, PostgreSQL em producao, PWA, testes amplos, pipeline de conteudo, balance lab e governanca "
        "de release. O jogo ja e jogavel e coerente como closed beta interna/controlada."
    ))
    story.append(p(
        "O ponto honesto: ainda nao esta pronto para beta publica ampla nem mercado industrial/comercial. O bloqueio nao e falta de codigo "
        "basico; e falta de prova externa, telemetria humana, polimento mobile fino, modularizacao de arquivos grandes e material mobile "
        "de loja atualizado para o Rebirth atual."
    ))
    status_rows = [
        [p("<b>Eixo</b>", CELL_W), p("<b>Estado atual</b>", CELL_W), p("<b>Leitura</b>", CELL_W)],
        ["Produto jogavel", "ALTO", "Arena, campanha, colecao, shop beta, progressao, perfil, historico e suporte existem."],
        ["Engine", "ALTO", "Python-first, comandos/eventos, replay, hashes, keywords vivas, balance lab."],
        ["Visual", "BOM", "Identidade gold/dark forte; QA visual passou. Mobile ainda denso em alguns estados."],
        ["Arquitetura", "BOA", "Limites corretos, mas app.py, rebirth.js, rebirth.css e persistence ainda grandes."],
        ["Release industrial", "BLOQUEADO", "Faltam legal, backup/restore, error tracking confirmado e KPIs humanos."],
        ["Deploy web", "SAUDAVEL", "Producao respondeu ok=true, PostgreSQL schema 11, headers e Server-Timing."],
        ["Android", "PARCIAL", "Wrapper/AAB existem, mas materiais e build precisam revalidacao Rebirth."],
        ["iOS", "INICIAL", "Dependencia/script Capacitor existem; projeto ios/ nao esta versionado."],
    ]
    story.append(table(status_rows, [38 * mm, 28 * mm, 108 * mm]))
    story.append(PageBreak())

    # Time and evidence
    story.append(p("Tempo De Producao", H1))
    story.append(rule())
    story.append(p(
        "Usando 15/03/2026 como referencia de 'meados de marco', a ideia tem <b>92 dias</b> ate 15/06/2026, "
        "ou <b>13,1 semanas</b>. Considerando o primeiro commit versionado em 24/04/2026, a producao registrada em git "
        "tem <b>52 dias</b>, <b>7,4 semanas</b> e <b>502 commits</b> no historico atual."
    ))
    timeline_rows = [
        [p("<b>Marco</b>", CELL_W), p("<b>Data</b>", CELL_W), p("<b>Leitura</b>", CELL_W)],
        ["Ideia / concepcao informada", "meados de marco de 2026", "92 dias ate agora se contado de 15/03/2026."],
        ["Primeira versao beta no git", "24/04/2026", "Inicio rastreavel da producao versionada."],
        ["Rebirth Foundation v58", "23/05/2026", "PostgreSQL, mobile-first, payload budget e gates."],
        ["Studio roadmap AAA", "02/06/2026", "Fases 0-9, Python-first e gates industriais."],
        ["Player-first / perf / YGO polish", "10-11/06/2026", "Melhorias de core loop, UX real, performance e zonas de jogo."],
        ["Analise atual", "15/06/2026", "Producao viva; testes locais e E2E verdes; release gate ainda bloqueado."],
    ]
    story.append(table(timeline_rows, [45 * mm, 35 * mm, 94 * mm]))
    story.append(p("Evidencias rodadas nesta analise", H2))
    evidence_rows = [
        [p("<b>Validacao</b>", CELL_W), p("<b>Resultado</b>", CELL_W)],
        ["Py compile core", "OK"],
        ["JS check + audio dedup", "OK; audio chain dedup: 5 asserts"],
        ["Suite Rebirth fast", "1318 passed, 5 skipped, 19 deselected, 3 warnings"],
        ["E2E navigation/auth", "19 passed"],
        ["Visual screenshots", "PASS; 5 screenshots; 0 issues"],
        ["Content validator", "103 cards, 83 monsters, 10 spells, 10 traps, art coverage 1.0, 0 errors"],
        ["Balance lab 120", "Player WR 52,5%; Bot WR 47,5%; avg 9,06 turnos; 92/103 cards used"],
        ["Release readiness", "ready=false; phase reports 9/9; external 2/5; public beta 1/9"],
        ["Producao web", "ambitionzgame.com/health ok=true; PostgreSQL schema 11"],
    ]
    story.append(table(evidence_rows, [60 * mm, 114 * mm]))
    story.append(PageBreak())

    # Product state
    story.append(p("Estado Atual Do Produto", H1))
    story.append(rule())
    product_rows = [
        [p("<b>Camada</b>", CELL_W), p("<b>Como esta hoje</b>", CELL_W)],
        ["Loop central", "Duelo tatico de cartas com dois campos de tres slots, energia, summon sickness, ataque direcionado, dano direto, fadiga e fim de partida."],
        ["Conteudo", "Catalogo ativo de 103 cartas: 83 monstros, 10 magias, 10 armadilhas; 40 Common, 60 Uncommon, 3 Legendary."],
        ["Mecanicas", "Mulligan unico, evolucao de duplicatas, field fusion, traps contextuais, magias com alvo e keywords RUSH/BURST/LIFESTEAL/TAUNT/SHIELD/PIERCE/REGEN/EXECUTE."],
        ["Produto em volta", "Auth, colecao, loadout, booster beta sem pagamento, progressao, perfil, historico, ledger, campanha PvE de 10 encontros, suporte e export/delete."],
        ["Runtime ativo", "Python/Flask + PostgreSQL + vanilla HTML/CSS/JS como render/input; SocketIO/Ascension/Arena/BE2 estao aposentados."],
        ["Idioma", "UI ativa em pt-BR; contratos JSON e identificadores de engine continuam em ingles."],
    ]
    story.append(table(product_rows, [42 * mm, 132 * mm]))
    story.append(p("Pontos fortes atuais", H2))
    strengths = [
        ["Engine server-authoritative e deterministica; boa base para replay, suporte, anti-cheat futuro e async competition."],
        ["Governanca de release rara para um indie/solo: gates, phase reports, CI, audit tools, health e evidence model."],
        ["Visual tem identidade propria: gold-on-dark, arena cinematic, campanha e colecao no mesmo mundo visual."],
        ["Produto nao e so arena: ja existe onboarding, perfil, historico, colecao, suporte e economia beta."],
    ]
    for item in strengths:
        story.append(p(f"- {item[0]}"))
    story.append(PageBreak())

    # Roadmap
    story.append(p("Roadmap Completo Por Fase", H1))
    story.append(rule())
    road_rows = [
        [p("<b>Fase</b>", CELL_W), p("<b>Status</b>", CELL_W), p("<b>O que existe</b>", CELL_W), p("<b>Bloqueio / proximo passo</b>", CELL_W)],
        ["0 External Closed-Beta Gate", "Implementada localmente; bloqueada", "Legal pages, runbooks, evidence tools, CI/GitHub QA, billing off.", "Prova externa: legal, backup/restore real, Sentry/GlitchTip smoke."],
        ["1 First 10 Minutes", "Implementada localmente; bloqueada por evidencia", "Tutorial, first-session plan, recap, deck coach, booster suggestion.", "Medir tutorial >80%, first match >70%, time-to-first-turn."],
        ["2 Human Telemetry", "Infra pronta; sem amostra", "Eventos enriquecidos, public beta gate, live balance payload.", "Coletar 500+ partidas humanas e coorte com --since."],
        ["3 Modularizacao", "Nao iniciada como fase", "Alguns limites ja existem.", "Depois da telemetria: quebrar app.py, persistence, engine, JS e CSS sem mudar gameplay."],
        ["4 UX Polish", "Parcial historico; fase bloqueada", "v100-v102 trouxeram arena feel, visual unity e player-first.", "Usar drop-off/telemetria para priorizar; resolver densidade mobile."],
        ["5 Retention Systems", "Fundacao existe; fase bloqueada", "Daily/weekly quests, campanha, perfil, daily claim.", "D1 >=35%, D7 >=20%, entender o motivo de retorno."],
        ["6 Content Expansion", "Deferida", "Catalogo atual suficiente para beta learning; validator OK.", "Adicionar conteudo so com hipotese e telemetria."],
        ["7 Async Competition", "Fundacao tecnica", "Replay share e ghost payloads existem atras de API autenticada.", "Transformar em UI social so depois de core/retention saudaveis."],
        ["8 Public Beta Gate", "Bloqueada", "Avaliador final existe e e estrito.", "Passar external proof + KPIs humanos + crash/error + balance."],
        ["9 Realtime PvP / Live Ops", "Futuro", "Base deterministica ajuda.", "Precisa reconnect duravel, abuso/report, timeout, live config, rollback."],
    ]
    story.append(table(road_rows, [22 * mm, 32 * mm, 58 * mm, 62 * mm]))
    story.append(PageBreak())

    # Visual with screenshots
    story.append(p("Road Visual E UX", H1))
    story.append(rule())
    story.append(p(
        "O visual esta acima de prototipo: a arena tem mesa, moldura, cartas com personalidade, feedback de turno e uma linguagem consistente nas paginas principais. "
        "A QA visual automatizada passou sem overflow horizontal, console errors, page errors, request failures ou HTTP 500."
    ))
    if (SHOT_DIR / "arena.png").exists() and (SHOT_DIR / "mobile_arena.png").exists():
        img_table = Table(
            [[image_block(SHOT_DIR / "arena.png", 92 * mm, 52 * mm), image_block(SHOT_DIR / "mobile_arena.png", 55 * mm, 96 * mm)]],
            colWidths=[105 * mm, 62 * mm],
        )
        img_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(img_table)
        story.append(p("Esquerda: arena desktop em mulligan. Direita: arena mobile no mesmo estado.", SMALL))
    story.append(finding("FORTE Identidade visual coesa", GREEN, [
        ("Evidencia", "v100 arena feel, v101 visual unity e screenshots atuais mostram a mesma linguagem gold/dark."),
        ("Impacto", "O jogo nao parece generico; ja ha uma assinatura visual vendavel."),
    ]))
    story.append(finding("PENDENTE Densidade mobile", ORANGE, [
        ("Evidencia", "No screenshot mobile, as cartas da mao inicial ficam comprimidas, nomes truncados e badges de ATK/GUARD brigam por area."),
        ("Proximo", "Polir estado de mulligan/mobile com cards maiores, carrossel ou resumo compacto; manter toque claro."),
    ]))
    story.append(finding("PENDENTE Materiais externos defasados", ORANGE, [
        ("Evidencia", "Play Store screenshots/textos ainda mostram visual roxo antigo, 250 cards, training/deck builder; produto atual e Rebirth 103 cards."),
        ("Proximo", "Regerar assets de loja, release notes e screenshots oficiais no visual Rebirth atual."),
    ]))
    story.append(PageBreak())

    # Engine architecture programming
    story.append(p("Engine, Arquitetura E Programacao", H1))
    story.append(rule())
    engine_rows = [
        [p("<b>Eixo</b>", CELL_W), p("<b>Estado</b>", CELL_W), p("<b>Analise</b>", CELL_W)],
        ["Engine", "Forte", "Regras em Python, comandos/eventos, hashes canonicos, replay envelope, reducers e testes amplos."],
        ["Balance", "Bom laboratorio", "120 matches atuais: WR agregado saudavel. Mas balance real segue bloqueado sem 500+ partidas humanas."],
        ["Persistencia", "Boa, com divida", "PostgreSQL autoritativo para contas/historico/economia; hot cache em memoria ainda limita reconnect/escala."],
        ["Frontend", "Funcional, pesado", "JS e CSS sao render/input, nao autoridade. rebirth.js 4.712 LOC e rebirth.css 15.602 LOC pedem modularizacao."],
        ["Backend app", "Funcional, pesado", "app.py 2.553 LOC; persistence 3.214 LOC; engine 2.498 LOC. O desenho e correto, o tamanho ja cobra juros."],
        ["Seguranca", "Boa base", "CSRF cobre /api/rebirth/ e /api/labs/; auth rate-limit; headers; billing live bloqueado."],
        ["Docs", "Ricas, mas com drift", "Alguns docs/manifest ainda falam one-card, lang=en ou fluxos legados; fonte de verdade atual e Rebirth Release/Rulebook."],
    ]
    story.append(table(engine_rows, [34 * mm, 28 * mm, 112 * mm]))
    story.append(p("Arquivos grandes atuais", H2))
    loc_rows = [
        [p("<b>Arquivo</b>", CELL_W), p("<b>LOC</b>", CELL_W), p("<b>Leitura</b>", CELL_W)],
        ["static/css/rebirth.css", "15.602", "Maior risco de polish visual; modularizar por dominio visual."],
        ["static/js/rebirth.js", "4.712", "Aceitavel para closed beta; dividir API/store/render/input/motion."],
        ["services/rebirth_persistence.py", "3.214", "Separar repositorios por dominio antes de social/economia maior."],
        ["app.py", "2.553", "Migrar rotas para blueprints quando os gates permitirem."],
        ["services/rebirth_engine.py", "2.498", "Quebrar combate, spells, traps, turn lifecycle e reward builders."],
    ]
    story.append(table(loc_rows, [58 * mm, 24 * mm, 92 * mm]))
    story.append(PageBreak())

    # Industrial maturity
    story.append(p("Nivel Industrial Do Game", H1))
    story.append(rule())
    story.append(p(
        "A nivel industrial, o projeto esta acima da media de MVP: tem CI, suite grande, E2E, visual QA, health real, release readiness, content validator, "
        "balance reports e runbooks. Isso e disciplina de estudio. O que ainda falta e evidencia operacional e dados humanos suficientes para chamar de beta publica."
    ))
    maturity_rows = [
        [p("<b>Area</b>", CELL_W), p("<b>Nota qualitativa</b>", CELL_W), p("<b>Por que</b>", CELL_W)],
        ["Engenharia de gameplay", "B+/A-", "Server-authoritative e deterministico; excelente base para PvE/async."],
        ["Operacao de release", "B", "Ferramentas maduras, mas gates externos ainda nao foram provados."],
        ["UX de primeira sessao", "B-", "Melhorou muito; precisa telemetria real e ajuste mobile fino."],
        ["Arte e apresentacao", "B", "Identidade forte; assets e loja precisam alinhar com Rebirth atual."],
        ["Escala", "C+", "Single process/hot cache funciona para beta pequena; precisa durabilidade e load test para publico."],
        ["Comercial/lojas", "C", "Android parcial; iOS inicial; materiais legais/loja/privacidade precisam prova final."],
    ]
    story.append(table(maturity_rows, [38 * mm, 30 * mm, 106 * mm]))
    story.append(p("Go / No-Go", H2))
    story.append(p("<b>Go:</b> continuar closed beta controlada, QA interna, coleta de telemetria e modularizacao planejada."))
    story.append(p("<b>No-Go:</b> marketing amplo, monetizacao real, beta publica aberta ou PvP realtime antes dos gates externos, telemetria humana e reconnect/ops amadurecerem."))
    story.append(PageBreak())

    # Deploy
    story.append(p("Deploy Web, Android E iOS", H1))
    story.append(rule())
    deploy_rows = [
        [p("<b>Plataforma</b>", CELL_W), p("<b>Estado</b>", CELL_W), p("<b>Caminho recomendado</b>", CELL_W)],
        ["Web", "Mais pronto", "Render ja configurado: build requirements, preDeploy schema upgrade, gunicorn, health. Producao atual ok=true em ambitionzgame.com e onrender."],
        ["PWA", "Bom, com ajuste de copy", "Manifest, icons, service worker e prompt de update existem. Corrigir manifest: descricao one-card e lang=en nao refletem pt-BR/Rebirth atual."],
        ["Android", "Parcial", "Capacitor Android existe, AAB antigo existe, assets Play existem. Rebuild atual, testar emulator/device, atualizar package/story/screenshots/textos e assinar com chave correta."],
        ["iOS", "Inicial", "Dependencias/script Capacitor iOS existem no root, mas nao ha pasta ios/ versionada. Criar com cap add ios, configurar bundle id, signing, privacy, screenshots e TestFlight."],
    ]
    story.append(table(deploy_rows, [30 * mm, 32 * mm, 112 * mm]))
    story.append(p("Riscos especificos de deploy", H2))
    risk_rows = [
        [p("<b>Risco</b>", CELL_W), p("<b>Impacto</b>", CELL_W), p("<b>Acao</b>", CELL_W)],
        ["Duas configs Android", "Root usa com.elementra.ambitiontcg/onrender; mobile usa com.ambitionzgame.app/ambitionzgame.com.", "Escolher um appId oficial e remover ambiguidade antes da loja."],
        ["AAB antigo", "Arquivo de 29/04 pode nao conter Rebirth atual.", "Rebuild release apos cap sync e smoke em dispositivo."],
        ["Assets Play defasados", "Loja vende outro produto visual e outro numero de cartas.", "Regerar screenshots/textos da versao Rebirth atual."],
        ["Sem ios/ versionado", "Nao ha build iOS real para TestFlight.", "Criar projeto, configurar signing e validar WebView/PWA/cookies."],
        ["Gates externos", "Public beta bloqueada mesmo com deploy vivo.", "Legal, backup/restore e error tracking com evidencia privada."],
    ]
    story.append(table(risk_rows, [42 * mm, 58 * mm, 74 * mm]))
    story.append(PageBreak())

    # Next roadmap
    story.append(p("Proximos Passos Recomendados", H1))
    story.append(rule())
    next_rows = [
        [p("<b>Horizonte</b>", CELL_W), p("<b>Prioridade</b>", CELL_W), p("<b>Entrega objetiva</b>", CELL_W)],
        ["Agora", "P0", "Fechar evidence bundle externo: legal, backup/restore, error tracking smoke; manter billing off."],
        ["Agora", "P0", "Atualizar manifest/PWA copy e materiais Play Store para Rebirth 103 cards, pt-BR e visual atual."],
        ["7-14 dias", "P1", "Rodar closed beta controlada com cohort window e coletar eventos obrigatorios, first match, tutorial, D1/D7 e errors."],
        ["14-30 dias", "P1", "Polir mobile mulligan/hand/card readability com screenshots e player-eyes harness."],
        ["30-45 dias", "P1", "Iniciar modularizacao congelando gameplay: JS renderer/store, CSS dominios, app blueprints, persistence repos."],
        ["45-60 dias", "P2", "Rebuild Android atual e preparar TestFlight/iOS skeleton; alinhar package/bundle IDs."],
        ["Depois", "P2", "Async ghost/replay UI antes de PvP realtime; realtime so com reconnect, abuso/report, observabilidade e rollback."],
    ]
    story.append(table(next_rows, [28 * mm, 25 * mm, 121 * mm]))
    if (SHOT_DIR / "collection.png").exists() and (SHOT_DIR / "campaign.png").exists():
        story.append(Spacer(1, 5 * mm))
        img_table = Table(
            [[image_block(SHOT_DIR / "collection.png", 78 * mm, 120 * mm), image_block(SHOT_DIR / "campaign.png", 78 * mm, 120 * mm)]],
            colWidths=[87 * mm, 87 * mm],
        )
        img_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(img_table)
        story.append(p("Evidencia visual atual: colecao e campanha em desktop.", SMALL))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        canvas.drawString(18 * mm, 9 * mm, "Ambitionz Rebirth - Relatorio de Andamento Geral - 15/06/2026")
        canvas.drawRightString(192 * mm, 9 * mm, f"Pagina {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    build()
