import hashlib
import hmac
import time


class SlidingWindowRateLimiter:
    def __init__(self):
        self._hits = {}

    def allow(self, key, limit, window_seconds, now=None):
        current_time = time.monotonic() if now is None else now
        window_seconds = max(1, int(window_seconds or 1))
        limit = max(1, int(limit or 1))
        cutoff = current_time - window_seconds
        hits = [hit for hit in self._hits.get(key, []) if hit >= cutoff]

        if len(hits) >= limit:
            self._hits[key] = hits
            return False

        hits.append(current_time)
        self._hits[key] = hits
        return True

    def clear(self):
        self._hits.clear()


def request_rate_limit_key(request, session, secret, scope, identity=""):
    ip_address = (request.remote_addr or request.headers.get("X-Forwarded-For", "unknown").split(",")[0]).strip()
    user_agent_hash = hashlib.sha256(str(request.headers.get("User-Agent", "")).encode("utf-8")).hexdigest()[:16]
    session_hint = session.get("user_id") or session.get("_csrf_token") or "anonymous"
    raw = f"{scope}:{ip_address}:{session_hint}:{identity}:{user_agent_hash}"
    return hmac.new(str(secret or "").encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
