# Ambitionz Rebirth Disaster Recovery Runbook

Updated: 2026-06-08

## Scope

This runbook covers the closed-beta PostgreSQL recovery path for Ambitionz
Rebirth. It is intentionally operational, not architectural: the goal is to
prove that account, collection, loadout, wallet, telemetry, support export and
match-history data can survive a restore drill before external testers are
invited.

Production gameplay remains PostgreSQL-authoritative. SQLite is valid only for
tests or isolated QA with `REBIRTH_ALLOW_SQLITE_TESTING=true`.

## Required Inputs

- Source database URL: `REBIRTH_DATABASE_URL` or `DATABASE_URL`.
- Disposable restore database URL for the drill.
- Current deployed commit SHA.
- Operator name and timestamp for the evidence record.
- A signed-in test account that has collection, progression and match history.

Never paste database credentials into docs, screenshots or issue comments. If a
command must be logged, redact user, password and host when sharing outside the
operator channel.

## Pre-Backup Checks

1. Confirm the app is healthy:

   ```bash
   curl -fsS "$PUBLIC_BASE_URL/health"
   ```

2. Confirm billing remains disabled:

   ```bash
   curl -fsS "$PUBLIC_BASE_URL/api/rebirth/release"
   ```

3. Export one signed-in account from `/rebirth/support` and save the export as
   evidence outside the repo.

## Backup Command

Use a custom-format dump so restore can use `pg_restore` safely.

Recommended operator dry-run:

```bash
REBIRTH_DATABASE_URL="$REBIRTH_DATABASE_URL" \
REBIRTH_RESTORE_DATABASE_URL="$REBIRTH_RESTORE_DATABASE_URL" \
python tools/ops/rebirth_backup_restore_drill.py
```

The dry-run prints redacted database fingerprints, prerequisite status and an
evidence skeleton without executing `pg_restore`.

```bash
mkdir -p /tmp/ambitionz-rebirth-backups
pg_dump "$REBIRTH_DATABASE_URL" \
  --format=custom \
  --no-owner \
  --file="/tmp/ambitionz-rebirth-backups/rebirth-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Expected result: command exits `0` and produces a non-empty `.dump` file.

## Restore Drill

Run the drill against a disposable database, never directly over production.
The helper refuses execution unless the restore target differs from the source
and the disposable-target acknowledgement is present:

```bash
REBIRTH_DATABASE_URL="$REBIRTH_DATABASE_URL" \
REBIRTH_RESTORE_DATABASE_URL="$REBIRTH_RESTORE_DATABASE_URL" \
python tools/ops/rebirth_backup_restore_drill.py \
  --execute \
  --i-understand-restore-target-is-disposable \
  --operator "$USER" \
  --source-commit "$(git rev-parse HEAD)"
```

After `/health` and a signed-in support export pass against the disposable
restore app, re-run or copy the output with `--health-check passed`,
`--support-export-check passed` and a private `--evidence-ref`.

```bash
createdb rebirth_restore_drill
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --dbname=rebirth_restore_drill \
  /tmp/ambitionz-rebirth-backups/rebirth-YYYYMMDDTHHMMSSZ.dump
```

Then validate schema and app-level data against the restored database:

```bash
REBIRTH_DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/rebirth_restore_drill" \
python -m services.rebirth_schema check
```

If the restored database is wired into a disposable app instance, verify:

- `/health` returns healthy.
- signed-in support export still works.
- match history and economy ledger load for the test account.
- `/api/rebirth/release` renders the release dashboard.

## Recovery Decision Tree

- Bad deploy, database healthy: roll back app to the last green commit first.
- Database host/DNS failure: verify Render/Postgres env vars, then restart only
  after confirming the target host and database name in logs.
- Schema migration failure: stop inviting testers, snapshot database, run
  `python -m services.rebirth_schema check`, then apply the smallest migration
  fix on a disposable restore before production.
- Suspected data corruption: stop writes if possible, take an immediate dump,
  preserve logs, export affected accounts, and restore only with owner approval.
- Billing incident: keep `REBIRTH_ENABLE_BILLING=false` and
  `REBIRTH_ALLOW_STRIPE_LIVE=false` while investigating.

## Evidence Record

Record each drill outside source control with:

- date/time UTC;
- source commit SHA;
- source database identifier, redacted;
- dump filename and size;
- restore target identifier, redacted;
- `services.rebirth_schema check` result;
- `/health` result;
- support export result;
- operator;
- unresolved issues.

Set `REBIRTH_BACKUP_RESTORE_DRILL=true` only after the evidence record exists
and the disposable restore has been validated. The public gate accepts
backup/restore evidence only when `drill_at` is no more than 30 days old.

Alternatively, keep the operator evidence outside source control and pass it to
the external gate checker:

```bash
python tools/ops/rebirth_pre_external_gate.py \
  --evidence /secure/path/rebirth-external-gates.json
```

Use `docs/REBIRTH_EXTERNAL_GATE_EVIDENCE.example.json` as the field template,
then remove `"example": true` in the private copy. Never store raw Postgres
URLs, passwords, Sentry DSNs or Stripe keys in the evidence file.

## Legal And Privacy Notes

The LGPD official text is Lei 13.709/2018. ANPD guidance for data subjects and
small treatment agents highlights data-subject rights and the need for a contact
channel. Ambitionz keeps `/rebirth/support`, `/privacy`, `/terms` and
`/data-deletion` reachable so the operator can complete external legal review
before enabling public beta gates.
