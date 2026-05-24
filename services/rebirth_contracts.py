PHASE_CHOOSE = "choose"
PHASE_RESULT = "result"
PHASE_FINISHED = "finished"
FIELD_SLOT_COUNT = 3

VALID_PHASES = {PHASE_CHOOSE, PHASE_RESULT, PHASE_FINISHED}

ERROR_HTTP_STATUS = {
    "malformed_request": 400,
    "authoritative_state_violation": 400,
    "missing_card": 400,
    "invalid_card": 400,
    "duplicate_not_available": 400,
    "missing_match": 404,
    "invalid_phase": 409,
    "match_finished": 409,
    "first_turn_direct_attack_blocked": 409,
}


class RebirthError(ValueError):
    def __init__(self, message, code="malformed_request", status=None):
        super().__init__(message)
        self.code = code
        self.status = status or ERROR_HTTP_STATUS.get(code, 400)


def error_status(code):
    return ERROR_HTTP_STATUS.get(code, 400)


def validate_phase(phase):
    if phase not in VALID_PHASES:
        raise RebirthError(f"Fase Rebirth inválida: {phase}", "invalid_phase")
    return phase
