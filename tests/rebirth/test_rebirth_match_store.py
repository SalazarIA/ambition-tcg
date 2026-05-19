import pytest

from services.rebirth_contracts import RebirthError
from services.rebirth_match_store import RebirthMatchStore


class FakeClock:
    def __init__(self):
        self.value = 1000

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def match(match_id):
    return {"match_id": match_id, "phase": "choose"}


def test_match_store_saves_and_loads_match():
    clock = FakeClock()
    store = RebirthMatchStore(ttl_seconds=30, max_matches=5, clock=clock)
    saved = match("rebirth-a")

    assert store.save(saved) is saved
    assert store.get("rebirth-a") is saved
    assert len(store) == 1


def test_match_store_expires_old_matches():
    clock = FakeClock()
    store = RebirthMatchStore(ttl_seconds=10, max_matches=5, clock=clock)
    store.save(match("rebirth-expiring"))

    clock.advance(11)

    with pytest.raises(RebirthError) as error:
        store.get("rebirth-expiring")
    assert error.value.code == "missing_match"
    assert len(store) == 0


def test_match_store_cleanup_is_defensive():
    clock = FakeClock()
    store = RebirthMatchStore(ttl_seconds=10, max_matches=5, clock=clock)
    store.save(match("rebirth-a"))
    store.save(match("rebirth-b"))
    clock.advance(11)

    assert store.cleanup() == 2
    assert store.cleanup() == 0
    assert len(store) == 0


def test_match_store_max_limit_evicts_oldest_match():
    clock = FakeClock()
    store = RebirthMatchStore(ttl_seconds=60, max_matches=2, clock=clock)
    store.save(match("rebirth-a"))
    store.save(match("rebirth-b"))
    assert store.get("rebirth-a")["match_id"] == "rebirth-a"
    store.save(match("rebirth-c"))

    with pytest.raises(RebirthError):
        store.get("rebirth-b")
    assert store.get("rebirth-a")["match_id"] == "rebirth-a"
    assert store.get("rebirth-c")["match_id"] == "rebirth-c"
    assert len(store) == 2
