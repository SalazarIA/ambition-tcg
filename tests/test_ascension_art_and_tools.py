import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ascension_art_manifest_is_valid():
    manifest_path = PROJECT_ROOT / "static" / "assets" / "ascension" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    assert manifest["version"] == "ascension_art_manifest_v1"
    assert "cards" in manifest
    assert "champions" in manifest
    assert "ui" in manifest


def test_ascension_balance_sim_runs_lightweight_check():
    result = subprocess.run(
        [sys.executable, "tools/qa/qa_ascension_balance_sim.py", "--matches", "10", "--no-write"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Ascension Balance Report" in result.stdout
    assert "Matches simulated: 10" in result.stdout
