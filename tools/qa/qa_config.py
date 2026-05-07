from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = PROJECT_ROOT / "reports" / "qa"
SCREENSHOT_ROOT = REPORT_ROOT / "screenshots"

QA_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

DEFAULT_LOCAL_URL = "http://127.0.0.1:8080"
DEFAULT_PRODUCTION_URL = "https://ambitionzgame.com"


def ensure_qa_dirs():
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_ROOT.mkdir(parents=True, exist_ok=True)


def qa_report_path(prefix="qa_run"):
    ensure_qa_dirs()
    return REPORT_ROOT / f"{prefix}_{QA_TIMESTAMP}.md"
