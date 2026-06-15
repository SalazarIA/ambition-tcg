"""Item 10: pixel-diff baseline gate (pure Pillow)."""
import importlib.util
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("pixel_diff", ROOT / "tools" / "qa" / "pixel_diff.py")
pixel_diff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pixel_diff)


def test_identical_images_zero_diff(tmp_path):
    path = tmp_path / "a.png"
    Image.new("RGB", (40, 40), (10, 20, 30)).save(path)
    result = pixel_diff.image_diff(str(path), str(path))
    assert result["ratio"] == 0.0
    assert result["size_mismatch"] is False


def test_changed_stripe_is_measured(tmp_path):
    base = Image.new("RGB", (100, 100), (0, 0, 0))
    changed = base.copy()
    for x in range(10):  # a 10%-wide white stripe
        for y in range(100):
            changed.putpixel((x, y), (255, 255, 255))
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    base.save(a)
    changed.save(b)
    result = pixel_diff.image_diff(str(a), str(b))
    assert 0.09 <= result["ratio"] <= 0.11  # ~10% of pixels changed


def test_size_mismatch_flagged(tmp_path):
    small, big = tmp_path / "s.png", tmp_path / "b.png"
    Image.new("RGB", (10, 10)).save(small)
    Image.new("RGB", (20, 20)).save(big)
    result = pixel_diff.image_diff(str(small), str(big))
    assert result["size_mismatch"] is True
    assert result["ratio"] == 1.0
