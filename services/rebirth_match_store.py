from services.rebirth_contracts import RebirthError


class RebirthMatchStore:
    def __init__(self):
        self._matches = {}

    def save(self, match):
        self._matches[match["match_id"]] = match
        return match

    def get(self, match_id):
        key = str(match_id or "")
        match = self._matches.get(key)
        if not match:
            raise RebirthError("Match not found.", "missing_match")
        return match

    def clear(self):
        self._matches.clear()

    def raw(self):
        return self._matches


MATCH_STORE = RebirthMatchStore()
