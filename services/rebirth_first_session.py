"""First-session planning for Ambitionz Rebirth.

This module keeps onboarding decisions in Python. The browser receives a
small plan and renders it; it should not decide the player's learning path.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


FIRST_SESSION_VERSION = "first-session-v1"


ARENA_TUTORIAL_STEPS: List[Dict[str, Any]] = [
    {
        "step": 1,
        "title": "Bem-vindo a Arena",
        "body": "Toque numa carta da sua mao para ver custo, ataque, guarda e habilidade antes de jogar.",
        "target": ".rb-hand .rb-mini-card",
    },
    {
        "step": 2,
        "title": "Invoque com mana",
        "body": "O botao principal joga a carta selecionada. Se faltar mana, encerre o turno para recarregar.",
        "target": "#play-button",
    },
    {
        "step": 3,
        "title": "Ataque do campo",
        "body": "Depois de invocar, selecione um monstro pronto no seu campo. O botao principal vira Atacar.",
        "target": ".rb-field-card[data-attacker-instance], #play-button",
    },
    {
        "step": 4,
        "title": "Dano direto tem trava",
        "body": "No primeiro turno, dano direto fica bloqueado para dar tempo do bot responder. Procure o texto no slot inimigo vazio.",
        "target": ".rb-field-slot-empty.is-locked, #result-panel",
    },
    {
        "step": 5,
        "title": "Evolua duplicatas",
        "body": "Quando duas copias aparecem na mao, o painel de evolucao cria a forma Rebirth antes da invocacao.",
        "target": "#evolution-panel, #evolve-button",
    },
    {
        "step": 6,
        "title": "Funda no campo",
        "body": "Duas unidades iguais no campo podem virar uma fusao maior. Use isso antes de atacar quando precisar quebrar guarda.",
        "target": "#evolution-panel, #evolve-button, .rb-field-card",
    },
    {
        "step": 7,
        "title": "Encerre o turno",
        "body": "Quando nao houver boa jogada, encerre o turno. O bot age, sua mana sobe e voce compra novas cartas.",
        "target": "#next-turn-button",
    },
    {
        "step": 8,
        "title": "Leia o recap",
        "body": "Ao terminar, o painel mostra por que voce venceu ou perdeu e sugere o proximo ajuste do deck.",
        "target": "#reward-panel, #result-actions",
    },
]


def _progress_value(progression: Optional[Dict[str, Any]], key: str, fallback: Any = 0) -> Any:
    if not isinstance(progression, dict):
        return fallback
    return progression.get(key, fallback)


def _status(done: bool, current: bool = False, locked: bool = False) -> str:
    if done:
        return "done"
    if current:
        return "current"
    if locked:
        return "locked"
    return "next"


def _next_action(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    for action in actions:
        if action["state"] in {"current", "next"}:
            return action
    return actions[-1]


def first_session_plan(
    *,
    account: Optional[Dict[str, Any]] = None,
    progression: Optional[Dict[str, Any]] = None,
    state: Optional[Dict[str, Any]] = None,
    release_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the authoritative first-ten-minute learning plan."""

    account = account or {}
    progression = progression or {}
    authenticated = bool(account.get("authenticated"))
    clashes = int(_progress_value(progression, "clashes", 0) or 0)
    wins = int(_progress_value(progression, "wins", 0) or 0)
    boosters = int(_progress_value(progression, "boosters_opened", 0) or 0)
    tutorial_step = int(_progress_value(progression, "tutorial_step", 0) or 0)
    tutorial_complete = bool(_progress_value(progression, "tutorial_complete", False))
    daily_claimed = bool(_progress_value(progression, "daily_claimed", False))
    match_finished = bool((state or {}).get("is_finished"))
    active_match_id = (state or {}).get("match_id")

    actions = [
        {
            "key": "create_or_continue",
            "minute": "0-1",
            "title": "Entrar ou jogar visitante",
            "copy": "Conta salva colecao e progresso; visitante serve para testar uma partida rapida.",
            "state": _status(authenticated, current=not authenticated),
            "href": "/rebirth/account" if not authenticated else "/rebirth",
        },
        {
            "key": "guided_duel",
            "minute": "1-5",
            "title": "Partida guiada",
            "copy": "Aprender mao, mana, campo, trava de dano direto e recap dentro da arena.",
            "state": _status(tutorial_complete or clashes > 0, current=authenticated and not tutorial_complete),
            "href": "/rebirth?firstRun=1",
        },
        {
            "key": "finish_match",
            "minute": "5-7",
            "title": "Fechar o primeiro match",
            "copy": "O recap explica causa de vitoria/derrota e aponta o proximo ajuste.",
            "state": _status(clashes > 0 or match_finished, current=authenticated and tutorial_complete and clashes == 0),
            "href": "/rebirth",
        },
        {
            "key": "claim_daily",
            "minute": "7-8",
            "title": "Resgatar diario",
            "copy": "A recompensa diaria fixa o loop jogar -> resgatar -> melhorar deck.",
            "state": _status(daily_claimed, current=clashes > 0 and not daily_claimed, locked=clashes == 0),
            "href": "/rebirth/progression",
        },
        {
            "key": "open_booster",
            "minute": "8-9",
            "title": "Abrir booster",
            "copy": "O pacote revela opcoes e ativa o coach de deck pos-booster.",
            "state": _status(boosters > 0, current=daily_claimed and boosters == 0, locked=not daily_claimed),
            "href": "/rebirth/shop",
        },
        {
            "key": "tune_deck",
            "minute": "9-10",
            "title": "Ajustar deck",
            "copy": "Trocar cartas soltas por pares, respostas e familia dominante.",
            "state": _status(wins > 0 and boosters > 0, current=boosters > 0),
            "href": "/rebirth/collection",
        },
    ]
    next_action = _next_action(actions)
    return {
        "version": FIRST_SESSION_VERSION,
        "release_version": release_version,
        "authenticated": authenticated,
        "active_match_id": active_match_id,
        "tutorial_step": tutorial_step,
        "tutorial_complete": tutorial_complete,
        "should_guide_match": bool(not tutorial_complete and clashes == 0),
        "estimated_minutes": 10,
        "next_action": next_action,
        "actions": actions,
        "arena_tutorial_steps": deepcopy(ARENA_TUTORIAL_STEPS),
    }
