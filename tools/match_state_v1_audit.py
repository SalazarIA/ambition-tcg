from services.match_state_v1 import build_match_state_v1

card = {
    "id": "base_audit_001",
    "name": "Audit Monster",
    "type": "Monster",
    "element": "Fire",
    "rarity": "Common",
    "sigil": "Fury",
    "role": "Aggressor",
    "cost": 1,
    "power": 2,
    "effect": "Audit effect.",
}

match = {
    "id": "audit_match",
    "training": True,
    "round": 1,
    "p1": {
        "sid": "sid1",
        "name": "Player",
        "hp": 3600,
        "energy": 2,
        "max_energy": 2,
        "ambition": 0,
        "intent": None,
        "ready": False,
        "hand": [card],
        "field": {},
        "deck": [],
    },
    "p2": {
        "sid": "sid2",
        "name": "Bot",
        "hp": 3600,
        "energy": 2,
        "max_energy": 2,
        "ambition": 0,
        "intent": None,
        "ready": False,
        "hand": [card, card],
        "field": {},
        "deck": [],
    },
}

payload = build_match_state_v1(match, viewer_key="p1")

print("# Match State V1 Audit")
print("schema", payload["schema"])
print("mode", payload["mode"])
print("round", payload["round"])
print("phase", payload["phase"])
print("me.hand", len(payload["me"]["hand"]))
print("enemy.hand_count", payload["enemy"]["hand_count"])
print("playable", payload["legal_actions"]["playable_card_ids"])
print("message", payload["message"])

required = [
    "schema",
    "match_id",
    "mode",
    "round",
    "phase",
    "me",
    "enemy",
    "legal_actions",
    "message",
]

missing = [key for key in required if key not in payload]

if missing:
    raise SystemExit(f"MISSING KEYS: {missing}")

if payload["schema"] != "ambitionz_match_v1":
    raise SystemExit("BAD SCHEMA")

if not payload["me"]["hand"]:
    raise SystemExit("HAND NOT EXPORTED")

print("MATCH_STATE_V1_AUDIT_PASSED")
