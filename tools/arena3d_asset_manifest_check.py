import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "static" / "assets" / "arena3d" / "manifest.json"


def iter_asset_entries(section):
    if isinstance(section, dict):
        for value in section.values():
            if isinstance(value, dict):
                yield value


def run():
    data = json.loads(MANIFEST.read_text())
    errors = []

    if data.get("schema") != "ambitionz_arena3d_assets_v1":
        errors.append("manifest schema mismatch")

    if data.get("runtimeFormat") != "glb":
        errors.append("runtimeFormat must be glb")

    for section_name in ["arenas", "cardBacks", "tokens", "fx"]:
        for entry in iter_asset_entries(data.get(section_name, {})):
            model = entry.get("model")
            required = bool(entry.get("required"))

            if not model:
                errors.append(f"{section_name} entry missing model")
                continue

            if not str(model).endswith(".glb"):
                errors.append(f"{section_name} model is not .glb: {model}")

            if required and not (MANIFEST.parent / model).exists():
                errors.append(f"required asset missing: {model}")

    if errors:
        for error in errors:
            print("FAIL", error)
        raise SystemExit(1)

    print("ARENA3D_ASSET_MANIFEST_OK")


if __name__ == "__main__":
    run()
