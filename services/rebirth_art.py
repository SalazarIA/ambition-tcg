from copy import deepcopy
import re


REBIRTH_ART_VERSION = "v76_RELEASE_POLISH-1"
ART_BASE_PATH = "/static/assets/rebirth/cards"


CARD_ART_PROFILES = {
    "dreadclaw": {
        "art_key": "rebirth.monster.dreadclaw.reference.v1",
        "path": f"{ART_BASE_PATH}/dreadclaw-art.webp",
        "status": "approved_reference_crop",
        "silhouette": "volcanic quadruped beast with obsidian plates",
        "finish": "cinematic raster crop",
        "palette": {
            "accent": "#f4ad26",
            "secondary": "#ff6a2a",
            "shadow": "#090605",
        },
        "prompt": "Volcanic black beast with amber magma cracks, premium dark battler card art, no text.",
    },
    "dreadmaw": {
        "art_key": "rebirth.monster.dreadmaw.apex.v1",
        "path": f"{ART_BASE_PATH}/dreadmaw-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "larger apex volcanic beast with crown-like back spikes",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#ffb22e",
            "secondary": "#ff4a1f",
            "shadow": "#070403",
        },
        "prompt": "Apex volcanic monster, crown of obsidian spikes, molten chest, premium dark card art, no text.",
    },
    "stoneshell": {
        "art_key": "rebirth.monster.stoneshell.guardian.v1",
        "path": f"{ART_BASE_PATH}/stoneshell-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "low armored stone guardian with shell plates",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#d2b574",
            "secondary": "#72cda3",
            "shadow": "#0a0d0a",
        },
        "prompt": "Low stone guardian with layered shell armor and emerald cracks, premium dark card art, no text.",
    },
    "stonewarden": {
        "art_key": "rebirth.monster.stonewarden.evolved.v1",
        "path": f"{ART_BASE_PATH}/stonewarden-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "upright stone sentinel shield body",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#e1c37d",
            "secondary": "#8ff0b7",
            "shadow": "#080b08",
        },
        "prompt": "Evolved upright stone sentinel with shield chest and green mineral seams, premium dark card art, no text.",
    },
    "shadewisp": {
        "art_key": "rebirth.monster.shadewisp.assassin.v1",
        "path": f"{ART_BASE_PATH}/shadewisp-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "knife-shaped shadow assassin",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#b7a7ff",
            "secondary": "#f0ad35",
            "shadow": "#05060b",
        },
        "prompt": "Blade-like shadow assassin with violet edges and one cyan eye, premium dark card art, no text.",
    },
    "skywarden": {
        "art_key": "rebirth.monster.skywarden.avian.v1",
        "path": f"{ART_BASE_PATH}/skywarden-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "armored avian sentinel with wide wings",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#dfe8ef",
            "secondary": "#69d8ff",
            "shadow": "#071019",
        },
        "prompt": "Armored avian sentinel with broad wings and bright sky edge light, premium dark card art, no text.",
    },
    "stormwarden": {
        "art_key": "rebirth.monster.stormwarden.evolved.v1",
        "path": f"{ART_BASE_PATH}/stormwarden-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "storm avian diving through lightning",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#f2f7ff",
            "secondary": "#56d7ff",
            "shadow": "#06111c",
        },
        "prompt": "Evolved storm avian diving with lightning wing blades, premium dark card art, no text.",
    },
    "ironbastion": {
        "art_key": "rebirth.monster.ironbastion.guardian.v1",
        "path": f"{ART_BASE_PATH}/ironbastion-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "heavy iron guardian knight",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#c7c9c7",
            "secondary": "#f5b646",
            "shadow": "#090a0b",
        },
        "prompt": "Heavy iron guardian knight with black steel armor and gold rim light, premium dark card art, no text.",
    },
    "ironbulwark": {
        "art_key": "rebirth.monster.ironbulwark.evolved.v1",
        "path": f"{ART_BASE_PATH}/ironbulwark-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "fortress-like iron titan shield form",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#dadbd7",
            "secondary": "#ffc75d",
            "shadow": "#08090a",
        },
        "prompt": "Evolved fortress iron titan with massive shield shoulders and gold furnace core, premium dark card art, no text.",
    },
    "embermaw": {
        "art_key": "rebirth.monster.embermaw.wyrm.v1",
        "path": f"{ART_BASE_PATH}/embermaw-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "serpentine fire wyrm with ember jaws",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#ffbf45",
            "secondary": "#ff5630",
            "shadow": "#100504",
        },
        "prompt": "Serpentine fire wyrm with ember jaws and molten wings, premium dark card art, no text.",
    },
    "embermaw_alpha": {
        "art_key": "rebirth.monster.embermaw-alpha.evolved.v1",
        "path": f"{ART_BASE_PATH}/embermaw-alpha-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "alpha fire wyrm with crown horns and furnace chest",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#ffd268",
            "secondary": "#ff3d1f",
            "shadow": "#100403",
        },
        "prompt": "Evolved alpha fire wyrm with crown horns, furnace chest and ash storm, premium dark card art, no text.",
    },
    "voidstalker": {
        "art_key": "rebirth.monster.voidstalker.hunter.v1",
        "path": f"{ART_BASE_PATH}/voidstalker-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "void hunter with long predatory frame",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#5edbff",
            "secondary": "#8d6cff",
            "shadow": "#030509",
        },
        "prompt": "Long void hunter emerging from a black rift with cyan eyes and violet edges, premium dark card art, no text.",
    },
    "nightfang": {
        "art_key": "rebirth.monster.nightfang.beast.v1",
        "path": f"{ART_BASE_PATH}/nightfang-art.webp",
        "status": "deterministic_premium_png",
        "silhouette": "lean dark beast mid-lunge",
        "finish": "procedural cinematic raster",
        "palette": {
            "accent": "#93a2ff",
            "secondary": "#f0b54a",
            "shadow": "#050509",
        },
        "prompt": "Lean night beast lunging through black smoke, sharp fangs and blue-violet rim light, premium dark card art, no text.",
    },
}


