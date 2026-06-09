"""Final public-beta readiness composition for Rebirth."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


REBIRTH_RELEASE_READINESS_VERSION = "rebirth-release-readiness-v1"


def _blocked_check_keys(checks: List[Dict[str, Any]]) -> List[str]:
    return [
        str(check.get("key") or check.get("name") or "").strip()
        for check in checks
        if check.get("state") != "passed"
    ]


def _phase_report_blockers(phase_report_audit: Optional[Dict[str, Any]]) -> List[str]:
    if not phase_report_audit:
        return []
    return [
        f"phase_{phase.get('phase')}_report"
        for phase in phase_report_audit.get("phases") or []
        if not phase.get("ok")
    ]


def release_readiness_report(
    external_gates: Dict[str, Any],
    public_beta_gate: Dict[str, Any],
    phase_report_audit: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    external_checks = list((external_gates or {}).get("checks") or [])
    public_checks = list((public_beta_gate or {}).get("checks") or [])
    external_blockers = _blocked_check_keys(external_checks)
    public_blockers = list((public_beta_gate or {}).get("blockers") or _blocked_check_keys(public_checks))
    phase_report_blockers = _phase_report_blockers(phase_report_audit)
    phase_reports_ready = bool((phase_report_audit or {}).get("ok")) if phase_report_audit is not None else True
    ready = (
        bool((external_gates or {}).get("ready"))
        and bool((public_beta_gate or {}).get("ready"))
        and phase_reports_ready
    )
    report = {
        "version": REBIRTH_RELEASE_READINESS_VERSION,
        "ready": ready,
        "external_ready": bool((external_gates or {}).get("ready")),
        "public_beta_ready": bool((public_beta_gate or {}).get("ready")),
        "phase_reports_ready": phase_reports_ready,
        "external_blockers": external_blockers,
        "public_beta_blockers": public_blockers,
        "phase_report_blockers": phase_report_blockers,
        "blockers": {
            "external": external_blockers,
            "public_beta": public_blockers,
            "phase_reports": phase_report_blockers,
        },
        "summary": {
            "external_passed": len(external_checks) - len(external_blockers),
            "external_total": len(external_checks),
            "public_beta_passed": len(public_checks) - len(public_blockers),
            "public_beta_total": len(public_checks),
        },
    }
    if phase_report_audit is not None:
        phases = list(phase_report_audit.get("phases") or [])
        report["summary"]["phase_reports_passed"] = len(phases) - len(phase_report_blockers)
        report["summary"]["phase_reports_total"] = len(phases)
    return report
