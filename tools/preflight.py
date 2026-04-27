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
from tools.match_telemetry_report import generate_report as generate_match_telemetry_report
from tools.rewards_report import main as generate_rewards_report_file
from tools.card_identity_report import main as generate_card_identity_report_file
from tools.applied_card_identity_report import main as generate_applied_card_identity_report_file
from tools.progression_loop_report import main as generate_progression_loop_report_file


def run_section(title, func):
    print("\\n" + "=" * 72)
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
    all_errors += run_section("MATCH TELEMETRY REPORT", lambda: [] if generate_match_telemetry_report() else ["Match telemetry report failed"])
    all_errors += run_section("REWARDS REPORT", lambda: [] if generate_rewards_report_file() is None else [])
    all_errors += run_section("CARD IDENTITY REPORT", lambda: [] if generate_card_identity_report_file() is None else [])
    all_errors += run_section("APPLIED CARD IDENTITY REPORT", lambda: [] if generate_applied_card_identity_report_file() is None else [])
    all_errors += run_section("PROGRESSION LOOP REPORT", lambda: [] if generate_progression_loop_report_file() is None else [])

    print("\\n" + "=" * 72)
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
