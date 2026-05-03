import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app, build_internal_rc_status


def generate_report():
    with app.app_context():
        status = build_internal_rc_status()

    print("INTERNAL RC STATUS:", status["status_label"])
    print("REQUIRED OK:", status["required_ok"])
    print("RECOMMENDED OK:", status["recommended_ok"])

    for check in status["checks"]:
        marker = "OK" if check["ok"] else "FAIL"
        print(f"{marker}: {check['label']} [{check['priority']}] - {check['detail']}")

    return status


def audit_internal_rc():
    status = generate_report()
    errors = []

    for check in status["checks"]:
        if check["priority"] == "required" and not check["ok"]:
            errors.append(f"Required RC check failed: {check['label']} - {check['detail']}")

    return errors


if __name__ == "__main__":
    failures = audit_internal_rc()

    if failures:
        for failure in failures:
            print("ERROR:", failure)

        raise SystemExit(1)
