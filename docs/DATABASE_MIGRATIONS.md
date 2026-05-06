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

Render is configured with:

```yaml
preDeployCommand: flask --app app db upgrade
```

This keeps migrations separate from the Gunicorn start command. Treat every model/schema change as a deploy gate: create the Alembic revision locally, review it, commit it, then take a Render PostgreSQL backup before deploying the build that contains it.

Recommended production order:

1. Confirm the migration revision exists in `migrations/versions`.
2. Review the generated migration for destructive operations.
3. Run tests locally.
4. Backup PostgreSQL in Render.
5. Deploy the candidate build.
6. Confirm the pre-deploy migration step passed.
7. Confirm `/health`.
8. Run login/register/training/arena smoke tests.

## Important

db.create_all() does not alter existing tables. Alembic should become the source of truth after baseline.
