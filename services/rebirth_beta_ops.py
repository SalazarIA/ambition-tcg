import os
from datetime import datetime, timedelta, timezone


def truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def external_gate_payload(config=None, workflow=None):
    config = config or {}
    billing_enabled = truthy(config.get("REBIRTH_ENABLE_BILLING"))
    live_allowed = truthy(config.get("REBIRTH_ALLOW_STRIPE_LIVE"))
    stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "")
    stripe_live_key_present = stripe_secret.startswith("sk_live_")
    sentry_configured = bool(config.get("SENTRY_DSN") or os.environ.get("SENTRY_DSN"))
    workflow_green = (workflow and workflow.get("conclusion") == "success") or truthy(
        config.get("REBIRTH_GITHUB_QA_GREEN") or os.environ.get("REBIRTH_GITHUB_QA_GREEN")
    )

    checks = [
        {
            "key": "legal_review",
            "name": "Revisão legal",
            "state": "passed" if truthy(config.get("REBIRTH_LEGAL_REVIEWED") or os.environ.get("REBIRTH_LEGAL_REVIEWED")) else "blocked",
            "copy": "Termos, Privacidade, deleção/exportação e monetização precisam de aceite externo.",
        },
        {
            "key": "backup_restore",
            "name": "Backup/restore Postgres",
            "state": "passed" if truthy(config.get("REBIRTH_BACKUP_RESTORE_DRILL") or os.environ.get("REBIRTH_BACKUP_RESTORE_DRILL")) else "blocked",
            "copy": "Drill real no Render/Postgres deve ser datado antes de convidar testers externos.",
        },
        {
            "key": "error_tracking",
            "name": "Error tracking",
            "state": "passed" if sentry_configured else "blocked",
            "copy": "Configure SENTRY_DSN para Sentry, GlitchTip ou provedor compatível.",
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
        "checks": checks,
    }


def _iso_days_ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


def beta_dashboard_payload(repo, *, limit=5000):
    events = repo.query_telemetry_events(limit=limit)
    d1_since = _iso_days_ago(1)
    d7_since = _iso_days_ago(7)

    def created_after(event, since):
        return str(event.get("created_at") or "") >= since

    def users_for(predicate):
        users = {
            int(event["user_id"])
            for event in events
            if event.get("user_id") is not None and predicate(event)
        }
        return len(users)

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
        "sample_size": len(events),
        "cards": [
            {"label": "D1 ativos", "value": users_for(lambda event: created_after(event, d1_since))},
            {"label": "D7 ativos", "value": users_for(lambda event: created_after(event, d7_since))},
            {
                "label": "1a partida",
                "value": f"{round(first_completion_rate * 100)}%" if first_completion_rate is not None else "sem amostra",
            },
            {"label": "Tutoriais", "value": len(tutorial_done)},
            {"label": "Erros", "value": len(errors)},
            {"label": "Feedbacks", "value": len(feedback)},
        ],
        "first_match": {
            "started": len(first_starts),
            "finished": len(first_finishes),
            "completion_rate": first_completion_rate,
        },
        "tutorial_completed": len(tutorial_done),
        "errors": len(errors),
        "feedback": len(feedback),
    }
