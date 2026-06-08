#!/usr/bin/env python3
"""Smoke-test Rebirth Sentry/GlitchTip error tracking.

This tool never prints the DSN. By default it performs a dry run. Use --send in
the target environment to emit a test event, then pass --confirmed-evidence-ref
only after the operator confirms the event exists in Sentry/GlitchTip.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_evidence_payload(
    *,
    provider: str,
    environment: str,
    event_id: str = "",
    confirmed_evidence_ref: str = "",
    tested_at: str | None = None,
) -> dict:
    return {
        "error_tracking": {
            "validated": bool(event_id and confirmed_evidence_ref),
            "provider": provider,
            "environment": environment,
            "test_event_id": event_id,
            "tested_at": tested_at or utc_now(),
            "evidence_ref": confirmed_evidence_ref,
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a Rebirth error-tracking smoke event.")
    parser.add_argument("--send", action="store_true", help="Actually send a test event through sentry-sdk.")
    parser.add_argument("--provider", default=os.environ.get("SENTRY_PROVIDER", "sentry-compatible"))
    parser.add_argument("--environment", default=os.environ.get("SENTRY_ENVIRONMENT", "closed-beta"))
    parser.add_argument("--release", default=os.environ.get("REBIRTH_RELEASE_VERSION", "rebirth-smoke"))
    parser.add_argument("--message", default="Ambitionz Rebirth closed-beta error-tracking smoke")
    parser.add_argument(
        "--confirmed-evidence-ref",
        default="",
        help="Private ticket/event reference after the operator confirms the event in the provider.",
    )
    parser.add_argument("--flush-timeout", type=float, default=5.0)
    args = parser.parse_args()

    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        payload = {
            "ok": False,
            "sent": False,
            "error": "SENTRY_DSN_missing",
            "evidence": build_evidence_payload(provider=args.provider, environment=args.environment),
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 2 if args.send else 0

    if not args.send:
        payload = {
            "ok": True,
            "sent": False,
            "dsn_configured": True,
            "message": "Dry run only. Re-run with --send in the target environment.",
            "evidence": build_evidence_payload(provider=args.provider, environment=args.environment),
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    try:
        import sentry_sdk
    except Exception as exc:
        payload = {
            "ok": False,
            "sent": False,
            "error": f"sentry_sdk_import_failed:{type(exc).__name__}",
            "evidence": build_evidence_payload(provider=args.provider, environment=args.environment),
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 2

    sentry_sdk.init(
        dsn=dsn,
        environment=args.environment,
        release=args.release,
        traces_sample_rate=0.0,
    )
    event_id = str(sentry_sdk.capture_message(args.message, level="warning") or "")
    sentry_sdk.flush(timeout=args.flush_timeout)
    evidence = build_evidence_payload(
        provider=args.provider,
        environment=args.environment,
        event_id=event_id,
        confirmed_evidence_ref=args.confirmed_evidence_ref,
    )
    payload = {
        "ok": bool(event_id),
        "sent": bool(event_id),
        "event_id": event_id,
        "release": args.release,
        "evidence": evidence,
        "notes": [
            "No DSN was printed.",
            "The evidence is valid only after --confirmed-evidence-ref is set from a private provider/ticket record.",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if event_id else 1


if __name__ == "__main__":
    raise SystemExit(main())
