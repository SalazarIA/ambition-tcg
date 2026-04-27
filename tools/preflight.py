import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app
from models import db

from tools.audit_routes import audit_routes, audit_template_endpoints
from tools.audit_files import audit_files
from tools.audit_cards import audit_cards
from tools.audit_database import audit_database
from tools.audit_config import audit_config
from tools.balance_report import generate_report, main as generate_balance_report_file


def run_section(title, func):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)

    try:
        errors = func()
    except Exception as error:
        errors = [f"{title} crashed: {type(error).__name__}: {error}"]

    if errors:
        print(f"{title}: FAILED")

        for error in errors:
            print("ERROR:", error)
    else:
        print(f"{title}: OK")

    return errors


def main():
    all_errors = []

    all_errors += run_section("FILES", audit_files)
    all_errors += run_section("CONFIG", lambda: audit_config(app))
    all_errors += run_section("DATABASE", lambda: audit_database(app, db))
    all_errors += run_section("ROUTES", lambda: audit_routes(app))
    all_errors += run_section("TEMPLATE ENDPOINTS", lambda: audit_template_endpoints(app))
    all_errors += run_section("CARDS", audit_cards)
    all_errors += run_section("BALANCE REPORT", lambda: [] if generate_balance_report_file() is None else [])

    print("\n" + "=" * 72)
    print("AMBITIONZ PREFLIGHT RESULT")
    print("=" * 72)

    if all_errors:
        print("AMBITIONZ PREFLIGHT FAILED")

        for error in all_errors:
            print("ERROR:", error)

        raise SystemExit(1)

    print("AMBITIONZ PREFLIGHT PASSED")


if __name__ == "__main__":
    main()
