"""PvP ao vivo (passo 3) — fila/match, handoff de turno (sem IA) e win->ELO.

Testa o orquestrador em memória (services.rebirth_live_pvp) de forma
determinística, sem depender do gameplay completo."""
import services.rebirth_live_pvp as live
from services.rebirth_cards import PLAYER_DECK as DEFAULT_LOADOUT
from services.rebirth_persistence import RebirthRepository


def _reset():
    live._QUEUE.clear()
    live._LIVE.clear()
    live._USER_LIVE.clear()


def _repo(flask_app):
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.ensure_schema()
    return repo


def _uid(repo, name):
    u = repo.create_user(name, name + "@example.com", "password123")
    return u["id"] if isinstance(u, dict) else u


def test_join_queues_then_matches(flask_app):
    _reset()
    r1 = live.join(101, "u1", list(DEFAULT_LOADOUT), 1500)
    assert r1["status"] == "waiting"
    r2 = live.join(102, "u2", list(DEFAULT_LOADOUT), 1500)
    assert r2["status"] == "matched"
    session = live._LIVE[r2["live_id"]]
    assert session["active_user"] == 101            # quem esperava começa (slot player)
    assert set(session["users"]) == {101, 102}
    assert session["match"].get("_runtime_mode") == "pvp_sync"


def test_end_turn_hands_off_without_ai(flask_app):
    _reset()
    live.join(201, "a", list(DEFAULT_LOADOUT), 1500)
    lid = live.join(202, "b", list(DEFAULT_LOADOUT), 1500)["live_id"]
    session = live._LIVE[lid]
    assert session["active_user"] == 201
    bot_field_before = len([c for c in session["match"]["bot"].get("battlefield", []) if c])
    live.end_turn(lid, 201)                          # 'a' encerra
    assert session["active_user"] == 202             # vez passou pro outro humano
    # a IA NÃO jogou pelo lado que recebeu o turno (sem invocações automáticas)
    new_player_field = len([c for c in session["match"]["player"].get("battlefield", []) if c])
    assert new_player_field == bot_field_before == 0


def test_not_your_turn_is_rejected(flask_app):
    _reset()
    live.join(301, "a", list(DEFAULT_LOADOUT), 1500)
    lid = live.join(302, "b", list(DEFAULT_LOADOUT), 1500)["live_id"]
    try:
        live.end_turn(lid, 302)                       # 302 não é o ativo
        assert False, "deveria recusar"
    except Exception as exc:
        assert "not_your_turn" in str(getattr(exc, "code", "")) or "turno" in str(exc).lower()


def test_finish_settles_symmetric_elo(flask_app):
    _reset()
    repo = _repo(flask_app)
    w = _uid(repo, "winner_live")
    l = _uid(repo, "loser_live")
    live.join(w, "winner_live", list(DEFAULT_LOADOUT), 1500)
    lid = live.join(l, "loser_live", list(DEFAULT_LOADOUT), 1500)["live_id"]
    session = live._LIVE[lid]
    # força um fim com o dono do slot 'player' (ativo = w) vencendo
    session["match"]["is_finished"] = True
    session["match"]["winner"] = "player"
    live._maybe_settle(session, repo)
    assert session["winner_user"] == w
    assert repo.get_user_ranking(w)["elo"] > 1500     # vencedor sobe
    assert repo.get_user_ranking(l)["elo"] < 1500     # perdedor cai (espelho)
    # idempotente: re-liquidar não muda nada
    before = repo.get_user_ranking(w)["elo"]
    live._maybe_settle(session, repo)
    assert repo.get_user_ranking(w)["elo"] == before
