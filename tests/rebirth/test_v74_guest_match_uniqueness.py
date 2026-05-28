"""Audit fix #1: guest matches must not collide on a shared match_id.

Pre-fix, `start_match()` with no seed hashed the constant
"rebirth-default-seed", so every guest match got id rebirth-963745ae6ffc.
Concurrent guests overwrote each other in MATCH_STORE (cross-player state
leak) and `choose_personality` always returned the same profile. This locks
the fix: unseeded matches get fresh ids and the bot profile varies.
"""

from services.rebirth_engine import start_match
from services.rebirth_match_store import RebirthMatchStore


def test_unseeded_matches_get_unique_ids():
    ids = {start_match()["match_id"] for _ in range(40)}
    # Collisions would crush this far below 40; allow a tiny birthday margin.
    assert len(ids) >= 39, f"guest match_ids collided: only {len(ids)} unique of 40"


def test_unseeded_matches_vary_bot_profile():
    profiles = {start_match()["bot_profile"]["id"] for _ in range(40)}
    # All three ladder personalities should surface across 40 unseeded matches.
    assert {"defensive", "aggressive", "opportunist"}.issubset(profiles), profiles


def test_seeded_matches_stay_deterministic():
    a = start_match(seed="stable-seed")
    b = start_match(seed="stable-seed")
    assert a["match_id"] == b["match_id"]
    assert a["bot_profile"]["id"] == b["bot_profile"]["id"]


def test_two_guests_do_not_share_a_store_slot():
    store = RebirthMatchStore()
    a = store.save(start_match())
    b = store.save(start_match())
    assert a["match_id"] != b["match_id"]
    # Both must remain independently retrievable — no overwrite.
    assert store.get(a["match_id"])["match_id"] == a["match_id"]
    assert store.get(b["match_id"])["match_id"] == b["match_id"]
    assert len(store) == 2
