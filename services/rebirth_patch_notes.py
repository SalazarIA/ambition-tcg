"""Novidades / Patch Notes do Ambitionz Rebirth.

Conteúdo curado em linguagem de jogador (mais recente primeiro). Atualize esta
lista a cada release — é a "cadência de live-ops" visível pro jogador.
"""
from __future__ import annotations

from typing import Any, Dict, List


PATCH_NOTES: List[Dict[str, Any]] = [
    {
        "version": "v131",
        "date": "Jun 2026",
        "title": "Polish do PvP",
        "tag": "Competitivo",
        "items": [
            "No PvP, o nome do oponente aparece no lugar do rótulo de bot.",
            "A fila ao vivo pareia por ELO mais próximo, pra duelos equilibrados.",
            "Mensagem clara de “entre na sua conta” ao tentar jogar ao vivo sem login.",
        ],
    },
    {
        "version": "v130",
        "date": "Jun 2026",
        "title": "PvP ao vivo",
        "tag": "Competitivo",
        "items": [
            "Duele contra outro jogador em tempo real: “Jogar ao vivo (PvP)” no Ranking.",
            "Entra na fila, pareia com um oponente e vocês jogam turno a turno.",
            "O ELO dos dois é ajustado ao fim do duelo.",
        ],
    },
    {
        "version": "v129",
        "date": "Jun 2026",
        "title": "PvP assíncrono",
        "tag": "Competitivo",
        "items": [
            "Desafie o deck de outro jogador direto do Ranking (botão “Desafiar”).",
            "O duelo é resolvido no servidor e o ELO dos dois lados é ajustado.",
            "Primeiro passo rumo ao PvP completo.",
        ],
    },
    {
        "version": "v128",
        "date": "Jun 2026",
        "title": "Mais atalhos + feedback de mana",
        "tag": "Controles",
        "items": [
            "Teclas 1–9 selecionam a carta da mão pela posição.",
            "ESC cancela a seleção atual.",
            "Duplo-clique na sua criatura ataca o herói inimigo quando o caminho está livre.",
            "A mana agora pisca ao ser gasta — o consumo não passa mais despercebido.",
        ],
    },
    {
        "version": "v127",
        "date": "Jun 2026",
        "title": "Atalhos de jogada",
        "tag": "Controles",
        "items": [
            "Duplo-clique numa carta da mão invoca/joga direto.",
            "Arraste a carta da mão e solte no altar pra invocar naquele slot.",
            "Espaço ou Enter encerram o turno.",
            "Clique numa área vazia do tabuleiro pra cancelar a seleção.",
            "Correção: o botão Fundir agora aparece quando a fusão está pronta.",
        ],
    },
    {
        "version": "v126",
        "date": "Jun 2026",
        "title": "Polish de invocação",
        "tag": "Feel",
        "items": [
            "Invocar uma criatura agora tem som dedicado (jogador e bot).",
            "Clarão/anel de energia no altar no momento da invocação.",
            "A sua carta recém-invocada entra em cena com animação, igual à do bot.",
        ],
    },
    {
        "version": "v125",
        "date": "Jun 2026",
        "title": "Novidades / Patch Notes",
        "tag": "Live-ops",
        "items": [
            "Esta página: o histórico de atualizações do jogo em um só lugar.",
            "Novo atalho “Novidades” na barra de navegação.",
        ],
    },
    {
        "version": "v124",
        "date": "Jun 2026",
        "title": "Temporada ranqueada",
        "tag": "Ranked",
        "items": [
            "Recompensa de fim de temporada por faixa de ELO (Bronze → Lendário).",
            "Soft-reset do ELO ao fechar a season pra manter a disputa viva.",
            "Sua faixa e a recompensa prevista aparecem no Ranking.",
        ],
    },
    {
        "version": "v123",
        "date": "Jun 2026",
        "title": "Forja — crafting de cartas",
        "tag": "Economia",
        "items": [
            "Desmanche cartas repetidas e ganhe pó.",
            "Crie as cartas Comum/Incomum que faltam gastando pó.",
            "Saldo de pó e botões de desmanchar/criar direto na Coleção.",
        ],
    },
    {
        "version": "v122",
        "date": "Jun 2026",
        "title": "Replays e ghosts",
        "tag": "Competitivo",
        "items": [
            "Seus replays verificáveis aparecem no Ranking, com código pra compartilhar e desafiar.",
        ],
    },
    {
        "version": "v121",
        "date": "Jun 2026",
        "title": "Guia de arquétipos",
        "tag": "Decks",
        "items": [
            "Novo guia no Deck Builder: Aggro Fogo, Controle Terra, Sustento Água, Sombra Pierce e Arcano.",
            "Clicar num arquétipo filtra o catálogo pelo elemento dele.",
        ],
    },
    {
        "version": "v120",
        "date": "Jun 2026",
        "title": "Rework visual da arena",
        "tag": "Arena",
        "items": [
            "Cartas da mão menores; tabuleiro e slots maiores.",
            "Cartas de campo maiores, com a força sempre visível.",
            "Layout que se adapta à altura da tela (sem quebrar em laptops).",
        ],
    },
    {
        "version": "v118",
        "date": "Jun 2026",
        "title": "Simetria e foto de perfil",
        "tag": "Perfil",
        "items": [
            "Heróis centralizados e simétricos na arena.",
            "Foto de perfil: clique no círculo do herói pra escolher um avatar.",
            "Overlay de vitória mais legível.",
        ],
    },
]


def patch_notes_payload() -> Dict[str, Any]:
    return {"entries": PATCH_NOTES, "count": len(PATCH_NOTES), "latest": PATCH_NOTES[0]["version"] if PATCH_NOTES else None}
