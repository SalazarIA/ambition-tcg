#!/usr/bin/env python3
"""Pixel-diff gate for the committed visual baselines.

Audit/Codex ask: a pixel-diff (or formal visual approval) on top of the
committed screenshots. This compares freshly captured screenshots against the
baselines under tests/rebirth/visual_baselines/ and fails when any surface
drifts beyond a tolerance — turning the baselines from passive artifacts into an
actual regression gate.

Pure Pillow (no numpy): the per-pixel luminance difference is thresholded into a
mask and counted via the (C-level) histogram, so even ~1MP screenshots compare
fast.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE_MANIFEST = PROJECT_ROOT / "tests" / "rebirth" / "visual_baselines" / "manifest.json"


def image_diff(path_a, path_b, channel_threshold: int = 12) -> dict:
    """Return the fraction of pixels that differ beyond ``channel_threshold``."""
    a = Image.open(path_a).convert("RGB")
    b = Image.open(path_b).convert("RGB")
    if a.size != b.size:
        return {"size_mismatch": True, "size_a": a.size, "size_b": b.size, "ratio": 1.0, "mismatched": None}
    diff = ImageChops.difference(a, b).convert("L")
    mask = diff.point(lambda p: 255 if p > channel_threshold else 0)
    mismatched = mask.histogram()[255]
    total = a.size[0] * a.size[1]
    return {
        "size_mismatch": False,
        "ratio": round(mismatched / total, 6) if total else 0.0,
        "mismatched": mismatched,
        "total": total,
    }


def diff_against_baselines(current_dir, *, manifest_path=DEFAULT_BASELINE_MANIFEST, tolerance: float = 0.02) -> dict:
    """Compare ``{current_dir}/{name}.png`` against each baseline screenshot."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    current_dir = Path(current_dir)
    results = []
    for shot in manifest.get("screenshots", []):
        name = shot["name"]
        baseline = PROJECT_ROOT / shot["screenshot"]
        candidate = current_dir / f"{name}.png"
        if not candidate.exists():
            results.append({"name": name, "status": "missing_candidate", "ratio": None})
            continue
        if not baseline.exists():
            results.append({"name": name, "status": "missing_baseline", "ratio": None})
            continue
        diff = image_diff(str(baseline), str(candidate))
        ok = (not diff["size_mismatch"]) and diff["ratio"] <= tolerance
        results.append({
            "name": name,
            "status": "pass" if ok else "fail",
            "ratio": diff["ratio"],
            "size_mismatch": diff["size_mismatch"],
        })
    failed = [r for r in results if r["status"] != "pass"]
    return {"ok": not failed, "tolerance": tolerance, "results": results, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Pixel-diff captured screenshots against baselines")
    parser.add_argument("current_dir", help="Directory with freshly captured {name}.png screenshots")
    parser.add_argument("--manifest", default=str(DEFAULT_BASELINE_MANIFEST))
    parser.add_argument("--tolerance", type=float, default=0.02)
    args = parser.parse_args()

    report = diff_against_baselines(args.current_dir, manifest_path=args.manifest, tolerance=args.tolerance)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["ok"]:
        print("RESULT=PASS pixel_diff")
        return 0
    print(f"RESULT=FAIL pixel_diff ({len(report['failed'])} surface(s) drifted)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
