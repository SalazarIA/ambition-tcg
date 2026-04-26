# Ambitionz Database Migration Plan

## Current state

- The project uses Flask-SQLAlchemy and db.create_all().
- Production uses PostgreSQL.
- Local development may use SQLite.

## Known limitation

db.create_all() creates missing tables but does not alter existing tables.

Schema changes currently require manual ALTER TABLE commands or schema helper functions.

## Recommended next step

1. Install Flask-Migrate.
2. Initialize migrations.
3. Generate first baseline migration.
4. Replace manual ALTER TABLE patches with controlled migrations.

## Future commands

```bash
pip install Flask-Migrate
flask db init
flask db migrate -m "baseline"
flask db upgrade
```

## Rules

- Never deploy a model change without a migration.
- Always run local preflight before deploy.
- Always backup production DB before destructive migrations.
