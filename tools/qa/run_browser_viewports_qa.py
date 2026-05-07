
from pathlib import Path
import subprocess
import time
import urllib.request
import os
import signal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://127.0.0.1:8080"
LOG_FILE = REPORT_DIR / "local_server_browser_viewports.log"


def kill_port():
    result = subprocess.run(
        ["bash", "-lc", "lsof -ti :8080"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    for pid in [p.strip() for p in result.stdout.splitlines() if p.strip()]:
        try:
            os.kill(int(pid), signal.SIGKILL)
            print(f"killed_pid={pid}")
        except Exception:
            pass


def wait_health():
    for _ in range(25):
        try:
            with urllib.request.urlopen(BASE_URL + "/health", timeout=2) as response:
                print(f"health_ok={response.status}")
                return True
        except Exception:
            time.sleep(1)

    return False


def main():
    kill_port()

    log_handle = LOG_FILE.open("w")
    server = subprocess.Popen(
        ["python3", "app.py"],
        cwd=PROJECT_ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(f"server_pid={server.pid}")

    ok = False

    try:
        if not wait_health():
            print("RESULT=FAIL health")
            return

        result = subprocess.run(
            [
                "python3",
                "tools/qa/ambitionz_qa_agent.py",
                "--target",
                "local",
                "--suite",
                "browser_viewports",
                "--base-url",
                BASE_URL,
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=280,
        )

        print(result.stdout)

        if result.stderr.strip():
            print("=== STDERR ===")
            print(result.stderr)

        ok = result.returncode == 0

        print("RESULT=" + ("PASS browser_viewports" if ok else "FAIL browser_viewports"))

    finally:
        try:
            server.terminate()
            server.wait(timeout=5)
        except Exception:
            try:
                server.kill()
            except Exception:
                pass

        log_handle.close()
        kill_port()

    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
