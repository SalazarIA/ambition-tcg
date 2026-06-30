"""PvP assíncrono — ELO contra o ELO REAL do oponente + espelho idempotente."""
from services.rebirth_persistence import RebirthRepository


def _repo(flask_app):
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.ensure_schema()
    return repo


def _user(repo, name):
    u = repo.create_user(name, name + "@example.com", "password123")
    return u["id"] if isinstance(u, dict) else u


def _pvp_match(match_id, winner, opp_id, opp_elo):
    return {
        "match_id": match_id,
        "is_finished": True,
        "winner": winner,
        "bot_profile": {"id": "opportunist"},
        "pvp": {"opponent_id": opp_id, "opponent_name": "rival", "opponent_elo": opp_elo},
    }


def test_pvp_win_moves_both_elos_symmetrically(flask_app):
    repo = _repo(flask_app)
    a = _user(repo, "alice")
    b = _user(repo, "bob")
    # ambos começam em 1500; alice (player) vence bob
    new_a = repo.apply_match_elo(a, _pvp_match("m1", "player", b, 1500))
    assert new_a > 1500                          # vencedor sobe
    assert repo.get_user_ranking(b)["elo"] < 1500  # oponente cai (espelho)
    # soma ~ simétrica em ELO igual (K=32 -> +16/-16)
    assert repo.get_user_ranking(a)["elo"] == 1516
    assert repo.get_user_ranking(b)["elo"] == 1484


def test_pvp_uses_opponent_elo_not_bot_profile(flask_app):
    repo = _repo(flask_app)
    a = _user(repo, "carol")
    b = _user(repo, "dave")
    # oponente forte (1900): vencer dá MAIS que contra um bot 1500
    repo.apply_match_elo(a, _pvp_match("m2", "player", b, 1900))
    assert repo.get_user_ranking(a)["elo"] >= 1525  # ganho maior por bater alguém acima


def test_pvp_elo_is_idempotent_per_match(flask_app):
    repo = _repo(flask_app)
    a = _user(repo, "erin")
    b = _user(repo, "finn")
    repo.apply_match_elo(a, _pvp_match("m3", "player", b, 1500))
    elo_a = repo.get_user_ranking(a)["elo"]
    elo_b = repo.get_user_ranking(b)["elo"]
    repo.apply_match_elo(a, _pvp_match("m3", "player", b, 1500))  # re-aplica mesmo match
    assert repo.get_user_ranking(a)["elo"] == elo_a
    assert repo.get_user_ranking(b)["elo"] == elo_b


def test_find_pvp_opponent_excludes_self(flask_app):
    repo = _repo(flask_app)
    a = _user(repo, "grace")
    b = _user(repo, "heidi")
    opp = repo.find_pvp_opponent(a, elo=1500)
    assert opp is not None
    assert opp["id"] != a


def test_bot_match_does_not_move_ranking_elo(flask_app):
    # Mudança de produto: só PvP real mexe no ranking. Partida comum contra
    # o computador (arena/ranqueada sem oponente disponível) não tem
    # match.pvp, então apply_match_elo deve ser um no-op.
    repo = _repo(flask_app)
    a = _user(repo, "ivan")
    bot_match = {
        "match_id": "bot1",
        "is_finished": True,
        "winner": "player",
        "bot_profile": {"id": "defensive"},
    }
    result = repo.apply_match_elo(a, bot_match)
    assert result is None
    assert repo.get_user_ranking(a)["elo"] == 1500


def test_campaign_match_does_not_move_ranking_elo(flask_app):
    # Campanha tem progressão própria (record_campaign_victory); não deve
    # tocar o ranking ELO, mesmo vencendo um chefe.
    repo = _repo(flask_app)
    a = _user(repo, "judy")
    campaign_match = {
        "match_id": "camp1",
        "is_finished": True,
        "winner": "player",
        "bot_profile": {"id": "aggressive"},
        "campaign_node": "node_05",
    }
    result = repo.apply_match_elo(a, campaign_match)
    assert result is None
    assert repo.get_user_ranking(a)["elo"] == 1500
