import os
from datetime import datetime, timezone

from services.rebirth_gate_evidence import validate_external_gate_evidence
from services.rebirth_public_beta_gate import public_beta_gate_report


def truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def external_gate_payload(
    config=None,
    workflow=None,
    evidence=None,
    *,
    require_external_evidence=False,
):
    config = config or {}
    evidence_report = validate_external_gate_evidence(evidence)
    billing_enabled = truthy(config.get("REBIRTH_ENABLE_BILLING"))
    live_allowed = truthy(config.get("REBIRTH_ALLOW_STRIPE_LIVE"))
    stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "")
    stripe_live_key_present = stripe_secret.startswith("sk_live_")
    legal_flag = truthy(
        config.get("REBIRTH_LEGAL_REVIEWED") or os.environ.get("REBIRTH_LEGAL_REVIEWED")
    )
    backup_flag = truthy(
        config.get("REBIRTH_BACKUP_RESTORE_DRILL") or os.environ.get("REBIRTH_BACKUP_RESTORE_DRILL")
    )
    sentry_configured = bool(config.get("SENTRY_DSN") or os.environ.get("SENTRY_DSN"))
    if require_external_evidence:
        legal_proven = evidence_report["legal_review"]["valid"]
        backup_proven = evidence_report["backup_restore"]["valid"]
        error_tracking_proven = evidence_report["error_tracking"]["valid"]
    else:
        legal_proven = legal_flag or evidence_report["legal_review"]["valid"]
        backup_proven = backup_flag or evidence_report["backup_restore"]["valid"]
        error_tracking_proven = sentry_configured or evidence_report["error_tracking"]["valid"]
    workflow_expected = bool(workflow and (workflow.get("expectedHeadSha") or workflow.get("branch")))
    workflow_matches = not workflow_expected or (
        (not workflow.get("expectedHeadSha") or workflow.get("matchedExpectedHead"))
        and (not workflow.get("branch") or workflow.get("matchedExpectedBranch"))
    )
    workflow_green = bool(workflow and workflow.get("conclusion") == "success" and workflow_matches)
    if not workflow_expected and not require_external_evidence:
        workflow_green = workflow_green or truthy(
            config.get("REBIRTH_GITHUB_QA_GREEN") or os.environ.get("REBIRTH_GITHUB_QA_GREEN")
        )

    checks = [
        {
            "key": "legal_review",
            "name": "Revisão legal",
            "state": "passed" if legal_proven else "blocked",
            "copy": "Termos, Privacidade, deleção/exportação e monetização precisam de aceite externo ou evidência auditável.",
        },
        {
            "key": "backup_restore",
            "name": "Backup/restore Postgres",
            "state": "passed" if backup_proven else "blocked",
            "copy": "Drill real no Render/Postgres deve ser datado antes de convidar testers externos e ter evidência auditável.",
        },
        {
            "key": "error_tracking",
            "name": "Error tracking",
            "state": "passed" if error_tracking_proven else "blocked",
            "copy": (
                "Confirme um evento real em Sentry, GlitchTip ou provedor compatível."
                if require_external_evidence
                else "Configure SENTRY_DSN para Sentry, GlitchTip ou provedor compatível."
            ),
        },
        {
            "key": "github_workflow",
            "name": "GitHub QA",
            "state": "passed" if workflow_green else "pending",
            "copy": "O workflow rebirth-closed-beta-qa precisa estar verde no GitHub, não só local.",
        },
        {
            "key": "billing_off",
            "name": "Stripe live desligado",
            "state": "passed" if not billing_enabled and not (stripe_live_key_present and live_allowed) else "blocked",
            "copy": "Pagamentos reais ficam bloqueados por padrão durante o beta fechado.",
        },
    ]
    return {
        "ready": all(check["state"] == "passed" for check in checks),
        "billing_enabled": billing_enabled,
        "stripe_live_key_present": stripe_live_key_present,
        "require_external_evidence": require_external_evidence,
        "evidence": evidence_report,
        "checks": checks,
    }


def _check_by_key(report, key):
    for check in report.get("checks") or []:
        if check.get("key") == key:
            return check
    return {"key": key, "state": "pending", "value": "sem amostra"}


def _card_from_check(report, key, label):
    check = _check_by_key(report, key)
    return {
        "label": label,
        "value": check.get("value") or "sem amostra",
        "state": check.get("state") or "pending",
        "target": check.get("target"),
    }


def beta_dashboard_payload(repo, *, limit=5000, since=None):
    events = repo.query_telemetry_events(limit=limit, since=since)
    public_gate = public_beta_gate_report(events)

    starts = [event for event in events if event["event_type"] == "match_started"]
    finishes = [event for event in events if event["event_type"] == "match_finished"]
    first_starts = [event for event in starts if (event.get("payload") or {}).get("first_duel")]
    first_finishes = [event for event in finishes if (event.get("payload") or {}).get("first_duel")]
    tutorial_done = [
        event
        for event in events
        if event["event_type"] == "tutorial_step_completed"
        and int((event.get("payload") or {}).get("step", 0) or 0) >= 4
    ]
    errors = [event for event in events if event["event_type"] in {"client_error", "server_error"}]
    feedback = [event for event in events if event["event_type"] == "feedback_submitted"]

    first_completion_rate = round(len(first_finishes) / max(1, len(first_starts)), 3) if first_starts else None
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "since": since,
        "sample_size": len(events),
        "cards": [
            _card_from_check(public_gate, "d1_retention", "D1 retenção"),
            _card_from_check(public_gate, "d7_retention", "D7 retenção"),
            _card_from_check(public_gate, "first_match_completion", "1a partida"),
            _card_from_check(public_gate, "tutorial_completion", "Tutorial"),
            _card_from_check(public_gate, "crash_rate", "Crash/Error"),
            {"label": "Feedbacks", "value": len(feedback)},
        ],
        "public_beta_gate": public_gate,
        "first_match": {
            "started": len(first_starts),
            "finished": len(first_finishes),
            "completion_rate": first_completion_rate,
        },
        "tutorial_completed": len(tutorial_done),
        "errors": len(errors),
        "feedback": len(feedback),
    }
