# Ambitionz Database Migrations

Ambitionz now supports Flask-Migrate/Alembic.

## Current Strategy

The project still keeps the beta schema guards:

- ensure_database_schema()
- ensure_liveops_schema(app)
- db.create_all()

They are kept temporarily as safety fallback while the migration workflow is introduced.

## Local setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Initialize migrations if the folder does not exist:

```bash
flask --app app db init
```

Create an empty baseline revision for existing databases:

```bash
flask --app app db revision -m "baseline existing schema"
```

Mark the current database as latest without applying destructive changes:

```bash
flask --app app db stamp head
```

For future model changes:

```bash
flask --app app db migrate -m "describe change"
flask --app app db upgrade
```

## Production rule

Do not run destructive migrations on Render without a database backup.

Recommended production order:

1. Confirm deploy boots successfully.
2. Confirm /health.
3. Backup PostgreSQL.
4. Run migration command only when needed.
5. Confirm /health again.
6. Run login/register/training smoke tests.

## Important

db.create_all() does not alter existing tables. Alembic should become the source of truth after baseline.
