import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT = 8080
BASE_URL = f"http://127.0.0.1:{PORT}"
LOG = ROOT / "reports" / "qa" / "local_server_real_start.log"


def kill_port():
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{PORT}"], text=True).strip()
        for pid in out.splitlines():
            try:
                os.kill(int(pid), signal.SIGKILL)
            except Exception:
                pass
    except Exception:
        pass


def wait_port(timeout=25):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    kill_port()

    env = os.environ.copy()
    env.setdefault("FLASK_ENV", "development")

    with LOG.open("w") as log:
        server = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=str(ROOT),
            stdout=log,
            stderr=log,
            env=env,
        )

        try:
            if not wait_port():
                print("server did not start")
                raise SystemExit(1)

            cmd = [
                sys.executable,
                "tools/qa/qa_browser_real_start_flow.py",
                "--base-url",
                BASE_URL,
            ]

            result = subprocess.run(
                cmd,
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                timeout=90,
            )

            print(result.stdout)
            print(result.stderr)

            if result.returncode != 0:
                print("RESULT=FAIL real_start_local")
                raise SystemExit(result.returncode)

            print("RESULT=PASS real_start_local")

        finally:
            try:
                server.terminate()
                server.wait(timeout=5)
            except Exception:
                try:
                    server.kill()
                except Exception:
                    pass
            kill_port()


if __name__ == "__main__":
    main()
