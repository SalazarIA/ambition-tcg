#!/usr/bin/env python3
"""Run or plan a Rebirth PostgreSQL backup/restore drill.

The default mode is a dry run. Execution requires --execute plus an explicit
acknowledgement that the restore target is disposable. The tool never prints
raw database URLs.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _db_fingerprint(url: str) -> dict:
    parsed = urlsplit(url or "")
    return {
        "scheme": parsed.scheme,
        "host": parsed.hostname or "",
        "port": parsed.port,
        "database": (parsed.path or "").lstrip("/"),
    }


def _same_database(left: str, right: str) -> bool:
    left_fp = _db_fingerprint(left)
    right_fp = _db_fingerprint(right)
    return bool(left_fp["host"] and left_fp == right_fp)


def _command_status(name: str) -> dict:
    return {"name": name, "available": bool(shutil.which(name))}


def _run(command: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, env=env, check=True, text=True, capture_output=True)


def build_evidence_payload(
    *,
    validated: bool,
    operator: str,
    source_commit: str,
    dump_path: Path,
    restore_target: str,
    schema_check: str = "pending",
    health_check: str = "pending",
    support_export_check: str = "pending",
    evidence_ref: str = "",
    drill_at: str | None = None,
    unresolved_issues: list[str] | None = None,
) -> dict:
    dump_bytes = dump_path.stat().st_size if dump_path.exists() else 0
    return {
        "backup_restore": {
            "validated": bool(validated),
            "drill_at": drill_at or utc_now(),
            "operator": operator,
            "source_commit": source_commit,
            "source_database": "redacted-source-db",
            "dump_filename": dump_path.name,
            "dump_bytes": dump_bytes,
            "restore_target": restore_target,
            "schema_check": schema_check,
            "health_check": health_check,
            "support_export_check": support_export_check,
            "unresolved_issues": unresolved_issues or [],
            "evidence_ref": evidence_ref,
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a safe Rebirth Postgres backup/restore drill.")
    parser.add_argument("--execute", action="store_true", help="Run pg_dump, pg_restore and schema check.")
    parser.add_argument("--source-url-env", default="REBIRTH_DATABASE_URL")
    parser.add_argument("--restore-url-env", default="REBIRTH_RESTORE_DATABASE_URL")
    parser.add_argument("--operator", default=os.environ.get("USER") or "operator")
    parser.add_argument("--source-commit", default=os.environ.get("RENDER_GIT_COMMIT", "local"))
    parser.add_argument("--dump-dir", default="/tmp/ambitionz-rebirth-backups")
    parser.add_argument("--dump-file", default="")
    parser.add_argument("--restore-target-label", default="redacted-disposable-restore-db")
    parser.add_argument("--evidence-ref", default="")
    parser.add_argument("--health-check", choices=("pending", "passed"), default="pending")
    parser.add_argument("--support-export-check", choices=("pending", "passed"), default="pending")
    parser.add_argument(
        "--i-understand-restore-target-is-disposable",
        action="store_true",
        help="Required with --execute because pg_restore uses --clean --if-exists.",
    )
    args = parser.parse_args()

    source_url = os.environ.get(args.source_url_env, "").strip() or os.environ.get("DATABASE_URL", "").strip()
    restore_url = os.environ.get(args.restore_url_env, "").strip()
    dump_dir = Path(args.dump_dir)
    dump_path = Path(args.dump_file) if args.dump_file else dump_dir / f"rebirth-{utc_now().replace(':', '').replace('-', '')}.dump"

    prerequisites = [_command_status("pg_dump"), _command_status("pg_restore")]
    missing = [item["name"] for item in prerequisites if not item["available"]]
    issues: list[str] = []
    if missing:
        issues.append("missing_commands:" + ",".join(missing))
    if not source_url:
        issues.append(f"{args.source_url_env}_missing")
    if args.execute and not restore_url:
        issues.append(f"{args.restore_url_env}_missing")
    if restore_url and _same_database(source_url, restore_url):
        issues.append("restore_target_matches_source")
    if args.execute and not args.i_understand_restore_target_is_disposable:
        issues.append("disposable_restore_ack_required")

    if issues or not args.execute:
        payload = {
            "ok": not issues and not args.execute,
            "executed": False,
            "mode": "dry_run",
            "source": _db_fingerprint(source_url) if source_url else None,
            "restore": _db_fingerprint(restore_url) if restore_url else None,
            "prerequisites": prerequisites,
            "issues": issues,
            "evidence": build_evidence_payload(
                validated=False,
                operator=args.operator,
                source_commit=args.source_commit,
                dump_path=dump_path,
                restore_target=args.restore_target_label,
                unresolved_issues=issues or ["dry_run_only"],
                evidence_ref=args.evidence_ref,
            ),
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 2 if args.execute and issues else 0

    dump_dir.mkdir(parents=True, exist_ok=True)
    _run(["pg_dump", source_url, "--format=custom", "--no-owner", f"--file={dump_path}"])
    _run(["pg_restore", "--clean", "--if-exists", "--no-owner", f"--dbname={restore_url}", str(dump_path)])
    schema_env = dict(os.environ)
    schema_env["REBIRTH_DATABASE_URL"] = restore_url
    _run([sys.executable, "-m", "services.rebirth_schema", "check"], env=schema_env)

    evidence = build_evidence_payload(
        validated=args.health_check == "passed" and args.support_export_check == "passed",
        operator=args.operator,
        source_commit=args.source_commit,
        dump_path=dump_path,
        restore_target=args.restore_target_label,
        schema_check="passed",
        health_check=args.health_check,
        support_export_check=args.support_export_check,
        evidence_ref=args.evidence_ref,
        unresolved_issues=[] if args.health_check == "passed" and args.support_export_check == "passed" else ["health_or_support_export_pending"],
    )
    payload = {
        "ok": True,
        "executed": True,
        "dump_file": dump_path.name,
        "dump_bytes": dump_path.stat().st_size,
        "restore_target": args.restore_target_label,
        "evidence": evidence,
        "notes": [
            "No database URL was printed.",
            "Evidence becomes gate-valid only when health_check and support_export_check are passed.",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
