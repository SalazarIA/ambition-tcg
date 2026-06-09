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
    assert report["external_blockers"] == ["legal_review"]
    assert report["public_beta_blockers"] == ["d1_retention"]
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
    assert report["blockers"] == {"external": [], "public_beta": []}
