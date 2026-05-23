import os
from collections import OrderedDict
from threading import RLock
from time import monotonic

from services.rebirth_contracts import RebirthError


DEFAULT_MATCH_TTL_SECONDS = 60 * 60
DEFAULT_MAX_MATCHES = 512


def _positive_int_env(name, default):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return max(1, value)


class RebirthMatchStore:
    def __init__(self, ttl_seconds=DEFAULT_MATCH_TTL_SECONDS, max_matches=DEFAULT_MAX_MATCHES, clock=None):
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.max_matches = max(1, int(max_matches))
        self._clock = clock or monotonic
        self._matches = OrderedDict()
        self._lock = RLock()

    def save(self, match):
        now = self._clock()
        key = str(match["match_id"])
        with self._lock:
            self.cleanup(now=now)
            self._matches[key] = {
                "match": match,
                "expires_at": now + self.ttl_seconds,
            }
            self._matches.move_to_end(key)
            self._trim_locked()
        return match

    def get(self, match_id):
        key = str(match_id or "")
        now = self._clock()
        with self._lock:
            record = self._matches.get(key)
            if not record:
                raise RebirthError("Partida não encontrada.", "missing_match")
            if record["expires_at"] <= now:
                self._matches.pop(key, None)
                raise RebirthError("Partida não encontrada.", "missing_match")
            record["expires_at"] = now + self.ttl_seconds
            self._matches.move_to_end(key)
            return record["match"]

    def cleanup(self, now=None):
        current = self._clock() if now is None else now
        with self._lock:
            expired = [
                key
                for key, record in self._matches.items()
                if record["expires_at"] <= current
            ]
            for key in expired:
                self._matches.pop(key, None)
            return len(expired)

    def _trim_locked(self):
        while len(self._matches) > self.max_matches:
            self._matches.popitem(last=False)

    def clear(self):
        with self._lock:
            self._matches.clear()

    def raw(self):
        with self._lock:
            self.cleanup()
            return {
                key: record["match"]
                for key, record in self._matches.items()
            }

    def __len__(self):
        with self._lock:
            self.cleanup()
            return len(self._matches)


MATCH_STORE = RebirthMatchStore(
    ttl_seconds=_positive_int_env("REBIRTH_MATCH_TTL_SECONDS", DEFAULT_MATCH_TTL_SECONDS),
    max_matches=_positive_int_env("REBIRTH_MAX_MATCHES", DEFAULT_MAX_MATCHES),
)
