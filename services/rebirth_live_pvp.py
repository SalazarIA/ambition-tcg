"""PvP ao vivo (dois humanos) — passo 3 da profundidade competitiva.

Sem infra nova: roda por POLLING no worker atual (-w 1 --threads 100). Fila de
matchmaking e partidas ao vivo vivem EM MEMÓRIA (protegidas por um Lock).

Modelo "ativo-sempre-no-slot-player": o engine roteia comandos pro lado
"player" e a "vez do bot" não roda IA quando _runtime_mode == "pvp_sync". O
jogador ATIVO ocupa sempre o slot "player"; ao encerrar o turno, trocamos os
lados (player<->bot) e o outro humano assume. Assim reusamos play_card/attack/
next_turn SEM refatorar o core determinístico.
"""
from __future__ import annotations

import secrets
import threading
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional

from services.rebirth_engine import start_match
from services.rebirth_dispatcher import (
    dispatch_command,
    SummonCardCommand,
    DeclareAttackCommand,
    EndTurnCommand,
    EvolveDuplicateCommand,
)
from services.rebirth_contracts import RebirthError
from services.rebirth_serializers import public_state

_LOCK = threading.RLock()
_QUEUE: List[Dict[str, Any]] = []          # jogadores aguardando par
_LIVE: Dict[str, Dict[str, Any]] = {}      # live_id -> sessão
_USER_LIVE: Dict[int, str] = {}            # user_id -> live_id atual
_QUEUE_TTL = 90                            # s: descarta espera fantasma
_TURN_TIMEOUT = 45.0                        # s sem ação -> auto-encerra o turno
_MAX_SKIPS = 3                             # turnos auto-pulados seguidos -> W.O.


def _now() -> float:
    return time.time()


def _other(session: Dict[str, Any], user_id: int) -> int:
    a, b = session["users"]
    return b if user_id == a else a


def _prune_queue() -> None:
    cutoff = _now() - _QUEUE_TTL
    _QUEUE[:] = [w for w in _QUEUE if w["ts"] >= cutoff]


def join(user_id: int, username: str, deck: List[str], elo: int) -> Dict[str, Any]:
    """Entra na fila de PvP ao vivo. Pareia com quem estiver esperando."""
    with _LOCK:
        # Já está numa partida ao vivo viva? devolve ela (reconexão simples).
        existing = _USER_LIVE.get(user_id)
        if existing and existing in _LIVE:
            return {"status": "matched", "live_id": existing}
        _prune_queue()
        # remove entradas antigas do próprio usuário na fila
        _QUEUE[:] = [w for w in _QUEUE if w["user_id"] != user_id]
        # Matchmaking: pareia com o jogador na fila de ELO MAIS PRÓXIMO (não só o
        # primeiro), pra duelos mais equilibrados.
        candidates = [w for w in _QUEUE if w["user_id"] != user_id]
        if not candidates:
            _QUEUE.append({"user_id": user_id, "username": username, "deck": list(deck), "elo": int(elo), "ts": _now()})
            return {"status": "waiting"}
        opponent = min(candidates, key=lambda w: abs(int(w.get("elo", 1500)) - int(elo)))
        _QUEUE.remove(opponent)
        return _create_match(opponent, {"user_id": user_id, "username": username, "deck": list(deck), "elo": int(elo)})