def _generic_palette(card_id):
    number = int(str(card_id).split("_")[-1])
    if number <= 20:
        return {"accent": "#ffb347", "secondary": "#ff5b35", "shadow": "#2a0f0b"}
    if number <= 40:
        return {"accent": "#b8fff6", "secondary": "#37c7ff", "shadow": "#092033"}
    if number <= 60:
        return {"accent": "#f0e2a0", "secondary": "#8bd05f", "shadow": "#17220d"}
    if number <= 80:
        return {"accent": "#f2d9ff", "secondary": "#9b5cff", "shadow": "#221437"}
    if number <= 90:
        return {"accent": "#f9e27d", "secondary": "#2f245f", "shadow": "#ffffff"}
    return {"accent": "#ff4f8b", "secondary": "#181022", "shadow": "#ffc6df"}


def art_profile(card_id):
    if card_id in CARD_ART_PROFILES:
        return deepcopy(CARD_ART_PROFILES[card_id])
    if re.fullmatch(r"card_\d{3}", str(card_id or "")):
        return {
            "art_key": f"rebirth.card.{card_id}.v1",
            "path": f"static/img/cards/baralho/{int(str(card_id).split('_')[-1])}.webp",
            "status": "optimized_webp_path",
            "silhouette": "tcg catalog sigil",
            "finish": "tcg card frame",
            "palette": _generic_palette(card_id),
            "prompt": f"Ambitionz Rebirth premium card art placeholder for {card_id}.",
        }
    raise KeyError(card_id)


def attach_art_profile(card):
    profile = art_profile(card["id"])
    card["art"] = profile["path"]
    card["art_key"] = profile["art_key"]
    card["art_version"] = REBIRTH_ART_VERSION
    card["art_status"] = profile["status"]
    card["art_finish"] = profile["finish"]
    card["silhouette"] = profile["silhouette"]
    card["palette"] = deepcopy(profile["palette"])
    return card


def active_art_paths():
    return sorted({profile["path"] for profile in CARD_ART_PROFILES.values()})


def art_manifest_payload():
    return {
        "product": "Ambitionz Rebirth",
        "version": REBIRTH_ART_VERSION,
        "cards": {
            card_id: {
                "art_key": profile["art_key"],
                "path": profile["path"],
                "status": profile["status"],
                "silhouette": profile["silhouette"],
                "finish": profile["finish"],
                "palette": deepcopy(profile["palette"]),
                "prompt": profile["prompt"],
            }
            for card_id, profile in CARD_ART_PROFILES.items()
        },
    }
