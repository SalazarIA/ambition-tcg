"""Retention and questline decisions for Rebirth."""

from __future__ import annotations

from typing import Any, Dict, List


def _int(profile: Dict[str, Any], key: str, fallback: int = 0) -> int:
    try:
        return int(profile.get(key, fallback) or fallback)
    except (TypeError, ValueError):
        return fallback


def _quest(key: str, name: str, progress: int, goal: int, reward: str, state: str) -> Dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "progress": max(0, min(progress, goal)),
        "goal": goal,
        "reward": reward,
        "state": state,
    }


def retention_questline(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Build daily/weekly loop payload from progression."""

    profile = profile or {}
    clashes = _int(profile, "clashes")
    wins = _int(profile, "wins")
    boosters = _int(profile, "boosters_opened")
    tutorial_complete = bool(profile.get("tutorial_complete", False))
    daily_claimed = bool(profile.get("daily_claimed", False))
    daily_ready = clashes >= 1

    quests: List[Dict[str, Any]] = [
        _quest(
            "play_one",
            "Jogue 1 partida",
            clashes,
            1,
            "25 XP diario",
            "claimed" if daily_claimed else "ready" if daily_ready else "locked",
        ),
        _quest(
            "win_one",
            "Venca 1 partida",
            wins,
            1,
            "Selo de leitura",
            "ready" if wins >= 1 else "locked",
        ),
        _quest(
            "open_booster",
            "Abra 1 booster",
            boosters,
            1,
            "Novas opcoes de deck",
            "ready" if boosters >= 1 else "locked",
        ),
        _quest(
            "finish_tutorial",
            "Conclua o tutorial",
            1 if tutorial_complete else 0,
            1,
            "60 XP",
            "claimed" if tutorial_complete else "ready",
        ),
    ]
    weekly = [
        _quest("play_five", "Jogue 5 partidas", clashes, 5, "Booster semanal", "ready" if clashes >= 5 else "locked"),
        _quest("win_three", "Venca 3 partidas", wins, 3, "Titulo de beta", "ready" if wins >= 3 else "locked"),
        _quest("open_three", "Abra 3 boosters", boosters, 3, "Carta incomum garantida", "ready" if boosters >= 3 else "locked"),
    ]
    next_goal = (
        "Resgate a recompensa diaria."
        if daily_ready and not daily_claimed
        else "Conclua o tutorial guiado."
        if not tutorial_complete
        else "Abra um booster e ajuste seu baralho."
        if boosters < 1
        else "Jogue por vitorias e teste novas linhas."
    )
    return {
        "daily": {
            "name": "Jogue um clash",
            "progress": min(1, clashes),
            "goal": 1,
            "reward": "25 XP",
            "state": "claimed" if daily_claimed else "ready" if daily_ready else "locked",
        },
        "quests": quests,
        "weekly": weekly,
        "retention": {
            "next_goal": next_goal,
            "daily_complete": daily_claimed,
            "beta_loop": ["Jogar", "Resgatar", "Abrir booster", "Ajustar deck"],
            "live_loop_version": "retention-loop-v1",
        },
    }
