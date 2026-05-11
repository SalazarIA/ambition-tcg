
from pathlib import Path
import subprocess
import time
import urllib.request
import os
import signal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = REPORT_DIR / "local_server_browser_qa.log"
BASE_URL = "http://127.0.0.1:8080"


def kill_port_8080():
    try:
        result = subprocess.run(
            ["bash", "-lc", "lsof -ti :8080"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )

        pids = [pid.strip() for pid in result.stdout.splitlines() if pid.strip()]

        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
                print(f"killed_port_8080_pid={pid}")
            except Exception as exc:
                print(f"kill_skip pid={pid} error={type(exc).__name__}:{exc}")

    except Exception as exc:
        print(f"kill_port_8080_error={type(exc).__name__}:{exc}")


def wait_health(timeout_seconds=25):
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL + "/health", timeout=2) as response:
                body = response.read().decode("utf-8", errors="ignore")
                print(f"health_ok status={response.status} body={body[:200]}")
                return True
        except Exception as exc:
            last_error = exc
            time.sleep(1)

    print(f"health_fail last_error={type(last_error).__name__}:{last_error}")
    return False


def latest_report():
    reports = sorted(REPORT_DIR.glob("qa_run_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


def print_report_tail(report, lines=280):
    if not report or not report.exists():
        print("no_report_found")
        return

    print("")
    print(f"=== LAST QA REPORT: {report} ===")

    content = report.read_text(errors="ignore").splitlines()
    for line in content[-lines:]:
        print(line)


def run_command(label, command, timeout=300):
    print("")
    print(f"=== RUN {label} ===")
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )

    print(result.stdout)

    if result.stderr.strip():
        print(f"=== {label} STDERR ===")
        print(result.stderr)

    return result


def main():
    print("=== SAFE LOCAL BROWSER QA ===")
    print(f"project={PROJECT_ROOT}")

    kill_port_8080()

    print("")
    print("=== START LOCAL SERVER ===")

    log_handle = LOG_FILE.open("w")

    server = subprocess.Popen(
        ["python3", "app.py"],
        cwd=PROJECT_ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(f"server_pid={server.pid}")

    try:
        if not wait_health():
            print("RESULT=FAIL reason=health")
            raise SystemExit(1)

        commands = [
            (
                "BROWSER QA",
                [
                    "python3",
                    "tools/qa/ambitionz_qa_agent.py",
                    "--target",
                    "local",
                    "--suite",
                    "browser",
                    "--base-url",
                    BASE_URL,
                ],
                300,
            ),
            (
                "FULL MATCH QA",
                [
                    "python3",
                    "tools/qa/ambitionz_qa_agent.py",
                    "--target",
                    "local",
                    "--suite",
                    "browser_full_match",
                    "--base-url",
                    BASE_URL,
                ],
                360,
            ),
            (
                "MOBILE REAL ROUND QA",
                [
                    "python3",
                    "tools/qa/qa_browser_real_round_flow.py",
                    "--base-url",
                    BASE_URL,
                ],
                240,
            ),
        ]

        results = [run_command(label, command, timeout=timeout) for label, command, timeout in commands]

        report = latest_report()
        print_report_tail(report)

        print("")
        print("=== SERVER LOG TAIL ===")
        if LOG_FILE.exists():
            for line in LOG_FILE.read_text(errors="ignore").splitlines()[-80:]:
                print(line)

        print("")
        failed = [(commands[index][0], result.returncode) for index, result in enumerate(results) if result.returncode != 0]
        if not failed:
            print("RESULT=PASS browser_eagle_eye")
        else:
            print("RESULT=FAIL browser_eagle_eye " + " ".join(f"{label}={code}" for label, code in failed))
            raise SystemExit(1)

    finally:
        print("")
        print("=== STOP LOCAL SERVER ===")
        try:
            server.terminate()
            server.wait(timeout=5)
            print("server_terminated")
        except Exception:
            try:
                server.kill()
                print("server_killed")
            except Exception as exc:
                print(f"server_kill_error={type(exc).__name__}:{exc}")

        log_handle.close()
        kill_port_8080()


if __name__ == "__main__":
    main()
