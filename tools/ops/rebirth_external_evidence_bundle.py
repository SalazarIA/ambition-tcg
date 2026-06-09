#!/usr/bin/env python3
"""Merge and validate secret-free Rebirth external gate evidence blocks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_gate_evidence import validate_external_gate_evidence  # noqa: E402


EVIDENCE_KEYS = {"legal_review", "backup_restore", "error_tracking"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_evidence_block(payload: Mapping[str, Any]) -> dict[str, Any]:
    candidate = payload.get("evidence") if isinstance(payload.get("evidence"), Mapping) else payload
    block = {
        key: candidate[key]
        for key in EVIDENCE_KEYS
        if isinstance(candidate, Mapping) and key in candidate
    }
    if isinstance(candidate, Mapping) and "example" in candidate:
        block["example"] = candidate["example"]
    if not block:
        raise ValueError("evidence_block_missing")
    return block


def merge_evidence_blocks(blocks: list[Mapping[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for block in blocks:
        for key, value in block.items():
            if key == "example":
                merged["example"] = bool(merged.get("example")) or bool(value)
                continue
            if key not in EVIDENCE_KEYS:
                continue
            if key in merged:
                raise ValueError(f"duplicate_evidence_key:{key}")
            merged[key] = value
    return merged


def _has_secret_like_validation_error(validation: Mapping[str, Any]) -> bool:
    for report in validation.values():
        errors = report.get("errors") if isinstance(report, Mapping) else []
        if "secret_like_value_detected" in (errors or []):
            return True
    return False


def _path_inside_repo(path: Path) -> bool:
    try:
        resolved = path.resolve()
        root = ROOT.resolve()
    except OSError:
        return False
    return resolved == root or root in resolved.parents


def build_bundle_payload(evidence: Mapping[str, Any], *, source_paths: list[str]) -> dict[str, Any]:
    validation = validate_external_gate_evidence(evidence)
    secret_like = _has_secret_like_validation_error(validation)
    ok = all(report.get("valid") for report in validation.values() if isinstance(report, Mapping))
    payload = {
        "ok": bool(ok),
        "source_paths": source_paths,
        "validation": validation,
        "secret_like_value_detected": secret_like,
        "notes": [
            "Use the evidence field as the private external evidence JSON only after every validation group is valid.",
            "Do not commit the filled evidence file to source control.",
        ],
    }
    if secret_like:
        payload["evidence_redacted"] = True
        payload["notes"].append("Evidence was not printed because a secret-like value was detected.")
    else:
        payload["evidence"] = dict(evidence)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Rebirth external evidence blocks into one validated bundle.")
    parser.add_argument("inputs", nargs="+", help="JSON files containing evidence blocks or helper command output.")
    parser.add_argument("--output", default="", help="Optional path for the merged secret-free evidence JSON.")
    parser.add_argument(
        "--allow-repo-output",
        action="store_true",
        help="Allow writing inside the repository. Use only for disposable local tests, never real evidence.",
    )
    parser.add_argument("--report-only", action="store_true", help="Print JSON but do not fail on incomplete evidence.")
    args = parser.parse_args()

    source_paths = [str(Path(path)) for path in args.inputs]
    try:
        blocks = [extract_evidence_block(_load_json(Path(path))) for path in args.inputs]
        evidence = merge_evidence_blocks(blocks)
        payload = build_bundle_payload(evidence, source_paths=source_paths)
    except Exception as exc:
        payload = {
            "ok": False,
            "source_paths": source_paths,
            "error": f"{type(exc).__name__}:{exc}",
            "notes": ["No evidence bundle was printed or written."],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if args.report_only else 2

    if args.output and _path_inside_repo(Path(args.output)) and not args.allow_repo_output:
        payload["output"] = None
        payload["output_error"] = "output_path_inside_repo"
        payload["notes"].append("Use an output path outside the repository, such as /secure/path/rebirth-external-gates.json.")
    elif args.output and not payload.get("secret_like_value_detected"):
        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(payload["evidence"], indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        payload["output"] = str(output_path)
    elif args.output:
        payload["output"] = None

    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    if args.report_only:
        return 0
    return 0 if payload["ok"] and not payload.get("secret_like_value_detected") and not payload.get("output_error") else 2


if __name__ == "__main__":
    raise SystemExit(main())
