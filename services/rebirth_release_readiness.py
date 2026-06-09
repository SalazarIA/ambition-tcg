"""Final public-beta readiness composition for Rebirth."""

from __future__ import annotations

from typing import Any, Dict, List


REBIRTH_RELEASE_READINESS_VERSION = "rebirth-release-readiness-v1"


def _blocked_check_keys(checks: List[Dict[str, Any]]) -> List[str]:
    return [
        str(check.get("key") or check.get("name") or "").strip()
        for check in checks
        if check.get("state") != "passed"
    ]


def release_readiness_report(external_gates: Dict[str, Any], public_beta_gate: Dict[str, Any]) -> Dict[str, Any]:
    external_checks = list((external_gates or {}).get("checks") or [])
    public_checks = list((public_beta_gate or {}).get("checks") or [])
    external_blockers = _blocked_check_keys(external_checks)
    public_blockers = list((public_beta_gate or {}).get("blockers") or _blocked_check_keys(public_checks))
    ready = bool((external_gates or {}).get("ready")) and bool((public_beta_gate or {}).get("ready"))
    return {
        "version": REBIRTH_RELEASE_READINESS_VERSION,
        "ready": ready,
        "external_ready": bool((external_gates or {}).get("ready")),
        "public_beta_ready": bool((public_beta_gate or {}).get("ready")),
        "external_blockers": external_blockers,
        "public_beta_blockers": public_blockers,
        "blockers": {
            "external": external_blockers,
            "public_beta": public_blockers,
        },
        "summary": {
            "external_passed": len(external_checks) - len(external_blockers),
            "external_total": len(external_checks),
            "public_beta_passed": len(public_checks) - len(public_blockers),
            "public_beta_total": len(public_checks),
        },
    }
