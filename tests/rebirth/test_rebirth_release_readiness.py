from services.rebirth_release_readiness import release_readiness_report


def test_release_readiness_requires_external_and_public_beta_gates():
    external = {
        "ready": False,
        "checks": [
            {"key": "legal_review", "state": "blocked"},
            {"key": "github_workflow", "state": "passed"},
        ],
    }
    public = {
        "ready": False,
        "blockers": ["d1_retention"],
        "checks": [
            {"key": "d1_retention", "state": "blocked"},
            {"key": "crash_rate", "state": "passed"},
        ],
    }

    report = release_readiness_report(external, public)

    assert report["ready"] is False
    assert report["external_ready"] is False
    assert report["public_beta_ready"] is False
    assert report["phase_reports_ready"] is True
    assert report["external_blockers"] == ["legal_review"]
    assert report["public_beta_blockers"] == ["d1_retention"]
    assert report["phase_report_blockers"] == []
    assert report["summary"] == {
        "external_passed": 1,
        "external_total": 2,
        "public_beta_passed": 1,
        "public_beta_total": 2,
    }


def test_release_readiness_passes_when_both_gate_groups_pass():
    external = {"ready": True, "checks": [{"key": "legal_review", "state": "passed"}]}
    public = {"ready": True, "blockers": [], "checks": [{"key": "d1_retention", "state": "passed"}]}

    report = release_readiness_report(external, public)

    assert report["ready"] is True
    assert report["blockers"] == {"external": [], "public_beta": [], "phase_reports": []}


def test_release_readiness_requires_phase_reports_when_provided():
    external = {"ready": True, "checks": [{"key": "legal_review", "state": "passed"}]}
    public = {"ready": True, "blockers": [], "checks": [{"key": "d1_retention", "state": "passed"}]}
    phase_reports = {
        "ok": False,
        "phases": [
            {"phase": 0, "ok": True, "errors": []},
            {"phase": 1, "ok": False, "errors": ["section_missing:risks"]},
        ],
    }

    report = release_readiness_report(external, public, phase_report_audit=phase_reports)

    assert report["ready"] is False
    assert report["phase_reports_ready"] is False
    assert report["phase_report_blockers"] == ["phase_1_report"]
    assert report["blockers"]["phase_reports"] == ["phase_1_report"]
    assert report["summary"]["phase_reports_passed"] == 1
    assert report["summary"]["phase_reports_total"] == 2


def test_release_readiness_passes_with_phase_reports_ready():
    external = {"ready": True, "checks": [{"key": "legal_review", "state": "passed"}]}
    public = {"ready": True, "blockers": [], "checks": [{"key": "d1_retention", "state": "passed"}]}
    phase_reports = {
        "ok": True,
        "phases": [
            {"phase": 0, "ok": True, "errors": []},
            {"phase": 1, "ok": True, "errors": []},
        ],
    }

    report = release_readiness_report(external, public, phase_report_audit=phase_reports)

    assert report["ready"] is True
    assert report["phase_reports_ready"] is True
    assert report["phase_report_blockers"] == []
    assert report["summary"]["phase_reports_passed"] == 2
    assert report["summary"]["phase_reports_total"] == 2
