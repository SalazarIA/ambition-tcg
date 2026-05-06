from services.arena_payload import build_arena_state_payload


sample_card = {
    "id": "audit_monster_001",
    "name": "Audit Vanguard",
    "type": "Monster",
    "element": "Fire",
    "rarity": "Common",
    "sigil": "Fury",
    "role": "Aggressor",
    "cost": 1,
    "power": 2,
    "effect": "Audit card.",
}

sample_match = {
    "round": 1,
    "phase": "Intent",
    "training": True,
    "p1": {
        "sid": "sid_p1",
        "user_id": 1,
        "name": "Player",
        "hp": 3600,
        "energy": 2,
        "max_energy": 2,
        "ambition": 0,
        "intent": "Strike",
        "ready": False,
        "hand": [sample_card],
        "deck": [],
        "graveyard": [],
        "field": {
            "monster": None,
            "spell": None,
            "trap": None,
        },
    },
    "p2": {
        "sid": "sid_p2",
        "user_id": 2,
        "name": "Bot",
        "hp": 3600,
        "energy": 2,
        "max_energy": 2,
        "ambition": 0,
        "intent": "Hidden",
        "ready": False,
        "hand": [sample_card, sample_card],
        "deck": [],
        "graveyard": [],
        "field": {},
    },
}

payload = build_arena_state_payload(sample_match, viewer_key="p1")

print("# Arena Payload Audit")
print("schema", payload.get("schema"))
print("round", payload.get("round"))
print("phase", payload.get("phase"))
print("me.name", payload["me"]["name"])
print("me.hand.count", len(payload["me"]["hand"]))
print("enemy.name", payload["enemy"]["name"])
print("enemy.hand_count", payload["enemy"]["hand_count"])
print("top_level_hand.count", len(payload["hand"]))

required = [
    "schema",
    "round",
    "phase",
    "me",
    "enemy",
    "hand",
    "my_hand",
    "enemy_hand_count",
]

missing = [key for key in required if key not in payload]

if missing:
    raise SystemExit(f"MISSING KEYS: {missing}")

if not payload["me"]["hand"]:
    raise SystemExit("MISSING ME HAND")

print("ARENA PAYLOAD AUDIT PASSED")