def _create_match(first: Dict[str, Any], second: Dict[str, Any]) -> Dict[str, Any]:
    """`first` (quem esperava) começa como slot 'player' e joga primeiro."""
    match = start_match(
        seed=f"pvp:{first['user_id']}:{second['user_id']}:{secrets.token_hex(4)}",
        player_card_ids=first["deck"],
        player_name=first["username"],
        bot_card_ids=second["deck"],
        bot_profile_id="opportunist",
        runtime_mode="pvp_sync",
        apply_reducers_inline=True,
    )
    match["bot"]["name"] = second["username"]
    live_id = "live_" + secrets.token_hex(8)
    match["match_id"] = live_id
    session = {
        "id": live_id,
        "users": [first["user_id"], second["user_id"]],
        "names": {first["user_id"]: first["username"], second["user_id"]: second["username"]},
        "elos": {first["user_id"]: first["elo"], second["user_id"]: second["elo"]},
        "active_user": first["user_id"],   # dono do slot "player"
        "match": match,
        "created": _now(),
        "settled": False,
        "turn_started_at": _now(),
        "skips": {},
    }
    _LIVE[live_id] = session
    _USER_LIVE[first["user_id"]] = live_id
    _USER_LIVE[second["user_id"]] = live_id
    return {"status": "matched", "live_id": live_id}


def _require(live_id: str, user_id: int) -> Dict[str, Any]:
    session = _LIVE.get(live_id)
    if not session or user_id not in session["users"]:
        raise RebirthError("Partida ao vivo não encontrada.", "live_not_found")
    return session


def _require_turn(session: Dict[str, Any], user_id: int) -> None:
    if session["match"].get("is_finished"):
        raise RebirthError("A partida já terminou.", "match_finished")
    if session["active_user"] != user_id:
        raise RebirthError("Aguarde o turno do oponente.", "not_your_turn")


def view(live_id: str, user_id: int, repo=None) -> Dict[str, Any]:
    """Estado pela PERSPECTIVA do jogador: o ativo vê o match normal; o que
    aguarda vê com os lados trocados (a própria mão revelada). Cada acesso roda
    o _tick (enforcement de timeout/abandono)."""
    with _LOCK:
        session = _require(live_id, user_id)
        _tick(session, repo)
        match = session["match"]
        if session["active_user"] == user_id:
            state = public_state(match)
        else:
            mirror = deepcopy(match)
            mirror["player"], mirror["bot"] = mirror["bot"], mirror["player"]
            state = public_state(mirror)
        # Nome do oponente pela perspectiva deste jogador (sempre o OUTRO humano),
        # pro HUD mostrar o username em vez do rótulo do bot — correto mesmo após
        # as trocas de lado.
        state["pvp"] = {"opponent_name": session["names"].get(_other(session, user_id))}
        seconds_left = max(0, int(_TURN_TIMEOUT - (_now() - float(session.get("turn_started_at") or _now()))))
        return {
            "live_id": live_id,
            "state": state,
            "your_turn": (session["active_user"] == user_id) and not match.get("is_finished"),
            "opponent": session["names"].get(_other(session, user_id)),
            "finished": bool(match.get("is_finished")),
            "winner_user": session.get("winner_user"),
            "turn_seconds_left": seconds_left,
        }


def play_card(live_id, user_id, *, card_instance_id=None, card_id=None, field_slot=None, target_instance_id=None, repo=None):
    with _LOCK:
        session = _require(live_id, user_id)
        _require_turn(session, user_id)
        session["skips"][user_id] = 0
        dispatch_command(session["match"], SummonCardCommand(
            card_instance_id=card_instance_id, card_id=card_id, field_slot=field_slot, target_instance_id=target_instance_id))
        _maybe_settle(session, repo)
        return view(live_id, user_id, repo)


def attack(live_id, user_id, *, attacker_instance_id=None, target_instance_id=None, repo=None):
    with _LOCK:
        session = _require(live_id, user_id)
        _require_turn(session, user_id)
        session["skips"][user_id] = 0
        dispatch_command(session["match"], DeclareAttackCommand(
            attacker_instance_id=attacker_instance_id, target_instance_id=target_instance_id))
        _maybe_settle(session, repo)
        return view(live_id, user_id, repo)


def evolve(live_id, user_id, *, card_id=None, repo=None):
    with _LOCK:
        session = _require(live_id, user_id)
        _require_turn(session, user_id)
        session["skips"][user_id] = 0
        dispatch_command(session["match"], EvolveDuplicateCommand(card_id=card_id))
        _maybe_settle(session, repo)
        return view(live_id, user_id, repo)


