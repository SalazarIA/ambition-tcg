from pathlib import Path

from services import rebirth_schema


class _FakeConnection:
    def __init__(self):
        self.statements = []

    def exec_driver_sql(self, statement):
        self.statements.append(statement)


class _FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        return False


class _FakeEngine:
    def __init__(self):
        self.connection = _FakeConnection()
        self.disposed = False

    def begin(self):
        return _FakeTransaction(self.connection)

    def dispose(self):
        self.disposed = True


def test_legacy_collision_preflight_runs_before_foundation_migration(monkeypatch):
    engine = _FakeEngine()
    monkeypatch.setattr(rebirth_schema, "make_engine", lambda _database_url: engine)

    rebirth_schema.upgrade_schema("postgresql://test")

    statements = engine.connection.statements
    assert "ALTER TABLE users RENAME TO users_legacy_ascension" in statements[0]
    assert statements[1] == rebirth_schema.MIGRATION_001.strip()
    assert engine.disposed is True


def test_fk_recovery_accepts_historical_rows_and_fences_new_user_ids():
    assert rebirth_schema.SCHEMA_VERSION == 6
    assert "pg_get_serial_sequence('users', 'id')" in rebirth_schema.MIGRATION_005
    assert "match_history_legacy_ascension" in rebirth_schema.MIGRATION_005
    assert "NOT LIKE '%%_legacy_ascension'" in rebirth_schema.MIGRATION_005
    assert "ADD CONSTRAINT %%I %%s NOT VALID" in rebirth_schema.MIGRATION_005


def test_database_error_details_are_not_public_by_default():
    source = Path("services/rebirth_persistence.py").read_text()

    assert 'os.environ.get("REBIRTH_EXPOSE_DB_ERRORS", "false")' in source
