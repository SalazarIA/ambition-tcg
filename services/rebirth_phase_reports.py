"""Phase report governance for the Rebirth execution plan."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PHASE_REPORTS = {
    0: ROOT / "docs" / "REBIRTH_PHASE_0_READINESS_REPORT.md",
    1: ROOT / "docs" / "REBIRTH_PHASE_1_FIRST_10_MINUTES_REPORT.md",
    2: ROOT / "docs" / "REBIRTH_PHASE_2_HUMAN_TELEMETRY_REPORT.md",
    3: ROOT / "docs" / "REBIRTH_PHASE_3_MODULARIZATION_REPORT.md",
    4: ROOT / "docs" / "REBIRTH_PHASE_4_UX_POLISH_REPORT.md",
    5: ROOT / "docs" / "REBIRTH_PHASE_5_RETENTION_SYSTEMS_REPORT.md",
    6: ROOT / "docs" / "REBIRTH_PHASE_6_CONTENT_EXPANSION_REPORT.md",
    7: ROOT / "docs" / "REBIRTH_PHASE_7_ASYNC_COMPETITION_REPORT.md",
    8: ROOT / "docs" / "REBIRTH_PHASE_8_PUBLIC_BETA_GATE_REPORT.md",
}

REQUIRED_SECTIONS = {
    "status": "## Status",
    "implemented": ("## What Was Implemented", "## Implemented In This Pass"),
    "files_changed": "## Files Changed",
    "tests_executed": "## Tests Executed",
    "coverage": "## Coverage",
    "risks": "## Risks",
    "next_steps": "## Next Steps",
    "project_status": "## Project Status",
}


def _has_section(text, heading):
    headings = heading if isinstance(heading, tuple) else (heading,)
    return any(candidate in text for candidate in headings)


def audit_phase_reports():
    phases = []
    for phase, path in PHASE_REPORTS.items():
        errors = []
        if not path.exists():
            phases.append(
                {
                    "phase": phase,
                    "path": str(path.relative_to(ROOT)),
                    "ok": False,
                    "errors": ["report_missing"],
                }
            )
            continue

        text = path.read_text(encoding="utf-8")
        for key, heading in REQUIRED_SECTIONS.items():
            if not _has_section(text, heading):
                errors.append(f"section_missing:{key}")
        if f"Phase {phase}" not in text and f"Phase_{phase}" not in path.name:
            errors.append("phase_number_missing")

        phases.append(
            {
                "phase": phase,
                "path": str(path.relative_to(ROOT)),
                "ok": not errors,
                "errors": errors,
            }
        )

    return {
        "ok": all(phase["ok"] for phase in phases),
        "required_sections": sorted(REQUIRED_SECTIONS),
        "phases": phases,
    }