def _handoff(session: Dict[str, Any], ended_user: int) -> None:
    """Passa a vez: o outro humano assume o slot 'player' e o relógio reinicia."""
    match = session["match"]
    match["player"], match["bot"] = match["bot"], match["player"]
    session["active_user"] = _other(session, ended_user)
    session["turn_started_at"] = _now()


def _end_turn_internal(session: Dict[str, Any], repo) -> None:
    match = session["match"]
    ended = session["active_user"]
    dispatch_command(match, EndTurnCommand(turn=match.get("turn")))
    if match.get("is_finished"):
        _maybe_settle(session, repo)
    else:
        _handoff(session, ended)


def _tick(session: Dict[str, Any], repo=None) -> None:
    """Enforcement preguiçoso de timeout (chamado em todo acesso à sessão). Se o
    ativo estourou o tempo do turno, auto-encerra; após _MAX_SKIPS turnos
    auto-pulados seguidos, ele perde por W.O. (oponente vence + ELO). Resolve
    abandono/aba fechada sem thread nem infra: o poll do oponente dispara."""
    match = session["match"]
    if match.get("is_finished") or session.get("settled"):
        return
    if (_now() - float(session.get("turn_started_at") or _now())) <= _TURN_TIMEOUT:
        return
    active = session["active_user"]
    session["skips"][active] = int(session["skips"].get(active, 0)) + 1
    if session["skips"][active] >= _MAX_SKIPS:
        match["is_finished"] = True
        match["winner"] = "bot"          # ativo (slot player) abandonou -> oponente vence
        _maybe_settle(session, repo)
        return
    _end_turn_internal(session, repo)


def end_turn(live_id, user_id, repo=None) -> Dict[str, Any]:
    """Encerra o turno do jogador ativo (sem IA em pvp_sync) e passa a vez; se a
    partida acabou, liquida o ELO dos dois."""
    with _LOCK:
        session = _require(live_id, user_id)
        _require_turn(session, user_id)
        session["skips"][user_id] = 0       # ação voluntária: jogador presente
        _end_turn_internal(session, repo)
        return view(live_id, user_id, repo)


def _maybe_settle(session: Dict[str, Any], repo) -> None:
    """Liquida o match se acabou (em QUALQUER comando: ataque letal, fadiga ou
    encerramento). Idempotente via session['settled']."""
    if session["match"].get("is_finished") and not session.get("settled"):
        _settle(session, repo)


def _settle(session: Dict[str, Any], repo) -> None:
    if session.get("settled"):
        return
    session["settled"] = True
    match = session["match"]
    winner_slot = match.get("winner")
    player_owner = session["active_user"]            # dono atual do slot "player"
    bot_owner = _other(session, player_owner)
    if winner_slot == "player":
        winner, loser = player_owner, bot_owner
    elif winner_slot == "bot":
        winner, loser = bot_owner, player_owner
    else:
        return
    session["winner_user"] = winner
    if repo is not None:
        try:
            repo.apply_match_elo(winner, {
                "is_finished": True,
                "winner": "player",
                "match_id": session["id"],
                "pvp": {"opponent_id": loser, "opponent_name": session["names"].get(loser),
                        "opponent_elo": int(session["elos"].get(loser, 1500))},
            })
        except Exception:
            pass


def leave(user_id: int) -> None:
    """Sai da fila (e libera o ponteiro de partida se terminada)."""
    with _LOCK:
        _QUEUE[:] = [w for w in _QUEUE if w["user_id"] != user_id]
        live_id = _USER_LIVE.get(user_id)
        if live_id and live_id in _LIVE and _LIVE[live_id]["match"].get("is_finished"):
            _USER_LIVE.pop(user_id, None)
