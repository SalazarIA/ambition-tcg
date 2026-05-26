#!/usr/bin/env python3
"""Check that product-readiness surfaces belong to the active Rebirth stack."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "app.py",
    "services/rebirth_engine.py",
    "services/rebirth_effects.py",
    "services/rebirth_reducers.py",
    "services/rebirth_replay.py",
    "services/rebirth_parity.py",
    "services/rebirth_profiler.py",
    "services/rebirth_balance.py",
    "services/rebirth_persistence.py",
    "services/rebirth_schema.py",
    "templates/rebirth.html",
    "static/css/rebirth.css",
    "static/js/rebirth.js",
    "tools/rebirth_gameplay_health.py",
    "tools/rebirth_benchmark.py",
    "tools/rebirth_stress_mcts.py",
]


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def main():
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).exists()]
    assert not missing, f"Missing active Rebirth files: {missing}"

    app_py = read("app.py")
    template = read("templates/rebirth.html")
    script = read("static/js/rebirth.js")
    css = read("static/css/rebirth.css")
    schema = read("services/rebirth_schema.py")

    for route in (
        '@app.get("/rebirth")',
        '@app.post("/api/rebirth/start")',
        '@app.post("/api/rebirth/play-card")',
        '@app.post("/api/rebirth/attack")',
        '@app.post("/api/rebirth/telemetry")',
    ):
        assert route in app_py
    assert "require_internal_lab_access()" in app_py
    assert "record_match_telemetry" in app_py
    assert 'id="phase-timeline"' in template
    assert 'id="interrupt-label"' in template
    assert "Confronto vencido" in script
    assert "match_abandoned" in script
    assert ".rb-resolution-strip" in css
    assert "pg_advisory_xact_lock" in schema
    print("PASS qa_product_rebirth_report active_product readiness_contracts")


if __name__ == "__main__":
    main()
