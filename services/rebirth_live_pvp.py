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

import logging
import os
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

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()
_QUEUE: List[Dict[str, Any]] = []          # jogadores aguardando par
_LIVE: Dict[str, Dict[str, Any]] = {}      # live_id -> sessão
_USER_LIVE: Dict[int, str] = {}            # user_id -> live_id atual
_QUEUE_TTL = 90                            # s: descarta espera fantasma
_TURN_TIMEOUT = 45.0                        # s sem ação -> auto-encerra o turno
_MAX_SKIPS = 3                             # turnos auto-pulados seguidos -> W.O.

# audit 30/06: partidas finalizadas nunca saíam de _LIVE (vazamento de memória
# sem teto, ao contrário de RebirthMatchStore). _LIVE_RETENTION_SECONDS dá
# tempo de um último poll ver o resultado final antes de remover a sessão;
# _LIVE_MAX_SESSIONS é o teto duro (mesma ordem de grandeza do MATCH_STORE).
_LIVE_RETENTION_SECONDS = 120
_LIVE_MAX_SESSIONS = 512
# Se NINGUÉM (nenhum dos dois lados) faz uma única requisição por esse tempo,
# o _tick lazy (que só roda dentro de view()) nunca dispara — a partida fica
# pendurada pra sempre. _prune_live varre todas as sessões periodicamente e
# anula (sem vencedor, sem ELO) as que ninguém mais está olhando.
_BOTH_ABANDONED_SECONDS = _TURN_TIMEOUT * (_MAX_SKIPS + 2)
_PRUNE_INTERVAL = 10.0
_last_prune = 0.0


def _worker_count() -> int:
    for name in ("WEB_CONCURRENCY", "GUNICORN_WORKERS"):
        try:
            value = int(os.environ.get(name, "") or 0)
        except (TypeError, ValueError):
            value = 0
        if value:
            return value
    return 1


if _worker_count() > 1:
    logger.warning(
        "rebirth_live_pvp: %d workers detected but the live-PvP queue/match "
        "state is in-process memory only (no Redis backend). Live PvP join/"
        "state/command will split across workers and break silently — keep "
        "this module single-worker until it gets a shared backend.",
        _worker_count(),
    )


def _now() -> float:
    return time.time()


def _other(session: Dict[str, Any], user_id: int) -> int:
    a, b = session["users"]
    return b if user_id == a else a


def _prune_queue() -> None:
    cutoff = _now() - _QUEUE_TTL
    _QUEUE[:] = [w for w in _QUEUE if w["ts"] >= cutoff]


def _drop_session(live_id: str, session: Dict[str, Any]) -> None:
    _LIVE.pop(live_id, None)
    for uid in session.get("users", ()):
        if _USER_LIVE.get(uid) == live_id:
            _USER_LIVE.pop(uid, None)


def _trim_live_locked() -> None:
    if len(_LIVE) <= _LIVE_MAX_SESSIONS:
        return
    # remove as mais antigas primeiro, priorizando as já finalizadas
    ordered = sorted(
        _LIVE.items(),
        key=lambda kv: (not kv[1]["match"].get("is_finished"), kv[1].get("created", 0)),
    )
    while len(_LIVE) > _LIVE_MAX_SESSIONS and ordered:
        live_id, session = ordered.pop(0)
        _drop_session(live_id, session)


def _prune_live(repo=None) -> None:
    """Varredura periódica (throttled) de TODAS as sessões: libera partidas
    finalizadas há tempo suficiente e anula (sem vencedor/ELO) partidas onde
    nenhum dos dois lados fez uma requisição nos últimos _BOTH_ABANDONED_SECONDS
    — caso em que o _tick lazy (só roda dentro de view()) nunca dispararia."""
    global _last_prune
    now = _now()
    if now - _last_prune < _PRUNE_INTERVAL:
        return
    _last_prune = now
    for live_id, session in list(_LIVE.items()):
        match = session["match"]
        if match.get("is_finished"):
            settled_at = float(session.get("settled_at") or session.get("created") or now)
            if session.get("settled") and (now - settled_at) >= _LIVE_RETENTION_SECONDS:
                _drop_session(live_id, session)
            continue
        last_seen = float(session.get("last_seen") or session.get("turn_started_at") or session.get("created") or now)
        if (now - last_seen) >= _BOTH_ABANDONED_SECONDS:
            match["is_finished"] = True
            match["winner"] = None  # ninguém apareceu: anula, sem W.O. unilateral e sem ELO
            _maybe_settle(session, repo)
            _drop_session(live_id, session)  # ninguém está olhando — pode sumir na hora
    _trim_live_locked()


def join(user_id: int, username: str, deck: List[str], elo: int, repo=None) -> Dict[str, Any]:
    """Entra na fila de PvP ao vivo. Pareia com quem estiver esperando."""
    with _LOCK:
        _prune_live(repo)
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
        "last_seen": _now(),
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
        _prune_live(repo)
        session = _require(live_id, user_id)
        session["last_seen"] = _now()
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
    session["settled_at"] = _now()
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


def leave(user_id: int, repo=None) -> None:
    """Sai da fila; se estiver numa partida ao vivo em andamento, desiste na
    hora (W.O. imediato pro oponente) em vez de fazer o oponente esperar o
    timeout de turno (até _TURN_TIMEOUT * _MAX_SKIPS segundos). Chamado pelo
    frontend ao fechar/trocar de aba (pagehide/visibilitychange) e pela ação
    explícita "leave"."""
    with _LOCK:
        _QUEUE[:] = [w for w in _QUEUE if w["user_id"] != user_id]
        live_id = _USER_LIVE.get(user_id)
        if not live_id or live_id not in _LIVE:
            return
        session = _LIVE[live_id]
        match = session["match"]
        if not match.get("is_finished"):
            other = _other(session, user_id)
            # quem desiste perde, não importa de quem é a vez no momento
            match["is_finished"] = True
            match["winner"] = "player" if session["active_user"] == other else "bot"
            _maybe_settle(session, repo)
        _USER_LIVE.pop(user_id, None)
