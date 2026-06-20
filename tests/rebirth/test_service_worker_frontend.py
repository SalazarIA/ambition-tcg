from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "script",
    [
        "tests/js/test_pwa_controllerchange.cjs",
        "tests/js/test_service_worker_cache_safety.cjs",
    ],
)
def test_service_worker_frontend_regressions(script):
    result = subprocess.run(
        ["node", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
