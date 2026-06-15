#!/usr/bin/env python3
"""Pre-migration Postgres backup — runs before the schema upgrade on deploy.

Best-effort by default: it logs and exits 0 when there is nothing to back up
(no DB URL, or SQLite) or when ``pg_dump`` is unavailable, so a misconfigured
backup never blocks a deploy. Once a durable destination is provisioned, set
``REBIRTH_BACKUP_REQUIRED=true`` to make failures fatal (exit 1).

Destination: ``REBIRTH_BACKUP_DIR`` (default ``/tmp/rebirth-backups``). For real
off-site durability, point it at a mounted Render disk or sync the artifact to
object storage — see docs/REBIRTH_DISASTER_RECOVERY_RUNBOOK.md.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def database_url() -> str:
    return (os.environ.get("REBIRTH_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()


def is_postgres(url: str) -> bool:
    return url.startswith("postgres://") or url.startswith("postgresql://")


def _required() -> bool:
    return os.environ.get("REBIRTH_BACKUP_REQUIRED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _finish(message: str, ok: bool = True) -> int:
    print(f"[backup] {message}")
    if ok:
        return 0
    return 1 if _required() else 0


def _prune(backup_dir: Path, keep: int) -> None:
    if keep <= 0:
        return
    files = sorted(backup_dir.glob("rebirth_predeploy_*.sql.gz"))
    for old in files[:-keep]:
        old.unlink(missing_ok=True)


def main() -> int:
    url = database_url()
    if not url:
        return _finish("no DATABASE_URL configured; skipping (SQLite/dev).")
    if not is_postgres(url):
        return _finish("non-Postgres DATABASE_URL; skipping.")
    if shutil.which("pg_dump") is None:
        return _finish("pg_dump not found on PATH; cannot create backup.", ok=False)
    if shutil.which("gzip") is None:
        return _finish("gzip not found on PATH; cannot compress backup.", ok=False)

    backup_dir = Path(os.environ.get("REBIRTH_BACKUP_DIR", "/tmp/rebirth-backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = backup_dir / f"rebirth_predeploy_{stamp}.sql.gz"

    try:
        with open(out, "wb") as handle:
            dump = subprocess.Popen(
                ["pg_dump", "--no-owner", "--no-privileges", url], stdout=subprocess.PIPE
            )
            gzip_proc = subprocess.Popen(["gzip", "-c"], stdin=dump.stdout, stdout=handle)
            if dump.stdout:
                dump.stdout.close()
            gzip_rc = gzip_proc.wait()
            dump_rc = dump.wait()
    except Exception as exc:  # noqa: BLE001
        out.unlink(missing_ok=True)
        return _finish(f"backup error: {exc}", ok=False)

    if dump_rc != 0 or gzip_rc != 0:
        out.unlink(missing_ok=True)
        return _finish(f"pg_dump failed (dump rc={dump_rc}, gzip rc={gzip_rc}).", ok=False)

    _prune(backup_dir, keep=int(os.environ.get("REBIRTH_BACKUP_KEEP", "5")))
    return _finish(f"wrote {out} ({out.stat().st_size} bytes).")


if __name__ == "__main__":
    sys.exit(main())
