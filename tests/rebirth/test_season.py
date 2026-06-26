"""Season (temporada) — recompensa por faixa de ELO + soft-reset + bump,
gatilho manual (close_season). Idempotente por (usuário, season)."""
from services.rebirth_persistence import RebirthRepository


def _repo(flask_app):
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.ensure_schema()
    return repo


def _user(repo, name):
    u = repo.create_user(name, name + "@example.com", "password123")
    return u["id"] if isinstance(u, dict) else u


def test_season_tier_thresholds(flask_app):
    repo = _repo(flask_app)
    assert repo.season_tier(1300)["tier"] == "Bronze"
    assert repo.season_tier(1500)["tier"] == "Prata"
    assert repo.season_tier(1700)["tier"] == "Ouro"
    assert repo.season_tier(1900)["tier"] == "Lendário"


def test_soft_reset_halves_distance_from_1500(flask_app):
    repo = _repo(flask_app)
    assert repo._soft_reset_elo(1900) == 1700
    assert repo._soft_reset_elo(1100) == 1300
    assert repo._soft_reset_elo(1500) == 1500


def test_close_season_rewards_resets_and_bumps(flask_app):
    repo = _repo(flask_app)
    uid = _user(repo, "champ")
    with repo.connect() as db:
        db.execute("UPDATE users SET ranking_elo = 1700, ranking_season = 1 WHERE id = ?", (uid,))
    summary = repo.close_season()
    assert summary["rewarded"] >= 1
    with repo.connect() as db:
        row = db.execute("SELECT ranking_elo, ranking_season FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["ranking_elo"] == 1600   # soft-reset 1700 -> 1600
    assert row["ranking_season"] == 2   # season bumped
    assert repo.get_dust(uid) >= 50     # faixa Ouro = 50 pó


def test_close_season_is_idempotent_per_season(flask_app):
    repo = _repo(flask_app)
    uid = _user(repo, "dup")
    with repo.connect() as db:
        db.execute("UPDATE users SET ranking_elo = 1700, ranking_season = 1 WHERE id = ?", (uid,))
    repo.close_season()                       # fecha season 1 (concede)
    dust_after_first = repo.get_dust(uid)
    with repo.connect() as db:                # simula re-rodar a MESMA season
        db.execute("UPDATE users SET ranking_season = 1 WHERE id = ?", (uid,))
    repo.close_season()                       # já tem ledger season:1 -> pula
    assert repo.get_dust(uid) == dust_after_first
