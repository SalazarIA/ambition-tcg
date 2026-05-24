# Ambitionz Rebirth Database Migrations

## Production Rule

PostgreSQL is the only production persistence backend. The active schema is
owned by `services/rebirth_schema.py`; startup never creates or modifies
production tables implicitly.

Render runs the additive migration gate before Gunicorn:

```bash
python -m services.rebirth_schema upgrade
```

The application then rejects `/health` with HTTP `503` unless the connection is
available and the current schema version is installed.

## Current Versions

| Version | Purpose |
| --- | --- |
| `1` | Single PostgreSQL source for accounts, sessions, cards, progression, wallet, immutable ledgers, market, telemetry and match history. |
| `2` | Authoritative `runtime_state_json` for authenticated match recovery after a process restart. |

## Local PostgreSQL Validation

```bash
export REBIRTH_DATABASE_URL='postgresql://user:password@localhost:5432/ambitionz'
python -m services.rebirth_schema upgrade
python -m services.rebirth_schema check
pytest tests/rebirth -m requires_postgres -q
```

SQLite may be used only by isolated local tests through `TESTING` or
`REBIRTH_ALLOW_SQLITE_TESTING=true`; it is not a production fallback.

## Rollout And Rollback

1. Back up the Render PostgreSQL database.
2. Run default pytest, E2E smoke tests and the PostgreSQL-marked tests in CI.
3. Deploy the build; verify the pre-deploy migration succeeds.
4. Verify `/health`, registration, authenticated match resume, booster open and
   market-in-Ouro smoke paths.
5. Roll back application code only after retaining the database backup. Current
   migrations are additive, so old data is preserved; do not delete ledger
   rows during rollback.
