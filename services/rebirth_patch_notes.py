"""Novidades / Patch Notes do Ambitionz Rebirth.

Conteúdo curado em linguagem de jogador (mais recente primeiro). Atualize esta
lista a cada release — é a "cadência de live-ops" visível pro jogador.
"""
from __future__ import annotations

from typing import Any, Dict, List


PATCH_NOTES: List[Dict[str, Any]] = [
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
