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
    "not_enough_energy": 409,
    "duplicate_not_available": 400,
    "missing_match": 404,
    "invalid_phase": 409,
    "match_finished": 409,
    "first_turn_direct_attack_blocked": 409,
    "fusion_catalog_mismatch": 400,
    "fusion_material_defeated": 400,
    "fusion_not_adjacent": 400,
    "fusion_target_missing": 400,
    "invalid_fusion_material": 400,
    "invalid_labs_player": 400,
    "labs_disabled": 404,
    "missing_fusion_material": 400,
    "invalid_campaign_payload": 400,
    "campaign_node_not_found": 404,
    "campaign_node_locked": 409,
    "replay_engine_mismatch": 409,
    "replay_card_set_mismatch": 409,
    "replay_ruleset_mismatch": 409,
    "replay_reducer_mismatch": 409,
    "replay_schema_mismatch": 409,
    "replay_command_unsupported": 409,
    "effect_chain_depth_exceeded": 409,
    "causal_chain_depth_exceeded": 409,
    "causal_cycle_detected": 409,
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
