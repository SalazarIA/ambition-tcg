import os
import hashlib
import json
import secrets
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from time import perf_counter
from flask import g, Flask, jsonify, make_response, redirect, render_template, request, send_from_directory, session

from services.rebirth_contracts import RebirthError
from services.rebirth_async_competition import async_competition_payload, async_history_payload
from services.rebirth_actions import canonical_action, legal_actions
from services.rebirth_balance import simulate_balance
from services.rebirth_bot import attack_utility_projection, tactical_utility_matrix
from services.rebirth_cards import dominant_family
from services.rebirth_campaign import CAMPAIGN_VERSION, campaign_payload, get_node, is_unlocked
from services.rebirth_content_pipeline import content_pipeline_report
from services.rebirth_dispatcher import (
    DeclareAttackCommand,
    EndTurnCommand,
    EvolveDuplicateCommand,
    FuseFieldPairCommand,
    MulliganCommand,
    SummonCardCommand,
    dispatch_command,
)
from services.rebirth_first_session import first_session_plan
from services.rebirth_live_balance import live_balance_payload
from services.rebirth_engine import start_match
from services.rebirth_match_store import MATCH_STORE
from services.rebirth_rate_limit import create_rate_limiter
from services.rebirth_persistence import (
    RebirthPersistenceError,
    RebirthRepository,
)
from services.rebirth_beta_ops import beta_dashboard_payload, external_gate_payload
from services.rebirth_deck_coach import deck_suggestions
from services.rebirth_postmatch import post_match_recap
from services.rebirth_phase_reports import audit_phase_reports
from services.rebirth_public_beta_gate import public_beta_gate_payload
from services.rebirth_release_readiness import release_readiness_report
from services.rebirth_product import (
    account_payload,
    auth_plan_payload,
    balance_payload,
    collection_payload,
    DEFAULT_LOADOUT,
    desktop_payload,
    history_payload,
    lab_payload,
    onboarding_payload,
    open_booster,
    profile_payload,
    product_shell_payload,
    progression_payload,
    release_payload,
    shop_payload,
    support_payload,
    validate_loadout,
)
from services.rebirth_serializers import public_state
from services.rebirth_reducers import reduce_event
from services.rebirth_telemetry import (
    REBIRTH_CLIENT_TELEMETRY_EVENTS,
    build_decision_telemetry_payload,
    build_match_telemetry_payload,
    client_telemetry_payload as build_client_telemetry_payload,
)
from services.email_service import send_email


app = Flask(__name__)
# Perf v103: gzip/brotli nas respostas dinâmicas (estado de partida ~30KB de
# JSON vira ~4KB no fio) e cache longo para estáticos — todos servidos com
# query de versão (?v=REBIRTH_RELEASE_VERSION), ou seja, imutáveis por URL.
try:
    from flask_compress import Compress

    app.config["COMPRESS_MIMETYPES"] = [
        "application/json",
        "text/html",
        "text/css",
        "application/javascript",
        "text/javascript",
        "image/svg+xml",
        "application/manifest+json",
    ]
    app.config["COMPRESS_MIN_SIZE"] = 1024
    Compress(app)
except ImportError:  # ambiente sem a dependência segue funcional, sem gzip
    pass
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 30
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ambitionz-rebirth-dev")
app.config["REBIRTH_DB_PATH"] = os.environ.get(
    "REBIRTH_DB_PATH",
    os.path.join(app.instance_path, "rebirth.db"),
)
app.config["REBIRTH_DATABASE_URL"] = os.environ.get("REBIRTH_DATABASE_URL") or os.environ.get("DATABASE_URL")
app.config["REBIRTH_ALLOW_SQLITE_TESTING"] = os.environ.get("REBIRTH_ALLOW_SQLITE_TESTING", "false") == "true"
app.config["REBIRTH_REQUIRE_CSRF"] = os.environ.get("REBIRTH_REQUIRE_CSRF", "true") == "true"
app.config["REBIRTH_AUTH_RATE_LIMIT"] = int(os.environ.get("REBIRTH_AUTH_RATE_LIMIT", "20"))
app.config["REBIRTH_AUTH_RATE_LIMIT_SECONDS"] = int(os.environ.get("REBIRTH_AUTH_RATE_LIMIT_SECONDS", "300"))
app.config["REBIRTH_ENABLE_INTERNAL_LAB"] = os.environ.get("REBIRTH_ENABLE_INTERNAL_LAB", "false") == "true"
# Telemetria de decisão é observacional e roda no caminho quente de cada jogada
# do jogador: pode ser desligada por ambiente sem afetar a jogabilidade.
app.config["REBIRTH_ENABLE_DECISION_TELEMETRY"] = os.environ.get("REBIRTH_ENABLE_DECISION_TELEMETRY", "true") == "true"
REBIRTH_RELEASE_VERSION = os.environ.get("REBIRTH_RELEASE_VERSION", "v123_CRAFTING")
app.config["REBIRTH_RELEASE_VERSION"] = REBIRTH_RELEASE_VERSION
app.config["REBIRTH_BALANCE_INTERACTIVE_MATCH_LIMIT"] = max(1, min(40, int(os.environ.get("REBIRTH_BALANCE_INTERACTIVE_MATCH_LIMIT", "24"))))
app.config["REBIRTH_POSTGRES_SERIALIZATION_ATTEMPTS"] = min(3, max(1, int(os.environ.get("REBIRTH_POSTGRES_SERIALIZATION_ATTEMPTS", "3"))))
app.config["REBIRTH_POSTGRES_RETRY_BACKOFF_SECONDS"] = max(0.0, float(os.environ.get("REBIRTH_POSTGRES_RETRY_BACKOFF_SECONDS", "0.02")))
app.config["REBIRTH_ENABLE_BILLING"] = os.environ.get("REBIRTH_ENABLE_BILLING", "false").strip().lower() == "true"
app.config["REBIRTH_ALLOW_STRIPE_LIVE"] = os.environ.get("REBIRTH_ALLOW_STRIPE_LIVE", "false").strip().lower() == "true"
app.config["REBIRTH_LEGAL_REVIEWED"] = os.environ.get("REBIRTH_LEGAL_REVIEWED", "false").strip().lower() == "true"
app.config["REBIRTH_BACKUP_RESTORE_DRILL"] = os.environ.get("REBIRTH_BACKUP_RESTORE_DRILL", "false").strip().lower() == "true"
app.config["REBIRTH_GITHUB_QA_GREEN"] = os.environ.get("REBIRTH_GITHUB_QA_GREEN", "false").strip().lower() == "true"
app.config["SENTRY_DSN"] = os.environ.get("SENTRY_DSN")
app.config["SENTRY_ENVIRONMENT"] = os.environ.get("SENTRY_ENVIRONMENT") or os.environ.get("RENDER_SERVICE_NAME") or "development"
app.config["SENTRY_TRACES_SAMPLE_RATE"] = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0") or 0)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE") == "true"

# Email verification. SMTP_* + MAIL_FROM são credenciais (env, não commitadas).
# Sem elas, email_service.send_email cai no fallback que loga o link — então
# o fluxo funciona em dev e em prod assim que o provedor for configurado.
app.config["PUBLIC_BASE_URL"] = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
app.config["SMTP_HOST"] = os.environ.get("SMTP_HOST")
app.config["SMTP_PORT"] = os.environ.get("SMTP_PORT", "587")
app.config["SMTP_USERNAME"] = os.environ.get("SMTP_USERNAME")
app.config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD")
app.config["SMTP_USE_TLS"] = os.environ.get("SMTP_USE_TLS", "true") == "true"
app.config["MAIL_FROM"] = os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USERNAME")
app.config["REBIRTH_REQUIRE_EMAIL_VERIFICATION"] = os.environ.get("REBIRTH_REQUIRE_EMAIL_VERIFICATION", "false") == "true"

REBIRTH_LABS_ENABLED = True
app.config["REBIRTH_LABS_ENABLED"] = os.environ.get("REBIRTH_LABS_ENABLED", str(REBIRTH_LABS_ENABLED)).lower() == "true"
REBIRTH_MATCHES = MATCH_STORE
# Rate limiter with a pluggable backend (memory by default; Redis once the app
# scales beyond -w 1, so the window is shared across workers). Auth and game
# routes use separate namespaces but the same shared backend.
AUTH_RATE_LIMITER = create_rate_limiter("rbauth")
GAME_RATE_LIMITER = create_rate_limiter("rbgame")
# Per-endpoint game limits (requests / window / IP). Generous for a human (a
# match is hundreds of actions over minutes) but caps abuse — e.g. mining match
# seeds via /start or flooding telemetry. 0 disables a bucket; tune via env.
GAME_RATE_LIMIT_WINDOW = max(1, int(os.environ.get("REBIRTH_GAME_RATE_LIMIT_SECONDS", "60")))
GAME_RATE_LIMITS = {
    "api_rebirth_start": int(os.environ.get("REBIRTH_START_RATE_LIMIT", "120")),
    "api_rebirth_campaign_start": int(os.environ.get("REBIRTH_START_RATE_LIMIT", "120")),
    "api_rebirth_booster_open": int(os.environ.get("REBIRTH_BOOSTER_RATE_LIMIT", "60")),
    "api_rebirth_play_card": 600,
    "api_rebirth_attack": 600,
    "api_rebirth_next_turn": 600,
    "api_rebirth_evolve": 600,
    "api_rebirth_mulligan": 300,
    "api_labs_fusion": 300,
    "api_rebirth_resume": 300,
    "api_rebirth_telemetry": int(os.environ.get("REBIRTH_TELEMETRY_RATE_LIMIT", "300")),
    "api_rebirth_telemetry_beacon": int(os.environ.get("REBIRTH_TELEMETRY_RATE_LIMIT", "300")),
}
MATCH_TELEMETRY_CLOCKS = {}
MATCH_TERMINAL_TELEMETRY = set()
MATCH_ABANDON_TELEMETRY = set()
MATCH_TELEMETRY_LOCK = threading.Lock()
_SCHEMA_BOOTSTRAP_LOCK = threading.Lock()
_SCHEMA_BOOTSTRAP_DONE = False


def _init_error_tracking():
    dsn = app.config.get("SENTRY_DSN")
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except Exception:
        app.logger.warning("rebirth.error_tracking skipped: sentry-sdk is not installed")
        return
    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=app.config.get("SENTRY_ENVIRONMENT"),
        release=app.config.get("REBIRTH_RELEASE_VERSION"),
        traces_sample_rate=max(0.0, min(1.0, float(app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0) or 0))),
    )
    app.logger.info("rebirth.error_tracking enabled")


_init_error_tracking()


def _bootstrap_rebirth_schema():
    """Roda upgrade_schema no boot do app se REBIRTH_DATABASE_URL aponta para
    Postgres e o schema está atrasado.

    Render starter plan ignora preDeployCommand — sem isso, novas tabelas e
    correções de schema legacy nunca chegam em produção. Idempotente: detecta
    versão antes de tentar upgrade, lock evita race entre threads gunicorn.
    """
    global _SCHEMA_BOOTSTRAP_DONE
    if _SCHEMA_BOOTSTRAP_DONE:
        return
    database_url = app.config.get("REBIRTH_DATABASE_URL")
    if not database_url:
        _SCHEMA_BOOTSTRAP_DONE = True
        return
    with _SCHEMA_BOOTSTRAP_LOCK:
        if _SCHEMA_BOOTSTRAP_DONE:
            return
        try:
            from services.rebirth_schema import (
                SCHEMA_VERSION,
                make_engine,
                normalize_database_url,
                upgrade_schema,
                validate_schema,
            )

            normalized = normalize_database_url(database_url)
            if not normalized.startswith("postgresql+psycopg://"):
                app.logger.info("rebirth.schema bootstrap skipped (non-postgres backend)")
                _SCHEMA_BOOTSTRAP_DONE = True
                return
            # Observabilidade de incidente: loga host/porta/db ALVO (sem
            # usuário/senha) antes de conectar, para distinguir "banco fora"
            # de "host stale na env var" direto no log do Render.
            from urllib.parse import urlsplit

            _target = urlsplit(normalized)
            app.logger.info(
                "rebirth.schema bootstrap alvo: host=%s port=%s db=%s",
                _target.hostname,
                _target.port,
                (_target.path or "").lstrip("/"),
            )
            engine = make_engine(normalized)
            try:
                status = validate_schema(engine)
            finally:
                engine.dispose()
            current_version = int(status.get("version", 0) or 0)
            if current_version >= SCHEMA_VERSION and not status.get("missing_tables") and not status.get("missing_columns"):
                app.logger.info("rebirth.schema already at v%s", current_version)
                _SCHEMA_BOOTSTRAP_DONE = True
                return
            app.logger.info(
                "rebirth.schema bootstrap upgrading: v%s -> v%s (missing=%s, columns=%s)",
                current_version,
                SCHEMA_VERSION,
                status.get("missing_tables"),
                status.get("missing_columns"),
            )
            upgrade_schema(normalized)
            app.logger.info("rebirth.schema bootstrap completed to v%s", SCHEMA_VERSION)
        except Exception:
            app.logger.exception("rebirth.schema bootstrap failed")
        finally:
            _SCHEMA_BOOTSTRAP_DONE = True


_bootstrap_rebirth_schema()

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        # F22-B: Google Fonts CSS (style) + woff2 binaries (font) liberados para
        # carregar Cinzel + Crimson Pro do CDN público. Sem dependência paga.
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "img-src 'self' data:",
        "font-src 'self' data: https://fonts.gstatic.com",
        "connect-src 'self'",
        "manifest-src 'self'",
        "worker-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


def json_error(message, code="malformed_request", status=400):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


def json_success(state, result=None, **extra):
    payload = {"ok": True, "state": state, "result": result}
    payload.update(extra)
    return jsonify(payload)


def json_payload(**extra):
    payload = {"ok": True}
    payload.update(extra)
    return jsonify(payload)


def json_from_rebirth_error(error):
    return json_error(str(error), error.code, status=getattr(error, "status", 400))


def json_from_persistence_error(error):
    return json_error(str(error), error.code, status=getattr(error, "status", 400))


def match_reward_payload(before, after, state):
    finished = bool((state or {}).get("is_finished"))
    if not after:
        if not finished:
            return None
        return {
            "persisted": False,
            "xp": 0,
            "level": 1,
            "xp_total": 0,
            "next_level_xp": 500,
            "xp_to_next": 500,
            "level_up": False,
            "achievements": [],
            "daily": {"name": "Jogue um clash", "progress": 0, "goal": 1, "state": "locked", "ready": False},
            "next_goal": "Abra Login / Cadastro no topo para guardar recompensas futuras.",
            "message": "Partida concluída como visitante.",
            "recap": post_match_recap(state),
        }

    before = before or {}
    before_level = int(before.get("level", 1) or 1)
    before_xp = int(before.get("xp", 0) or 0)
    before_clashes = int(before.get("clashes", 0) or 0)
    before_wins = int(before.get("wins", 0) or 0)
    xp_delta = max(0, int(after.get("xp", 0) or 0) - before_xp)
    achievements = []
    if before_clashes == 0 and int(after.get("clashes", 0) or 0) >= 1:
        achievements.append({"key": "first_clash", "name": "Primeiro Clash"})
    if before_wins == 0 and int(after.get("wins", 0) or 0) >= 1:
        achievements.append({"key": "first_win", "name": "Primeira Vitória"})

    level = int(after.get("level", 1) or 1)
    daily_progress = min(1, int(after.get("clashes", 0) or 0))
    daily_state = "claimed" if after.get("daily_claimed") else "ready" if daily_progress >= 1 else "locked"
    xp_total = int(after.get("xp", 0) or 0)
    next_xp = int(after.get("next_level_xp", level * 500) or level * 500)
    xp_to_next = max(0, next_xp - xp_total)
    outcome = ((state or {}).get("result") or {}).get("outcome") or ((state or {}).get("winner") or "Clash")
    terminal_labels = {"Victory": "Vitória", "Defeat": "Derrota", "Clash": "Clash"}
    clash_labels = {"Victory": "Confronto vencido", "Defeat": "Unidade perdida", "Clash": "Troca resolvida"}
    outcome_label = (terminal_labels if finished else clash_labels).get(outcome, outcome)
    return {
        "persisted": True,
        "xp": xp_delta,
        "level": level,
        "xp_total": xp_total,
        "next_level_xp": next_xp,
        "xp_to_next": xp_to_next,
        "level_up": level > before_level,
        "achievements": achievements,
        "daily": {
            "name": "Jogue um clash",
            "progress": daily_progress,
            "goal": 1,
            "state": daily_state,
            "ready": daily_state == "ready",
        },
        "next_goal": "Resgate sua recompensa diária." if daily_state == "ready" else "Abra Cartas para ajustar seu baralho." if level >= 3 else "Jogue o próximo clash guiado.",
        "message": f"{outcome_label}: +{xp_delta} XP salvos na sua conta Rebirth.",
        "recap": post_match_recap(state),
    }


def clash_reward_payload_from_progress(before, progress, state):
    if progress and progress.get("last_reward_applied") is False:
        return match_reward_payload(progress, progress, state)
    return match_reward_payload(before, progress, state)


def csrf_token():
    token = session.get("rebirth_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["rebirth_csrf_token"] = token
    return token


def establish_rebirth_session(user):
    session.clear()
    session["rebirth_user_id"] = user["id"]
    session_token = secrets.token_urlsafe(48)
    rebirth_repo().create_session(
        user["id"],
        session_token,
        expires_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds"),
    )
    session["rebirth_session_token"] = session_token
    session["rebirth_csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True
    return session["rebirth_csrf_token"]


def clear_rebirth_session():
    token = session.get("rebirth_session_token")
    if token:
        rebirth_repo().revoke_session(token)
    session.clear()
    return csrf_token()


def csrf_payload():
    return {"csrf": csrf_token()}


_REPO_CACHE = {}
_REPO_CACHE_LIMIT = 32


def rebirth_repo():
    """Repositório Rebirth com cache por destino.

    Antes, CADA chamada construía um RebirthRepository novo — e, em Postgres,
    um engine SQLAlchemy novo com pool próprio (conexão TCP/TLS por chamada,
    várias vezes por request). O cache reusa o engine/pool pelo processo.
    """
    database_url = app.config.get("REBIRTH_DATABASE_URL")
    retry_options = {
        "serialization_retry_attempts": app.config["REBIRTH_POSTGRES_SERIALIZATION_ATTEMPTS"],
        "serialization_retry_backoff_seconds": app.config["REBIRTH_POSTGRES_RETRY_BACKOFF_SECONDS"],
    }
    if database_url:
        cache_key = ("postgres", database_url, tuple(sorted(retry_options.items())))
    elif app.config.get("TESTING") or app.config.get("REBIRTH_ALLOW_SQLITE_TESTING"):
        cache_key = ("sqlite", app.config["REBIRTH_DB_PATH"], tuple(sorted(retry_options.items())))
    else:
        raise RebirthPersistenceError(
            "REBIRTH_DATABASE_URL e obrigatoria fora do ambiente de testes.",
            "database_not_configured",
            status=503,
        )
    repo = _REPO_CACHE.get(cache_key)
    if repo is None:
        if database_url:
            repo = RebirthRepository(database_url=database_url, **retry_options)
        else:
            repo = RebirthRepository(app.config["REBIRTH_DB_PATH"], **retry_options)
        if len(_REPO_CACHE) >= _REPO_CACHE_LIMIT:
            _REPO_CACHE.pop(next(iter(_REPO_CACHE)), None)
        _REPO_CACHE[cache_key] = repo
    return repo


def int_arg(name, default, maximum):
    """Query param inteiro com clamp — `?limit=abc` derrubava o endpoint com 500."""
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = int(default)
    return max(1, min(int(maximum), value))


def guest_wallet_payload():
    return {"GOLD": 0, "COINZ": 0, "ledger_source": "wallet_ledger", "guest": True}


def remember_active_match(match, user=None):
    if not match or not match.get("match_id"):
        return None
    session["rebirth_active_match_id"] = match["match_id"]
    session["rebirth_active_match_owner"] = int(user["id"]) if user else None
    return match["match_id"]


def reconnect_payload(match=None, user=None):
    match_id = (match or {}).get("match_id") or session.get("rebirth_active_match_id")
    return {
        "active_match_id": match_id,
        "durable": bool(user),
        "scope": "account_postgres" if user else "guest_session_memory",
        "in_progress": bool(match and not match.get("is_finished")),
    }


def shop_data_for_user(user):
    repo = rebirth_repo()
    history = []
    market = []
    warnings = []
    if user:
        try:
            history = repo.booster_history(user["id"])
        except RebirthPersistenceError as error:
            warnings.append(
                {"surface": "booster_history", "code": error.code, "message": str(error)}
            )
    try:
        market = repo.market_offers(exclude_user_id=user["id"] if user else None)
    except RebirthPersistenceError as error:
        warnings.append({"surface": "market", "code": error.code, "message": str(error)})
    return history, market, warnings


def current_user(*, required=False):
    token = session.get("rebirth_session_token")
    if not token:
        return None
    try:
        return rebirth_repo().user_for_session(token)
    except RebirthPersistenceError as error:
        if required:
            raise
        # Banco/schema indisponível (ex.: Postgres fora do ar ou host que não
        # resolve): degrada para deslogado em vez de derrubar páginas HTML
        # com 500. Fluxos que exigem conta chamam current_user(required=True)
        # e preservam o erro real de persistência.
        app.logger.warning(
            "current_user indisponível, degradando para deslogado: %s",
            getattr(error, "code", "unknown"),
        )
        return None


def current_account():
    return account_payload(current_user())


def auth_sync_payload(user):
    repo = rebirth_repo()
    collection_counts = repo.collection_counts(user["id"])
    loadout_ids = repo.loadout_card_ids(user["id"])
    return {
        "wallet": repo.wallet_payload(user["id"]),
        "collection": collection_payload(
            account=account_payload(user),
            collection_counts=collection_counts,
            loadout_card_ids=loadout_ids,
        ),
    }


def rebirth_navbar_payload(user=None, progression=None):
    progress = progression
    if user and progress is None:
        progress = rebirth_repo().progression(user["id"]) or {}
    progress = progress or {}
    level = int(progress.get("level", 1) or 1)
    xp = int(progress.get("xp", 0) or 0)
    next_level = int(progress.get("next_level_xp", level * 500) or level * 500)
    xp_percent = 0 if next_level <= 0 else min(100, max(0, round((xp / next_level) * 100)))
    wallet = progress.get("wallet") or {}
    gold = int(wallet.get("GOLD", progress.get("gold", 0)) or 0)
    coinz = int(wallet.get("COINZ", progress.get("coinz", progress.get("premium", 0))) or 0)
    return {
        "authenticated": bool(user),
        "player_name": user["username"] if user else "Visitante",
        "player_label": "Jogador" if user else "Visitante",
        "email_verified": bool(user.get("email_verified")) if user else True,
        "level": level,
        "xp": xp,
        "next_level_xp": next_level,
        "xp_percent": xp_percent,
        "gold": gold,
        "coinz": coinz,
        "wallet": {"GOLD": gold, "COINZ": coinz, "ledger_source": wallet.get("ledger_source", "wallet_ledger")},
    }


def require_user():
    user = current_user(required=True)
    if not user:
        raise RebirthPersistenceError("Entre para usar a coleção persistida do Rebirth.", "auth_required", status=401)
    return user


def enforce_auth_rate_limit(action, identifier="anonymous"):
    limit = int(app.config.get("REBIRTH_AUTH_RATE_LIMIT", 20))
    window_seconds = int(app.config.get("REBIRTH_AUTH_RATE_LIMIT_SECONDS", 300))
    if limit <= 0 or window_seconds <= 0:
        return

    remote_addr = request.remote_addr or "local"
    identity = str(identifier or "anonymous").strip().lower()
    keys = (f"{action}:ip:{remote_addr}", f"{action}:identity:{remote_addr}:{identity}")
    if AUTH_RATE_LIMITER.hit(keys, limit, window_seconds):
        raise RebirthPersistenceError("Muitas tentativas de acesso. Tente novamente mais tarde.", "rate_limited", status=429)


def get_match(match_id, user=None):
    try:
        match = MATCH_STORE.get(match_id)
    except RebirthError as error:
        if error.code != "missing_match" or not user:
            raise
        restored = rebirth_repo().runtime_match_state(user["id"], match_id)
        match = MATCH_STORE.save(restored)
    owner_id = match.get("owner_user_id")
    if user and owner_id and int(owner_id) == int(user["id"]):
        settle_campaign_victory(rebirth_repo(), user, match)
    return match


def ensure_match_access(match, user=None):
    owner_id = match.get("owner_user_id")
    if owner_id and (not user or int(user["id"]) != int(owner_id)):
        raise RebirthError("Esta partida pertence a outra conta Rebirth.", "match_forbidden", status=403)
    return match


def persist_match_if_owned(repo, user, match):
    if user and match:
        match["owner_user_id"] = user["id"]
        return repo.upsert_match_history(user["id"], match)
    return None


def settle_campaign_victory(repo, user, match):
    if not repo or not user or not match:
        return None
    if not match.get("campaign_node") or not match.get("is_finished") or match.get("winner") != "player":
        return None
    if match.get("campaign_version") != CAMPAIGN_VERSION:
        return None
    node = get_node(match.get("campaign_node"))
    if not node:
        return None
    return repo.record_campaign_victory(
        user["id"],
        node["id"],
        node["reward"],
        CAMPAIGN_VERSION,
        match_state=match,
    )


def record_match_telemetry(repo, user, match, event_type, **extra):
    """Best-effort product metrics kept outside deterministic match state."""
    if not match:
        return
    match_id = str(match.get("match_id") or "")
    if not match_id:
        return
    elapsed_ms = None
    total_elapsed_ms = None
    reserved_terminal = False
    reserved_abandon = False
    now = time.monotonic()
    with MATCH_TELEMETRY_LOCK:
        if event_type == "match_abandoned":
            if match_id in MATCH_ABANDON_TELEMETRY:
                return
            MATCH_ABANDON_TELEMETRY.add(match_id)
            reserved_abandon = True
        terminal_recorded = match_id in MATCH_TERMINAL_TELEMETRY
        if terminal_recorded and event_type in {"match_finished", "match_won", "match_lost", "match_drawn"}:
            if reserved_abandon:
                MATCH_ABANDON_TELEMETRY.discard(match_id)
            return
        if match.get("is_finished") and not terminal_recorded:
            MATCH_TERMINAL_TELEMETRY.add(match_id)
            reserved_terminal = True
        timing = MATCH_TELEMETRY_CLOCKS.get(match_id)
        if event_type == "match_started" or not isinstance(timing, dict):
            timing = {"started_at": now, "last_at": now}
            MATCH_TELEMETRY_CLOCKS[match_id] = timing
        else:
            elapsed_ms = round(max(0.0, now - timing["last_at"]) * 1000)
            timing["last_at"] = now
        total_elapsed_ms = round(max(0.0, now - timing["started_at"]) * 1000)
        if match.get("is_finished") or event_type == "match_abandoned":
            MATCH_TELEMETRY_CLOCKS.pop(match_id, None)
    payload = build_match_telemetry_payload(
        match,
        event_type,
        elapsed_ms=elapsed_ms,
        total_elapsed_ms=total_elapsed_ms,
        release_version=app.config["REBIRTH_RELEASE_VERSION"],
        authenticated=bool(user),
        extra=extra,
    )
    try:
        telemetry_repo = repo or rebirth_repo()
        telemetry_repo.record_telemetry_event(event_type, payload, user_id=(user or {}).get("id"))
        if match.get("is_finished") and reserved_terminal:
            if event_type != "match_finished":
                telemetry_repo.record_telemetry_event("match_finished", payload, user_id=(user or {}).get("id"))
            outcome_event = None
            if match.get("winner") == "player":
                outcome_event = "match_won"
            elif match.get("winner") == "bot":
                outcome_event = "match_lost"
            elif match.get("winner"):
                outcome_event = "match_drawn"
            if outcome_event and event_type != outcome_event:
                telemetry_repo.record_telemetry_event(outcome_event, payload, user_id=(user or {}).get("id"))
    except Exception:
        with MATCH_TELEMETRY_LOCK:
            if reserved_terminal:
                MATCH_TERMINAL_TELEMETRY.discard(match_id)
            if reserved_abandon:
                MATCH_ABANDON_TELEMETRY.discard(match_id)
        app.logger.exception("rebirth.telemetry write failed for %s", event_type)


def _decision_action_id(action):
    payload = action.get("payload") or {}
    identity = (
        payload.get("attacker_instance_id")
        or payload.get("card_instance_id")
        or payload.get("card_id")
        or action.get("type")
    )
    target = payload.get("target_instance_id")
    return f"{action.get('type')}:{identity}" + (f"->{target}" if target else "")


def _decision_action_score(match, action):
    if action.get("type") != "attack":
        return None
    payload = action.get("payload") or {}
    player_field = [
        card for card in ((match["player"].get("field") or match["player"].get("battlefield") or [])) if card
    ]
    bot_field = [
        card for card in ((match["bot"].get("field") or match["bot"].get("battlefield") or [])) if card
    ]
    attacker = next(
        (card for card in player_field if card.get("instance_id") == payload.get("attacker_instance_id")),
        None,
    )
    target = next(
        (card for card in bot_field if card.get("instance_id") == payload.get("target_instance_id")),
        None,
    )
    if not attacker:
        return None
    projection = attack_utility_projection(
        attacker,
        target,
        bot_battlefield=player_field,
        player_battlefield=bot_field,
        player_hp=match["bot"].get("hp", 30),
        turn=match.get("turn", 1),
        player_wounded=match["bot"].get("wounded", False),
        bot_wounded=match["player"].get("wounded", False),
    )
    return float(projection.get("utility", 0) or 0)


def decision_telemetry_snapshot(match, action):
    """Capture legal options before mutation for human decision-quality telemetry."""
    normalized = canonical_action(action["type"], **(action.get("payload") or {}))
    # verify=False de propósito: a telemetria só conta/perfila as opções e NÃO
    # pode reexecutar o dispatcher. Com verify=True, simular o candidato
    # `end_turn` rodava a fase inteira do bot (choose_response fantasma) a cada
    # jogada do jogador — custo e efeito colateral observável. A enumeração de
    # _candidate_actions já filtra energia, slots, taunt e elegibilidade de ataque.
    options = legal_actions(match, verify=False)
    scored = [
        (candidate, _decision_action_score(match, candidate))
        for candidate in options
        if candidate.get("type") == normalized.get("type")
    ]
    scored = [(candidate, score) for candidate, score in scored if score is not None]
    chosen_score = _decision_action_score(match, normalized)
    best_action = max(scored, key=lambda item: item[1]) if scored else (None, None)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return build_decision_telemetry_payload(
        actor="human",
        action_type=normalized["type"],
        legal_action_count=len(options),
        chosen_action_id=_decision_action_id(normalized),
        chosen_action_fingerprint=hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24],
        best_action_id=_decision_action_id(best_action[0]) if best_action[0] else None,
        chosen_score=chosen_score,
        best_score=best_action[1],
        turn=match.get("turn"),
        profile_id=(match.get("bot_profile") or {}).get("id"),
        difficulty=(match.get("bot_difficulty") or {}).get("id"),
        archetype=dominant_family(
            [
                card
                for card in (
                    (match.get("player") or {}).get("field")
                    or (match.get("player") or {}).get("battlefield")
                    or []
                )
                if card
            ]
        ),
    )


def safe_decision_snapshot(match, action):
    """Telemetria observacional: nunca pode bloquear nem derrubar a jogada.

    Roda atrás de flag de ambiente e isola qualquer falha — uma exceção aqui
    jamais deve impedir o dispatch real da ação do jogador.
    """
    if not app.config.get("REBIRTH_ENABLE_DECISION_TELEMETRY", True):
        return None
    try:
        return decision_telemetry_snapshot(match, action)
    except Exception:
        app.logger.exception("rebirth.decision telemetry snapshot failed")
        return None


def record_decision_metrics(repo, user, match, decision_metrics):
    """Emite o evento decision_made apenas quando há métricas válidas."""
    if not decision_metrics:
        return
    record_match_telemetry(repo, user, match, "decision_made", **decision_metrics)


def _bot_legal_attack_count(match):
    """Count validated bot attack candidates before beam pruning."""
    from services.rebirth_keywords import forces_target, has_taunt_on_side

    bot_field = [
        card for card in ((match.get("bot") or {}).get("field") or (match.get("bot") or {}).get("battlefield") or [])
        if card
    ]
    player_field = [
        card
        for card in (
            (match.get("player") or {}).get("field")
            or (match.get("player") or {}).get("battlefield")
            or []
        )
        if card
    ]
    if has_taunt_on_side(player_field):
        player_field = [card for card in player_field if forces_target(card)]
    rows = tactical_utility_matrix(
        bot_field,
        player_field,
        player_hp=(match.get("player") or {}).get("hp", 30),
        turn=match.get("turn", 1),
        player_wounded=(match.get("player") or {}).get("wounded", False),
        bot_wounded=(match.get("bot") or {}).get("wounded", False),
    )
    return sum(1 for row in rows if row.get("allowed"))


def bot_decision_telemetry_payloads(match_before, events):
    """Rebuild pre-decision states so bot counts are not post-pruning."""
    shadow = deepcopy(match_before)
    decisions = []
    for event in events:
        event_payload = event.get("payload") or {}
        if event.get("event_type") == "ATTACK_DECLARED" and event_payload.get("automated"):
            try:
                legal_action_count = _bot_legal_attack_count(shadow) if shadow is not None else None
            except Exception:
                legal_action_count = None
            if legal_action_count is None:
                legal_action_count = event_payload.get("legal_action_count")
            decisions.append(
                build_decision_telemetry_payload(
                    actor="bot",
                    action_type="attack",
                    legal_action_count=legal_action_count,
                    chosen_action_id=(
                        f"attack:{event_payload.get('attacker_instance_id')}"
                        f"->{event_payload.get('target_instance_id') or 'hero'}"
                    ),
                    chosen_score=event_payload.get("chosen_score"),
                    best_score=event_payload.get("best_score"),
                    turn=shadow.get("turn"),
                    profile_id=event_payload.get("profile_id"),
                    difficulty=event_payload.get("difficulty_id"),
                    archetype=dominant_family(
                        [
                            card
                            for card in (
                                (shadow.get("bot") or {}).get("field")
                                or (shadow.get("bot") or {}).get("battlefield")
                                or []
                            )
                            if card
                        ]
                    ),
                )
            )
        if shadow is not None:
            try:
                shadow = reduce_event(shadow, event)
            except Exception:
                shadow = None
    return decisions


def require_internal_lab_access():
    if app.config.get("TESTING") or app.config.get("REBIRTH_ENABLE_INTERNAL_LAB"):
        return
    require_admin_token()


def internal_balance_matches(default=24):
    try:
        requested = int(request.args.get("matches", default) or default)
    except (TypeError, ValueError) as exc:
        raise RebirthError("Informe uma quantidade válida de partidas.", "invalid_balance_matches") from exc
    limit = int(app.config.get("REBIRTH_BALANCE_INTERACTIVE_MATCH_LIMIT", 24) or 24)
    return max(1, min(requested, limit))


def onboarding_difficulty(is_first_duel, progress, requested_difficulty=None):
    """Rampa de dificuldade pra suavizar o onboarding: easy → casual → normal.

    Evita o salto de 'mole' (tutorial, easy) direto para 'perde sempre' (normal
    cru). Visitante e jogador novo (< 4 partidas) jogam no casual; a escolha
    explícita do jogador é sempre respeitada.
    """
    if requested_difficulty:
        return requested_difficulty
    if is_first_duel:
        return "easy"
    games = 0
    if progress:
        games = int(progress.get("wins", 0) or 0) + int(progress.get("losses", 0) or 0)
    return "casual" if games < 4 else "normal"


def start_memory_rebirth_match(payload):
    is_first_duel = bool(payload.get("tutorial"))
    player_card_ids = DEFAULT_LOADOUT if is_first_duel else None
    bot_profile_id = "novice" if is_first_duel else None
    requested_seed = payload.get("seed")
    if is_first_duel and requested_seed is None:
        requested_seed = "guided-first-match"
    match = start_match(
        seed=requested_seed,
        player_card_ids=player_card_ids,
        player_name="Você",
        bot_profile_id=bot_profile_id,
        bot_difficulty_id=onboarding_difficulty(is_first_duel, None, payload.get("difficulty")),
        runtime_mode="singleplayer",
        apply_reducers_inline=False,
        first_duel=is_first_duel,
    )
    match = MATCH_STORE.save(match)
    remember_active_match(match)
    try:
        record_match_telemetry(None, None, match, "match_started", guest=True)
    except Exception:
        app.logger.info("rebirth.telemetry unavailable for guest match start")
    state = public_state(match)
    return json_success(
        state,
        match.get("result"),
        match_id=match["match_id"],
        reconnect=reconnect_payload(match),
        first_session=first_session_plan(
            account=account_payload(None),
            progression={},
            state=state,
            release_version=app.config["REBIRTH_RELEASE_VERSION"],
        ),
    )


def require_admin_token():
    expected = os.environ.get("REBIRTH_ADMIN_TOKEN") or app.config.get("REBIRTH_ADMIN_TOKEN")
    supplied = request.headers.get("X-Rebirth-Admin-Token")
    if not expected:
        raise RebirthPersistenceError("Concessões administrativas estão desativadas até configurar REBIRTH_ADMIN_TOKEN.", "admin_disabled", 403)
    if not supplied or not secrets.compare_digest(str(expected), str(supplied)):
        raise RebirthPersistenceError("Token administrativo Rebirth inválido.", "admin_forbidden", 403)
    return "rebirth-admin"


def request_json(required=False):
    payload = request.get_json(silent=True)
    if payload is None:
        if required and request.data:
            raise RebirthError("O corpo da requisição deve conter JSON válido.", "malformed_request")
        return {}
    if not isinstance(payload, dict):
        raise RebirthError("O corpo da requisição deve ser um objeto JSON.", "malformed_request")
    return payload


AUTHORITATIVE_COMBAT_FIELDS = {"exhausted", "has_attacked", "has_acted"}

# audit #15: a defesa anti-injeção era um denylist (3 campos). Denylist é
# frágil — um novo campo autoritativo esquecido vira brecha. O allowlist
# abaixo é o conjunto EXATO de chaves que os endpoints de combate aceitam no
# corpo; qualquer outra é rejeitada. O engine continua autoritativo de
# qualquer forma (ignora dano/winner injetados), mas isto fecha a porta cedo.
COMBAT_PAYLOAD_ALLOWED_FIELDS = {
    "match_id",
    "card_instance_id",
    "card_id",
    "field_slot",
    "slot",
    "attacker_instance_id",
    "target_instance_id",
}


def reject_authoritative_combat_fields(payload):
    pending = [payload]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if AUTHORITATIVE_COMBAT_FIELDS.intersection(value):
                raise RebirthError(
                    "O estado de ação é controlado exclusivamente pelo servidor.",
                    "authoritative_state_violation",
                    status=400,
                )
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)


def enforce_combat_payload_allowlist(payload):
    if not isinstance(payload, dict):
        return
    unexpected = [key for key in payload if key not in COMBAT_PAYLOAD_ALLOWED_FIELDS]
    if unexpected:
        raise RebirthError(
            "Campos não reconhecidos na ação de combate.",
            "unexpected_combat_fields",
            status=400,
        )


@app.context_processor
def inject_rebirth_security():
    user = current_user()
    return {
        "csrf_token": csrf_token,
        "rebirth_release_version": app.config["REBIRTH_RELEASE_VERSION"],
        "rebirth_navbar": rebirth_navbar_payload(user),
    }


REBIRTH_CSRF_PROTECTED_PREFIXES = ("/api/rebirth/", "/api/labs/")
# Endpoints intended for navigator.sendBeacon, which cannot attach custom
# headers — CSRF token travels in the request body instead. The endpoint
# verifies the token manually before mutating anything.
REBIRTH_CSRF_BODY_PATHS = frozenset({"/api/rebirth/telemetry/beacon"})
# S4 fix: Stripe webhook é POST server-to-server (Stripe → nosso backend).
# Não tem sessão, não tem cookie, não pode mandar X-Rebirth-CSRF. A
# autenticidade é verificada por Stripe-Signature (HMAC com whsec_).
# Por isso isentamos do CSRF middleware.
REBIRTH_CSRF_EXEMPT_PATHS = frozenset({"/api/rebirth/billing/webhook"})


@app.before_request
def protect_rebirth_mutations():
    if not app.config.get("REBIRTH_REQUIRE_CSRF", True):
        return None
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if not any(request.path.startswith(prefix) for prefix in REBIRTH_CSRF_PROTECTED_PREFIXES):
        return None
    if request.path in REBIRTH_CSRF_EXEMPT_PATHS:
        # Webhooks externos (Stripe etc) usam HMAC próprio em vez de CSRF.
        return None
    if request.path in REBIRTH_CSRF_BODY_PATHS:
        # CSRF verification is delegated to the endpoint (reads from body).
        return None

    expected = session.get("rebirth_csrf_token")
    supplied = request.headers.get("X-Rebirth-CSRF")
    if not expected or not supplied or not secrets.compare_digest(str(expected), str(supplied)):
        return json_error("O token CSRF do Rebirth é obrigatório.", "csrf_required", status=403)
    return None


@app.before_request
def _mark_request_start():
    g._rb_request_t0 = perf_counter()


@app.before_request
def _enforce_game_rate_limit():
    # Defense-in-depth on top of CSRF: cap per-IP request rate on the mutating
    # game + telemetry endpoints so they can't be scraped or flooded.
    limit = GAME_RATE_LIMITS.get(request.endpoint or "")
    if not limit or limit <= 0:
        return None
    key = f"{request.endpoint}:{request.remote_addr or 'local'}"
    if GAME_RATE_LIMITER.hit((key,), limit, GAME_RATE_LIMIT_WINDOW):
        return json_error("Muitas requisições em sequência. Aguarde alguns segundos.", "rate_limited", status=429)
    return None


@app.after_request
def add_server_timing(response):
    # Perf v103: Server-Timing expõe o custo do app por request no DevTools
    # de qualquer jogador e em RUM — como um estúdio mede produção de verdade.
    started = getattr(g, "_rb_request_t0", None)
    if started is not None:
        response.headers.setdefault(
            "Server-Timing", f"app;dur={(perf_counter() - started) * 1000:.1f}"
        )
    return response


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    return response


@app.get("/")
def index():
    return render_template("index.html", page=product_shell_payload(account=current_account()))


# === S5: SEO discovery — sitemap + robots ===

@app.get("/robots.txt")
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /rebirth/lab\n"
        "Disallow: /rebirth/balance\n"
        "\n"
        "Sitemap: https://ambitionzgame.com/sitemap.xml\n"
    )
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.get("/sitemap.xml")
def sitemap_xml():
    base = (os.environ.get("PUBLIC_BASE_URL") or "https://ambitionzgame.com").rstrip("/")
    public_paths = [
        "/",
        "/rebirth",
        "/rebirth/campaign",
        "/rebirth/collection",
        "/rebirth/shop",
        "/rebirth/billing",
        "/rebirth/progression",
        "/rebirth/ranking",
        "/rebirth/profile",
    ]
    urls = "\n".join(
        f"    <url><loc>{base}{p}</loc><changefreq>weekly</changefreq></url>"
        for p in public_paths
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )
    return body, 200, {"Content-Type": "application/xml; charset=utf-8"}


@app.get("/rebirth")
def rebirth():
    user = current_user()
    progress = rebirth_repo().progression(user["id"]) if user else None
    account = account_payload(user)
    return render_template(
        "rebirth.html",
        account=account,
        progression=progress or {},
        first_session=first_session_plan(
            account=account,
            progression=progress or {},
            release_version=app.config["REBIRTH_RELEASE_VERSION"],
        ),
    )


@app.get("/rebirth/campaign")
def rebirth_campaign():
    user = current_user()
    progress = rebirth_repo().get_campaign_progress(user["id"]) if user else None
    return render_template(
        "rebirth_campaign.html",
        account=account_payload(user),
        campaign=campaign_payload(progress),
    )


@app.get("/rebirth/account")
def rebirth_account():
    return render_template("rebirth_product.html", page=auth_plan_payload(account=current_account()))


@app.get("/rebirth/collection")
def rebirth_collection():
    user = current_user()
    repo = rebirth_repo()
    collection_counts = repo.collection_counts(user["id"]) if user else None
    loadout_ids = repo.loadout_card_ids(user["id"]) if user else None
    return render_template(
        "rebirth_product.html",
        page=collection_payload(
            account=account_payload(user),
            collection_counts=collection_counts,
            loadout_card_ids=loadout_ids,
        ),
        crafting_dust=(repo.get_dust(user["id"]) if user else 0),
    )


@app.get("/rebirth/shop")
def rebirth_shop():
    user = current_user()
    history, market, warnings = shop_data_for_user(user)
    page = shop_payload(account=account_payload(user), booster_history=history, market_offers=market)
    if warnings:
        page["warnings"] = warnings
    response = make_response(
        render_template(
            "rebirth_product.html",
            page=page,
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/rebirth/progression")
def rebirth_progression():
    user = current_user()
    progress = rebirth_repo().progression(user["id"]) if user else None
    return render_template("rebirth_product.html", page=progression_payload(account=account_payload(user), progression=progress))


@app.get("/rebirth/profile")
def rebirth_profile():
    user = current_user()
    profile = rebirth_repo().profile(user["id"]) if user else None
    return render_template("rebirth_product.html", page=profile_payload(account=account_payload(user), profile=profile))


@app.get("/rebirth/history")
def rebirth_history():
    user = current_user()
    repo = rebirth_repo()
    matches = repo.match_history(user["id"], limit=12) if user else []
    ledger = repo.economy_ledger(user["id"], limit=20) if user else []
    return render_template(
        "rebirth_product.html",
        page=history_payload(account=account_payload(user), matches=matches, ledger=ledger),
    )


@app.get("/rebirth/desktop")
def rebirth_desktop():
    return render_template("rebirth_product.html", page=desktop_payload())


@app.get("/rebirth/onboarding")
def rebirth_onboarding():
    user = current_user()
    progress = rebirth_repo().progression(user["id"]) if user else None
    return render_template("rebirth_product.html", page=onboarding_payload(account=account_payload(user), progression=progress))


@app.get("/rebirth/balance")
def rebirth_balance():
    try:
        require_internal_lab_access()
        return render_template("rebirth_product.html", page=balance_payload(simulation=simulate_balance(matches=internal_balance_matches())))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


def release_since_arg():
    since = request.args.get("since") or None
    return since.replace(" ", "+") if since else None


@app.get("/rebirth/release")
def rebirth_release():
    repo = rebirth_repo()
    since = release_since_arg()
    gates = external_gate_payload(app.config, require_external_evidence=True)
    dashboard = beta_dashboard_payload(repo, since=since)
    live_balance = live_balance_payload(repo, since=since, release_version=app.config["REBIRTH_RELEASE_VERSION"])
    public_gate = public_beta_gate_payload(
        repo,
        since=since,
        release_version=app.config["REBIRTH_RELEASE_VERSION"],
        live_balance=live_balance,
    )
    phase_report_audit = audit_phase_reports()
    return render_template(
        "rebirth_product.html",
        page=release_payload(
            gates=gates,
            dashboard=dashboard,
            content_report=content_pipeline_report(),
            live_balance=live_balance,
            public_beta_gate=public_gate,
            phase_report_audit=phase_report_audit,
            release_readiness=release_readiness_report(
                gates,
                public_gate,
                phase_report_audit=phase_report_audit,
            ),
        ),
    )


@app.get("/rebirth/support")
def rebirth_support():
    user = current_user()
    return render_template("rebirth_product.html", page=support_payload(account=account_payload(user)))


@app.get("/rebirth/lab")
def rebirth_lab():
    return render_template("rebirth_product.html", page=lab_payload())


# === S3: ranking ELO ===

@app.get("/rebirth/ranking")
def rebirth_ranking_page():
    user = current_user()
    repo = rebirth_repo()
    top = repo.get_ranking_top(limit=20)
    me = repo.get_user_ranking(user["id"]) if user else None
    return render_template(
        "rebirth_ranking.html",
        account=account_payload(user),
        top=top,
        me=me,
    )


@app.get("/api/rebirth/ranking/top")
def api_rebirth_ranking_top():
    limit = request.args.get("limit", "20")
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20
    return json_payload(top=rebirth_repo().get_ranking_top(limit=limit))


@app.get("/api/rebirth/ranking/me")
def api_rebirth_ranking_me():
    try:
        user = require_user()
        return json_payload(ranking=rebirth_repo().get_user_ranking(user["id"]))
    except RebirthPersistenceError as error:
        # require_user() levanta RebirthPersistenceError(auth_required, 401)
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


# === K3: Deck Builder — endpoints + página ===

@app.get("/api/rebirth/catalog")
def api_rebirth_catalog():
    """Retorna o catálogo completo de cartas (sem dados sensíveis).
    Usado pelo deck builder + ferramentas de análise."""
    from services.rebirth_cards import CARD_CATALOG
    # Stripa campos internos pesados (heuristic_vector, art_status, etc)
    fields = (
        "id", "name", "type", "family", "element", "tier", "rarity",
        "cost", "attack", "guard", "ability_name", "ability_text",
        "keywords", "synergy", "art",
    )
    catalog = [
        {k: c.get(k) for k in fields if k in c}
        for c in CARD_CATALOG
    ]
    return json_payload(catalog=catalog, count=len(catalog))




@app.get("/rebirth/deck-builder")
def rebirth_deck_builder_page():
    user = current_user()
    repo = rebirth_repo()
    decks = repo.list_decks(user["id"]) if user else []
    return render_template(
        "rebirth_deck_builder.html",
        account=account_payload(user),
        decks=decks,
    )


@app.get("/api/rebirth/decks")
def api_rebirth_decks_list():
    try:
        user = require_user()
        return json_payload(decks=rebirth_repo().list_decks(user["id"]))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.post("/api/rebirth/decks")
def api_rebirth_decks_create():
    try:
        user = require_user()
        payload = request_json(required=True)
        result = rebirth_repo().save_deck(
            user["id"],
            name=payload.get("name", "Novo Deck"),
            cards=payload.get("cards", []),
        )
        return json_payload(deck=result)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.put("/api/rebirth/decks/<int:deck_id>")
def api_rebirth_decks_update(deck_id):
    try:
        user = require_user()
        payload = request_json(required=True)
        result = rebirth_repo().save_deck(
            user["id"],
            name=payload.get("name", "Deck"),
            cards=payload.get("cards", []),
            deck_id=deck_id,
        )
        return json_payload(deck=result)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.delete("/api/rebirth/decks/<int:deck_id>")
def api_rebirth_decks_delete(deck_id):
    try:
        user = require_user()
        return json_payload(result=rebirth_repo().delete_deck(user["id"], deck_id))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.post("/api/rebirth/decks/<int:deck_id>/activate")
def api_rebirth_decks_activate(deck_id):
    try:
        user = require_user()
        return json_payload(result=rebirth_repo().set_active_deck(user["id"], deck_id))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


# === S4: Stripe billing — venda de gems ===


def rebirth_billing_status():
    secret = os.environ.get("STRIPE_SECRET_KEY", "")
    live_key = secret.startswith("sk_live_")
    billing_enabled = bool(app.config.get("REBIRTH_ENABLE_BILLING"))
    live_allowed = bool(app.config.get("REBIRTH_ALLOW_STRIPE_LIVE"))
    disabled = not billing_enabled or (live_key and not live_allowed)
    reason = None
    if not billing_enabled:
        reason = "Pagamentos reais estão desligados durante o beta fechado."
    elif live_key and not live_allowed:
        reason = "Chaves Stripe live foram detectadas, mas REBIRTH_ALLOW_STRIPE_LIVE não está ativo."
    return {
        "enabled": billing_enabled and not (live_key and not live_allowed),
        "live_key_present": live_key,
        "live_allowed": live_allowed,
        "disabled": disabled,
        "reason": reason,
    }


def require_rebirth_billing_enabled():
    status = rebirth_billing_status()
    if status["disabled"]:
        raise RebirthError(status["reason"], "monetization_disabled", status=410)
    return status


@app.get("/rebirth/billing")
def rebirth_billing_page():
    user = current_user()
    repo = rebirth_repo()
    packages = [{"id": pid, **info} for pid, info in repo.BILLING_PACKAGES.items()]
    return render_template(
        "rebirth_billing.html",
        account=account_payload(user),
        packages=packages,
        billing_status=rebirth_billing_status(),
        stripe_publishable_key=os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
    )


@app.get("/terms")
def terms():
    return render_template("terms.html")


@app.get("/privacy")
def privacy():
    return render_template("privacy.html")


@app.get("/data-deletion")
def data_deletion():
    return render_template("data_deletion.html")


@app.get("/feedback")
def feedback():
    return redirect("/rebirth/support", code=302)


@app.get("/closed-test")
def closed_test():
    return redirect("/rebirth/release", code=302)


@app.get("/first-session")
def first_session():
    return redirect("/rebirth/onboarding", code=302)


@app.post("/api/rebirth/billing/checkout")
def api_rebirth_billing_checkout():
    """Cria uma Stripe Checkout Session pro pacote selecionado. Retorna
    a URL de redirect que o frontend abre. Requer STRIPE_SECRET_KEY no env."""
    try:
        user = require_user()
        payload = request_json(required=True)
        package_id = str(payload.get("package_id") or "")
        repo = rebirth_repo()
        pkg = repo.BILLING_PACKAGES.get(package_id)
        if not pkg:
            return json_error("Pacote inválido.", "billing_invalid_package", 400)
        require_rebirth_billing_enabled()
        # invalida package_id que o frontend tentou enviar com whitespace etc
        secret = os.environ.get("STRIPE_SECRET_KEY")
        if not secret:
            return json_error(
                "Stripe não está configurado neste ambiente.",
                "billing_not_configured",
                503,
            )
        try:
            import stripe  # noqa: WPS433
        except ImportError:
            return json_error(
                "Dependência stripe não instalada (pip install stripe).",
                "billing_not_configured",
                503,
            )
        stripe.api_key = secret
        public_base = (os.environ.get("PUBLIC_BASE_URL") or request.url_root).rstrip("/")
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            client_reference_id=str(user["id"]),
            line_items=[{
                "price_data": {
                    "currency": "brl",
                    "unit_amount": int(pkg["price_cents"]),
                    "product_data": {"name": f"Ambitionz Rebirth · {pkg['label']}"},
                },
                "quantity": 1,
            }],
            metadata={"user_id": str(user["id"]), "package_id": package_id},
            success_url=f"{public_base}/rebirth/billing?status=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{public_base}/rebirth/billing?status=cancel",
        )
        return json_payload(checkout_url=session.url, session_id=session.id)
    except RebirthPersistenceError as error:
        # require_user() levanta RebirthPersistenceError("auth_required", 401)
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)
    except Exception as exc:  # noqa: BLE001
        return json_error(str(exc), "billing_checkout_failed", 500)


@app.post("/api/rebirth/billing/webhook")
def api_rebirth_billing_webhook():
    """Webhook Stripe: processa checkout.session.completed e credita gems.
    Configurado na Stripe Dashboard apontando pra este endpoint."""
    if rebirth_billing_status()["disabled"]:
        return ("billing_disabled", 200)
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        return ("", 503)
    try:
        import stripe  # noqa: WPS433
    except ImportError:
        return ("", 503)
    payload = request.get_data(as_text=False)
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception as exc:  # noqa: BLE001
        return (f"webhook_invalid: {exc}", 400)
    if event["type"] == "checkout.session.completed":
        sess = event["data"]["object"]
        user_id = int(sess.get("metadata", {}).get("user_id") or 0)
        package_id = sess.get("metadata", {}).get("package_id") or ""
        if user_id and package_id:
            try:
                rebirth_repo().credit_billing_gems(user_id, package_id, sess["id"])
            except RebirthPersistenceError as err:
                # 500 força o retry do Stripe: devolver 200 aqui descartava o
                # evento com o cliente já cobrado e as gems não creditadas.
                app.logger.error("billing webhook credit_failed: %s (session=%s)", err.code, sess.get("id"))
                return (f"credit_failed: {err.code}", 500)
    return ("", 200)


@app.get("/health")
def health():
    try:
        persistence = rebirth_repo().health_status()
        return jsonify(
            {
                "ok": True,
                "status": "healthy",
                "product": "Ambitionz Rebirth",
                "architecture": "Ambitionz Rebirth PostgreSQL Foundation",
                "persistence": persistence,
            }
        )
    except RebirthPersistenceError as error:
        return (
            jsonify(
                {
                    "ok": False,
                    "status": "unhealthy",
                    "product": "Ambitionz Rebirth",
                    "architecture": "Ambitionz Rebirth PostgreSQL Foundation",
                    "error": {"code": error.code, "message": str(error)},
                }
            ),
            503,
        )


@app.get("/service-worker.js")
def service_worker():
    response = send_from_directory(
        os.path.join(app.root_path, "static", "js"),
        "service-worker.js",
        mimetype="application/javascript",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.get("/manifest.webmanifest")
def webmanifest():
    return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")


@app.post("/api/rebirth/start")
def api_rebirth_start():
    try:
        payload = request_json(required=False)
        if not session.get("rebirth_session_token"):
            return start_memory_rebirth_match(payload)
        user = current_user()
        repo = rebirth_repo() if user else None
        player_card_ids = None
        player_name = "Você"
        bot_profile_id = None
        progress = None
        # "First duel" é ativado explicitamente pelo cliente via payload.tutorial.
        # O frontend (rebirth.js > RebirthCoach.shouldGuideFirstMatch) já manda
        # tutorial=true quando clashes=0 e tutorial_complete=false, então o
        # auto-detect mora lá. Mantemos esta rota agnostica para preservar
        # contratos de testes que passam seeds custom sem o flag.
        is_first_duel = bool(payload.get("tutorial"))
        if user:
            progress = repo.progression(user["id"])
            player_card_ids = repo.loadout_card_ids(user["id"])
            player_name = user["username"]
            if is_first_duel:
                player_card_ids = DEFAULT_LOADOUT
                bot_profile_id = "novice"
            elif progress and int(progress.get("clashes", 0) or 0) < 3:
                # A primeira sequência após o tutorial deve ensinar leitura
                # de mesa; o perfil agressivo é reservado para depois que o
                # jogador já registrou seus primeiros clashes.
                bot_profile_id = "defensive"
        requested_seed = payload.get("seed")
        if is_first_duel and requested_seed is None:
            requested_seed = "guided-first-match"
        engine_seed = f"user:{user['id']}:{requested_seed}" if user and requested_seed is not None else requested_seed

        def build_match(seed_value):
            return start_match(
                seed=seed_value,
                player_card_ids=player_card_ids,
                player_name=player_name,
                bot_profile_id=bot_profile_id,
                bot_difficulty_id=onboarding_difficulty(is_first_duel, progress, payload.get("difficulty")),
                runtime_mode="singleplayer",
                apply_reducers_inline=False,
                first_duel=is_first_duel,
            )

        match = build_match(engine_seed)
        if engine_seed is not None:
            try:
                existing = MATCH_STORE.get(match["match_id"])
            except RebirthError:
                existing = None
            if existing is not None:
                # Seed reutilizada gerava o MESMO match_id e devolvia a partida
                # antiga em vez de criar uma nova. Salga a seed na colisão.
                match = build_match(f"{engine_seed}:retry:{secrets.token_hex(4)}")
        if user:
            match["owner_user_id"] = user["id"]
            match["seed"] = str(requested_seed or "")
        match = MATCH_STORE.save(match)
        remember_active_match(match, user=user)
        # A partida NÃO é persistida no start: cada visita ao /rebirth dispara
        # um start automático e enchia o histórico de partidas-fantasma. O
        # primeiro comando real (play/attack/next-turn) faz o primeiro upsert.
        record_match_telemetry(repo, user, match, "match_started", guest=not bool(user))
        state = public_state(match)
        return json_success(
            state,
            match.get("result"),
            match_id=match["match_id"],
            reconnect=reconnect_payload(match, user=user),
            first_session=first_session_plan(
                account=account_payload(user),
                progression=progress or {},
                state=state,
                release_version=app.config["REBIRTH_RELEASE_VERSION"],
            ),
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/campaign")
def api_rebirth_campaign():
    try:
        user = require_user()
        progress = rebirth_repo().get_campaign_progress(user["id"])
        return json_payload(campaign=campaign_payload(progress))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.post("/api/rebirth/campaign/start")
def api_rebirth_campaign_start():
    try:
        payload = request_json(required=True)
        node_id = payload.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise RebirthError("Informe um nó válido da campanha.", "invalid_campaign_payload")
        node = get_node(node_id.strip())
        if not node:
            raise RebirthError("Este encontro da campanha não existe.", "campaign_node_not_found")

        user = require_user()
        repo = rebirth_repo()
        progress = repo.get_campaign_progress(user["id"])
        if not is_unlocked(node["id"], progress):
            raise RebirthError("Venca o encontro anterior para liberar este duelo.", "campaign_node_locked")

        attempt = repo.start_campaign_attempt(user["id"], node["id"], CAMPAIGN_VERSION)
        match = start_match(
            seed=f"campaign:{user['id']}:{node['id']}:{attempt}",
            player_card_ids=repo.loadout_card_ids(user["id"]),
            player_name=user["username"],
            bot_profile_id=node["bot_profile_id"],
            bot_difficulty_id=node["bot_difficulty_id"],
            runtime_mode="singleplayer",
            apply_reducers_inline=False,
            first_duel=False,
            bot_card_ids=node["bot_deck_override"],
            player_hp=node["player_hp"],
            bot_hp=node["bot_hp"],
            campaign_version=CAMPAIGN_VERSION,
            campaign_node=node["id"],
            campaign_attempt=attempt,
            campaign_modifiers=node["modifiers"],
            campaign_presentation={
                **node["presentation"],
                "name": node["name"],
                "intro": node["intro"],
                "order": node["order"],
            },
            campaign_advice={
                "tip": node["loss_tip"],
                "key_card": node["key_card"],
            },
        )
        match["owner_user_id"] = user["id"]
        match["seed"] = f"campaign:{node['id']}:{attempt}"
        match = MATCH_STORE.save(match)
        remember_active_match(match, user=user)
        record_match_telemetry(
            repo,
            user,
            match,
            "match_started",
            campaign_node=node["id"],
            campaign_attempt=attempt,
        )
        return json_success(
            public_state(match),
            match.get("result"),
            match_id=match["match_id"],
            reconnect=reconnect_payload(match, user=user),
            campaign=campaign_payload(repo.get_campaign_progress(user["id"])),
            campaign_reward=None,
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/labs/fusion")
def api_labs_fusion():
    if not app.config.get("REBIRTH_LABS_ENABLED"):
        return json_error("Rebirth Labs esta desativado.", "labs_disabled", status=404)
    try:
        payload = request_json(required=True)
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        ensure_match_access(match, user=user)
        fusion = dispatch_command(
            match,
            FuseFieldPairCommand(
                player_id=payload.get("player_id"),
                source_instance_a=payload.get("source_instance_a"),
                source_instance_b=payload.get("source_instance_b"),
            ),
        )
        repo = rebirth_repo() if user else None
        persist_match_if_owned(repo, user, match)
        campaign_reward = settle_campaign_victory(repo, user, match)
        record_match_telemetry(
            repo,
            user,
            match,
            "field_pair_fused",
            source_instance_a=payload.get("source_instance_a"),
            source_instance_b=payload.get("source_instance_b"),
        )
        return json_success(public_state(match), match.get("result"), fusion=fusion, campaign_reward=campaign_reward)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/play-card")
def api_rebirth_play_card():
    try:
        payload = request_json(required=True)
        reject_authoritative_combat_fields(payload)
        enforce_combat_payload_allowlist(payload)
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        repo = rebirth_repo() if user else None
        ensure_match_access(match, user=user)
        if payload.get("attacker_instance_id"):
            decision_metrics = safe_decision_snapshot(
                match,
                canonical_action(
                    "attack",
                    attacker_instance_id=payload.get("attacker_instance_id"),
                    target_instance_id=payload.get("target_instance_id"),
                ),
            )
            dispatch_command(
                match,
                DeclareAttackCommand(
                    attacker_instance_id=payload.get("attacker_instance_id"),
                    target_instance_id=payload.get("target_instance_id"),
                ),
            )
        else:
            decision_metrics = safe_decision_snapshot(
                match,
                canonical_action(
                    "play_card",
                    card_instance_id=payload.get("card_instance_id"),
                    card_id=payload.get("card_id"),
                    field_slot=payload.get("field_slot", payload.get("slot")),
                    target_instance_id=payload.get("target_instance_id"),
                ),
            )
            dispatch_command(
                match,
                SummonCardCommand(
                    card_instance_id=payload.get("card_instance_id"),
                    card_id=payload.get("card_id"),
                    field_slot=payload.get("field_slot", payload.get("slot")),
                    target_instance_id=payload.get("target_instance_id"),
                ),
            )
        state = public_state(match)
        progress = None
        reward = match_reward_payload(None, None, state)
        campaign_reward = None
        if user:
            if state.get("last_clash") and state.get("phase") in {"result", "finished"}:
                before = repo.progression(user["id"])
                progress = repo.record_clash_result(user["id"], state)
                reward = clash_reward_payload_from_progress(before, progress, state)
            repo.upsert_match_history(user["id"], match)
            campaign_reward = settle_campaign_victory(repo, user, match)
        record_decision_metrics(repo, user, match, decision_metrics)
        record_match_telemetry(
            repo,
            user,
            match,
            "card_played",
            card_id=payload.get("card_id"),
            card_instance_id=payload.get("card_instance_id"),
        )
        return json_success(
            state,
            match.get("result"),
            progression=progress,
            match_reward=reward,
            campaign_reward=campaign_reward,
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/attack")
def api_rebirth_attack():
    try:
        payload = request_json(required=True)
        reject_authoritative_combat_fields(payload)
        enforce_combat_payload_allowlist(payload)
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        repo = rebirth_repo() if user else None
        ensure_match_access(match, user=user)
        decision_metrics = safe_decision_snapshot(
            match,
            canonical_action(
                "attack",
                attacker_instance_id=payload.get("attacker_instance_id"),
                target_instance_id=payload.get("target_instance_id"),
            ),
        )
        dispatch_command(
            match,
            DeclareAttackCommand(
                attacker_instance_id=payload.get("attacker_instance_id"),
                target_instance_id=payload.get("target_instance_id"),
            ),
        )
        state = public_state(match)
        progress = None
        reward = match_reward_payload(None, None, state)
        campaign_reward = None
        if user:
            if state.get("last_clash") and state.get("phase") in {"result", "finished"}:
                before = repo.progression(user["id"])
                progress = repo.record_clash_result(user["id"], state)
                reward = clash_reward_payload_from_progress(before, progress, state)
            repo.upsert_match_history(user["id"], match)
            campaign_reward = settle_campaign_victory(repo, user, match)
        record_decision_metrics(repo, user, match, decision_metrics)
        record_match_telemetry(
            repo,
            user,
            match,
            "combat_resolved",
            attacker_instance_id=payload.get("attacker_instance_id"),
            target_instance_id=payload.get("target_instance_id"),
        )
        return json_success(
            state,
            match.get("result"),
            progression=progress,
            match_reward=reward,
            campaign_reward=campaign_reward,
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/evolve")
def api_rebirth_evolve():
    try:
        payload = request_json(required=True)
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        ensure_match_access(match, user=user)
        decision_metrics = safe_decision_snapshot(
            match,
            canonical_action("evolve", card_id=payload.get("card_id")),
        )
        evolved = dispatch_command(match, EvolveDuplicateCommand(card_id=payload.get("card_id")))
        repo = rebirth_repo() if user else None
        persist_match_if_owned(repo, user, match)
        campaign_reward = settle_campaign_victory(repo, user, match)
        record_decision_metrics(repo, user, match, decision_metrics)
        record_match_telemetry(repo, user, match, "card_evolved", card_id=payload.get("card_id"))
        return json_success(public_state(match), match.get("result"), evolved=evolved, campaign_reward=campaign_reward)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/next-turn")
def api_rebirth_next_turn():
    try:
        payload = request_json(required=True)
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        ensure_match_access(match, user=user)
        decision_metrics = safe_decision_snapshot(
            match,
            canonical_action("end_turn", turn=match.get("turn")),
        )
        match_before_bot_turn = deepcopy(match)
        events_before = len(match.get("events") or [])
        dispatch_command(match, EndTurnCommand(turn=match.get("turn")))
        # Eventos da fase do bot: o cliente encena invocações/ataques em
        # sequência antes de aplicar o estado final (turno do bot visível).
        bot_phase_events = [dict(event) for event in (match.get("events") or [])[events_before:]]
        repo = rebirth_repo() if user else None
        persist_match_if_owned(repo, user, match)
        campaign_reward = settle_campaign_victory(repo, user, match)
        for bot_decision in bot_decision_telemetry_payloads(match_before_bot_turn, bot_phase_events):
            record_match_telemetry(repo, user, match, "decision_made", **bot_decision)
        record_decision_metrics(repo, user, match, decision_metrics)
        record_match_telemetry(repo, user, match, "turn_ended")
        return json_success(
            public_state(match),
            match.get("result"),
            campaign_reward=campaign_reward,
            bot_phase_events=bot_phase_events,
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/mulligan")
def api_rebirth_mulligan():
    try:
        payload = request_json(required=True)
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        ensure_match_access(match, user=user)
        decision_metrics = safe_decision_snapshot(match, canonical_action("mulligan"))
        dispatch_command(match, MulliganCommand())
        repo = rebirth_repo() if user else None
        persist_match_if_owned(repo, user, match)
        record_decision_metrics(repo, user, match, decision_metrics)
        record_match_telemetry(repo, user, match, "hand_mulliganed")
        return json_success(public_state(match), match.get("result"), mulliganed=True)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/shell")
def api_rebirth_shell():
    return json_payload(shell=product_shell_payload(account=current_account()))


@app.get("/api/rebirth/auth-plan")
def api_rebirth_auth_plan():
    return json_payload(auth=auth_plan_payload(account=current_account()))


@app.get("/api/rebirth/session")
def api_rebirth_session():
    user = current_user()
    wallet = rebirth_repo().wallet_payload(user["id"]) if user else guest_wallet_payload()
    progress = rebirth_repo().progression(user["id"]) if user else {}
    account = account_payload(user)
    return json_payload(
        account=account,
        wallet=wallet,
        reconnect=reconnect_payload(user=user),
        first_session=first_session_plan(
            account=account,
            progression=progress or {},
            release_version=app.config["REBIRTH_RELEASE_VERSION"],
        ),
        **csrf_payload(),
    )


@app.get("/api/rebirth/csrf")
def api_rebirth_csrf():
    return json_payload(**csrf_payload())


@app.get("/api/rebirth/wallet")
def api_rebirth_wallet():
    try:
        user = current_user()
        if not user:
            return json_payload(wallet=guest_wallet_payload())
        return json_payload(wallet=rebirth_repo().wallet_payload(user["id"]))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


def _verification_link(token):
    base = app.config.get("PUBLIC_BASE_URL") or request.host_url.rstrip("/")
    return f"{base}/rebirth/verify?token={token}"


def send_verification_email(user_email, token):
    """Best-effort verification email. Falls back to logging the link when
    SMTP isn't configured (email_service handles that), so the flow never
    blocks registration and works in dev immediately."""
    if not user_email or not token:
        return False
    link = _verification_link(token)
    subject = "Confirme seu email — Ambitionz Rebirth"
    body = (
        "Bem-vindo ao Ambitionz Rebirth!\n\n"
        "Confirme seu email para garantir sua coleção, nível e recompensas:\n"
        f"{link}\n\n"
        "Se você não criou esta conta, ignore este email."
    )
    try:
        return bool(send_email(user_email, subject, body))
    except Exception:
        app.logger.exception("rebirth.verification email send failed")
        return False


@app.post("/api/rebirth/auth/register")
def api_rebirth_auth_register():
    try:
        payload = request_json(required=True)
        if not app.config.get("TESTING"):
            if payload.get("age_confirmed") is not True or payload.get("privacy_accepted") is not True:
                raise RebirthError(
                    "Confirme idade minima e aceite Termos/Privacidade para criar a conta beta.",
                    "consent_required",
                    status=400,
                )
        enforce_auth_rate_limit("register", payload.get("email") or payload.get("username"))
        user = rebirth_repo().create_user(
            payload.get("username"),
            payload.get("email"),
            payload.get("password"),
        )
        # Token transiente só pra disparar o email; não vai no payload público.
        send_verification_email(user.get("email"), user.pop("verification_token", None))
        token = establish_rebirth_session(user)
        return json_payload(account=account_payload(user), csrf=token, **auth_sync_payload(user))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/auth/verify-email")
def api_rebirth_auth_verify_email():
    try:
        payload = request_json(required=True)
        token = str(payload.get("token") or "").strip()
        if not token:
            raise RebirthError("Informe o token de verificação.", "invalid_verification_token")
        user = rebirth_repo().verify_email_token(token)
        if not user:
            raise RebirthError("Token de verificação inválido ou já utilizado.", "verification_failed", status=410)
        return json_payload(account=account_payload(user), verified=True)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/auth/resend-verification")
def api_rebirth_auth_resend_verification():
    try:
        user = require_user()
        enforce_auth_rate_limit("resend_verification", user.get("email"))
        if user.get("email_verified"):
            return json_payload(account=account_payload(user), already_verified=True)
        token = rebirth_repo().regenerate_verification_token(user["id"])
        if not token:
            return json_payload(account=account_payload(user), already_verified=True)
        send_verification_email(user.get("email"), token)
        return json_payload(account=account_payload(user), resent=True)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/rebirth/verify")
def rebirth_verify_email_link():
    token = str(request.args.get("token") or "").strip()
    verified = bool(token) and bool(rebirth_repo().verify_email_token(token)) if token else False
    return redirect(f"/rebirth?verified={'1' if verified else '0'}", code=302)


@app.post("/api/rebirth/auth/login")
def api_rebirth_auth_login():
    try:
        payload = request_json(required=True)
        enforce_auth_rate_limit("login", payload.get("email"))
        user = rebirth_repo().authenticate(payload.get("email"), payload.get("password"))
        token = establish_rebirth_session(user)
        return json_payload(account=account_payload(user), csrf=token, **auth_sync_payload(user))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/auth/logout")
def api_rebirth_auth_logout():
    token = clear_rebirth_session()
    return json_payload(account=account_payload(None), csrf=token)


@app.post("/api/rebirth/auth/change-password")
def api_rebirth_auth_change_password():
    try:
        payload = request_json(required=True)
        user = require_user()
        enforce_auth_rate_limit("change-password", user["id"])
        rebirth_repo().change_password(user["id"], payload.get("current_password"), payload.get("new_password"))
        return json_payload(account=account_payload(user), message="Senha atualizada.")
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/collection")
def api_rebirth_collection():
    user = current_user()
    repo = rebirth_repo()
    collection_counts = repo.collection_counts(user["id"]) if user else None
    loadout_ids = repo.loadout_card_ids(user["id"]) if user else None
    return json_payload(
        collection=collection_payload(
            account=account_payload(user),
            collection_counts=collection_counts,
            loadout_card_ids=loadout_ids,
        )
    )


@app.post("/api/rebirth/loadout")
def api_rebirth_loadout():
    try:
        payload = request_json(required=True)
        user = require_user()
        repo = rebirth_repo()
        saved = repo.validate_and_save_loadout(user["id"], payload.get("card_ids"))
        return json_payload(loadout=validate_loadout(saved, collection_counts=repo.collection_counts(user["id"])))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except ValueError as error:
        return json_error(str(error), "invalid_loadout", status=400)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/shop")
def api_rebirth_shop():
    user = current_user()
    history, market, warnings = shop_data_for_user(user)
    shop = shop_payload(account=account_payload(user), booster_history=history, market_offers=market)
    if warnings:
        shop["warnings"] = warnings
    return json_payload(shop=shop)


@app.get("/api/rebirth/market/offers")
def api_rebirth_market_offers():
    try:
        user = current_user()
        offers = rebirth_repo().market_offers(exclude_user_id=user["id"] if user else None)
        return json_payload(market={"offers": offers, "fee_rate": "5%", "currencies": ["GOLD"]})
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.post("/api/rebirth/market/list")
def api_rebirth_market_list():
    try:
        user = require_user()
        payload = request_json(required=True)
        repo = rebirth_repo()
        offer = repo.create_market_offer(user["id"], payload.get("card_id"), payload.get("price"), payload.get("currency_type"))
        offers = repo.market_offers(exclude_user_id=user["id"])
        return json_payload(market={"offer": offer, "offers": offers})
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except ValueError as error:
        return json_error(str(error), "invalid_market_card", status=400)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/market/buy")
def api_rebirth_market_buy():
    try:
        user = require_user()
        payload = request_json(required=True)
        repo = rebirth_repo()
        purchase = repo.buy_market_offer(user["id"], payload.get("offer_id"))
        offers = repo.market_offers(exclude_user_id=user["id"])
        wallet = purchase.get("buyer_wallet") or rebirth_repo().wallet_payload(user["id"])
        return json_payload(market={"purchase": purchase, "offers": offers}, wallet=wallet)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/booster/open")
def api_rebirth_booster_open():
    try:
        payload = request_json(required=False)
        user = require_user()
        seed = payload.get("seed")
        booster = open_booster(seed)
        repo = rebirth_repo()
        repo.record_booster(user["id"], booster, seed)
        collection_counts = repo.collection_counts(user["id"])
        loadout_card_ids = repo.loadout_card_ids(user["id"])
        progression = repo.progression(user["id"])
        return json_payload(
            booster=booster,
            collection=collection_payload(
                account=account_payload(user),
                collection_counts=collection_counts,
                loadout_card_ids=loadout_card_ids,
            ),
            progression=progression,
            deck_suggestions=deck_suggestions(
                profile=progression,
                collection_counts=collection_counts,
                loadout_card_ids=loadout_card_ids,
                booster_cards=booster.get("cards") or [],
            ),
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/shop/verify-receipt")
def api_rebirth_shop_verify_receipt():
    return json_error(
        "Compras de Coinz permanecem desativadas ate a integracao oficial das lojas.",
        "monetization_disabled",
        status=410,
    )


@app.get("/api/rebirth/progression")
def api_rebirth_progression():
    user = current_user()
    progress = rebirth_repo().progression(user["id"]) if user else None
    return json_payload(progression=progression_payload(account=account_payload(user), progression=progress))


@app.get("/api/rebirth/profile")
def api_rebirth_profile():
    user = current_user()
    profile = rebirth_repo().profile(user["id"]) if user else None
    return json_payload(profile=profile_payload(account=account_payload(user), profile=profile))


@app.get("/api/rebirth/match-history")
def api_rebirth_match_history():
    try:
        user = require_user()
        return json_payload(history=rebirth_repo().match_history(user["id"], limit=int_arg("limit", 12, 50)))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.get("/api/rebirth/match-history/<match_id>/events")
def api_rebirth_match_events(match_id):
    try:
        user = require_user()
        return json_payload(events=rebirth_repo().match_events(user["id"], match_id, limit=int_arg("limit", 50, 200)))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.get("/api/rebirth/match-state/<match_id>")
def api_rebirth_match_state(match_id):
    try:
        user = require_user()
        state = rebirth_repo().match_state(user["id"], match_id)
        return json_payload(state=state)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/resume")
def api_rebirth_resume():
    try:
        payload = request_json(required=True)
        user = current_user()
        match_id = str(payload.get("match_id") or session.get("rebirth_active_match_id") or "").strip()
        if not match_id:
            raise RebirthError("Informe match_id para retomar a partida.", "missing_match")
        if user:
            restored = rebirth_repo().runtime_match_state(user["id"], match_id)
            match = MATCH_STORE.save(restored)
            ensure_match_access(match, user=user)
            repo = rebirth_repo()
        else:
            if match_id != session.get("rebirth_active_match_id"):
                raise RebirthError("Esta partida de visitante nao pertence a sessao atual.", "match_forbidden", status=403)
            match = MATCH_STORE.get(match_id)
            repo = None
        remember_active_match(match, user=user)
        record_match_telemetry(repo, user, match, "match_resumed")
        state = public_state(match)
        return json_success(
            state,
            match.get("result"),
            match_id=match["match_id"],
            resumed=True,
            reconnect=reconnect_payload(match, user=user),
            first_session=first_session_plan(
                account=account_payload(user),
                progression=rebirth_repo().progression(user["id"]) if user else {},
                state=state,
                release_version=app.config["REBIRTH_RELEASE_VERSION"],
            ),
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/economy-ledger")
def api_rebirth_economy_ledger():
    try:
        user = require_user()
        return json_payload(ledger=rebirth_repo().economy_ledger(user["id"], limit=int_arg("limit", 30, 100)))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.post("/api/rebirth/progression/claim-daily")
def api_rebirth_progression_claim_daily():
    try:
        user = require_user()
        return json_payload(claim=rebirth_repo().claim_daily_reward(user["id"]))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


# === Crafting (pó) — desmanchar duplicata -> pó; criar carta <- pó (Comum/Incomum) ===
@app.post("/api/rebirth/craft/disenchant")
def api_rebirth_craft_disenchant():
    try:
        user = require_user()
        card_id = (request.get_json(silent=True) or {}).get("card_id")
        if not card_id:
            return json_error("card_id é obrigatório.", "missing_card_id", status=400)
        return json_payload(craft=rebirth_repo().disenchant_card(user["id"], str(card_id)))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.post("/api/rebirth/craft/create")
def api_rebirth_craft_create():
    try:
        user = require_user()
        card_id = (request.get_json(silent=True) or {}).get("card_id")
        if not card_id:
            return json_error("card_id é obrigatório.", "missing_card_id", status=400)
        return json_payload(craft=rebirth_repo().craft_card(user["id"], str(card_id)))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.get("/api/rebirth/desktop")
def api_rebirth_desktop():
    return json_payload(desktop=desktop_payload())


@app.get("/api/rebirth/onboarding")
def api_rebirth_onboarding():
    user = current_user()
    progress = rebirth_repo().progression(user["id"]) if user else None
    return json_payload(onboarding=onboarding_payload(account=account_payload(user), progression=progress))


@app.get("/api/rebirth/first-session")
def api_rebirth_first_session():
    user = current_user()
    progress = rebirth_repo().progression(user["id"]) if user else {}
    account = account_payload(user)
    return json_payload(
        first_session=first_session_plan(
            account=account,
            progression=progress or {},
            release_version=app.config["REBIRTH_RELEASE_VERSION"],
        )
    )


@app.post("/api/rebirth/onboarding/complete")
def api_rebirth_onboarding_complete():
    try:
        payload = request_json(required=True)
        user = require_user()
        step = payload.get("step", 4)
        repo = rebirth_repo()
        tutorial = repo.complete_tutorial_step(user["id"], step)
        repo.record_telemetry_event(
            "tutorial_step_completed",
            {
                "step": tutorial.get("step"),
                "already_claimed": bool(tutorial.get("already_claimed")),
                "rebirth_release_version": app.config["REBIRTH_RELEASE_VERSION"],
            },
            user_id=user["id"],
        )
        return json_payload(tutorial=tutorial)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/balance/simulate")
def api_rebirth_balance_simulate():
    try:
        require_internal_lab_access()
        return json_payload(balance=simulate_balance(matches=internal_balance_matches()))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/balance/telemetry")
def api_rebirth_balance_telemetry():
    try:
        require_internal_lab_access()
        return json_payload(
            live_balance=live_balance_payload(
                rebirth_repo(),
                release_version=app.config["REBIRTH_RELEASE_VERSION"],
            )
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/telemetry")
def api_rebirth_telemetry():
    try:
        payload = request_json(required=True)
        event_type = str(payload.get("event_type") or "").strip().lower()
        if event_type not in REBIRTH_CLIENT_TELEMETRY_EVENTS:
            raise RebirthError("Evento de telemetria não permitido.", "invalid_telemetry_event")
        user = current_user()
        if event_type == "match_abandoned":
            match = get_match(payload.get("match_id"), user=user)
            ensure_match_access(match, user=user)
            record_match_telemetry(rebirth_repo() if user else None, user, match, "match_abandoned", client_reason=payload.get("reason"))
        else:
            rebirth_repo().record_telemetry_event(
                event_type,
                build_client_telemetry_payload(
                    event_type,
                    payload,
                    user=user,
                    release_version=app.config["REBIRTH_RELEASE_VERSION"],
                ),
                user_id=(user or {}).get("id"),
            )
        return json_payload(recorded=True)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/telemetry/beacon")
def api_rebirth_telemetry_beacon():
    # Dedicated endpoint for navigator.sendBeacon (pagehide path). sendBeacon
    # cannot attach custom headers, so CSRF travels in the request body and
    # is verified explicitly here. Payload is intentionally narrow:
    # match_abandoned only, no client-supplied user identifiers.
    if app.config.get("REBIRTH_REQUIRE_CSRF", True):
        body_csrf = (request.get_json(silent=True) or {}).get("csrf") if request.is_json else None
        if not body_csrf:
            try:
                body_csrf = request.form.get("csrf") if request.form else None
            except Exception:
                body_csrf = None
        expected = session.get("rebirth_csrf_token")
        if not expected or not body_csrf or not secrets.compare_digest(str(expected), str(body_csrf)):
            return json_error("O token CSRF do Rebirth é obrigatório.", "csrf_required", status=403)
    try:
        payload = request.get_json(silent=True) or {}
        if payload.get("event_type") != "match_abandoned":
            raise RebirthError("Evento de telemetria não permitido.", "invalid_telemetry_event")
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        ensure_match_access(match, user=user)
        record_match_telemetry(
            rebirth_repo() if user else None,
            user,
            match,
            "match_abandoned",
            client_reason=payload.get("reason") or "pagehide_beacon",
            transport="sendBeacon",
        )
        return json_payload(recorded=True)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/release")
def api_rebirth_release():
    repo = rebirth_repo()
    since = release_since_arg()
    gates = external_gate_payload(app.config, require_external_evidence=True)
    live_balance = live_balance_payload(repo, since=since, release_version=app.config["REBIRTH_RELEASE_VERSION"])
    public_gate = public_beta_gate_payload(
        repo,
        since=since,
        release_version=app.config["REBIRTH_RELEASE_VERSION"],
        live_balance=live_balance,
    )
    phase_report_audit = audit_phase_reports()
    return json_payload(
        release=release_payload(
            gates=gates,
            dashboard=beta_dashboard_payload(repo, since=since),
            content_report=content_pipeline_report(),
            live_balance=live_balance,
            public_beta_gate=public_gate,
            phase_report_audit=phase_report_audit,
            release_readiness=release_readiness_report(
                gates,
                public_gate,
                phase_report_audit=phase_report_audit,
            ),
        )
    )


@app.get("/api/rebirth/content/validate")
def api_rebirth_content_validate():
    try:
        require_internal_lab_access()
        return json_payload(content_pipeline=content_pipeline_report())
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/async/share/<match_id>")
def api_rebirth_async_share(match_id):
    try:
        user = require_user()
        match = rebirth_repo().runtime_match_state(user["id"], match_id)
        ensure_match_access(match, user=user)
        if not match.get("is_finished"):
            raise RebirthError("Finalize a partida antes de gerar um replay competitivo.", "match_not_finished", status=409)
        return json_payload(async_competition=async_competition_payload(match))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/async/ghosts")
def api_rebirth_async_ghosts():
    try:
        user = require_user()
        repo = rebirth_repo()
        states = []
        for item in repo.match_history(user["id"], limit=6):
            if item.get("status") != "finished":
                continue
            try:
                states.append(repo.runtime_match_state(user["id"], item["match_id"]))
            except RebirthPersistenceError:
                continue
        return json_payload(async_competition=async_history_payload(states))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/support/export")
def api_rebirth_support_export():
    try:
        user = require_user()
        return json_payload(export=rebirth_repo().support_export(user["id"]))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.post("/api/rebirth/support/reset")
def api_rebirth_support_reset():
    try:
        payload = request_json(required=True)
        user = require_user()
        if payload.get("confirm") != "RESET REBIRTH":
            raise RebirthPersistenceError("Digite RESET REBIRTH para reiniciar esta conta.", "reset_confirmation_required", 409)
        return json_payload(export=rebirth_repo().reset_account(user["id"]))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/support/delete-account")
def api_rebirth_support_delete_account():
    try:
        payload = request_json(required=True)
        user = require_user()
        if payload.get("confirm") != "DELETE REBIRTH":
            raise RebirthPersistenceError("Digite DELETE REBIRTH para excluir esta conta.", "delete_confirmation_required", 409)
        deletion = rebirth_repo().delete_account(user["id"])
        session.clear()
        csrf = csrf_token()
        return json_payload(deletion=deletion, account=account_payload(None), csrf=csrf)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/support/feedback")
def api_rebirth_support_feedback():
    try:
        payload = request_json(required=True)
        user = current_user()
        message = str(payload.get("message") or "").strip()
        if len(message) < 8:
            raise RebirthError("Descreva o feedback com pelo menos 8 caracteres.", "feedback_too_short")
        category = str(payload.get("category") or "general").strip().lower()[:40] or "general"
        severity = str(payload.get("severity") or "normal").strip().lower()[:24] or "normal"
        match_id = str(payload.get("match_id") or "").strip()[:120] or None
        if match_id and user:
            # Partidas recém-iniciadas vivem só no MATCH_STORE até o primeiro
            # comando (fix das partidas-fantasma); o feedback aceita as duas
            # fontes antes de descartar o vínculo.
            try:
                live = MATCH_STORE.get(match_id)
                ensure_match_access(live, user=user)
            except RebirthError:
                try:
                    rebirth_repo().runtime_match_state(user["id"], match_id)
                except RebirthPersistenceError:
                    match_id = None
        feedback = {
            "category": category,
            "severity": severity,
            "message": message[:2000],
            "match_id": match_id,
            "account_authenticated": bool(user),
            "cohort": "account" if user else "guest",
            "user_id": user["id"] if user else None,
            "session_active_match_id": session.get("rebirth_active_match_id"),
            "rebirth_release_version": app.config["REBIRTH_RELEASE_VERSION"],
            "surface": str(payload.get("surface") or "support").strip()[:80],
        }
        feedback = {key: value for key, value in feedback.items() if value is not None}
        rebirth_repo().record_telemetry_event("feedback_submitted", feedback, user_id=(user or {}).get("id"))
        return json_payload(recorded=True, feedback={"category": category, "severity": severity, "match_id": match_id})
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/admin/grant")
def api_rebirth_admin_grant():
    try:
        actor = require_admin_token()
        payload = request_json(required=True)
        user_id = int(payload.get("user_id") or 0)
        if user_id <= 0:
            raise RebirthPersistenceError("Informe user_id.", "invalid_admin_grant", 400)
        return json_payload(
            export=rebirth_repo().admin_grant(
                actor,
                user_id,
                resource=payload.get("resource"),
                amount=payload.get("amount", 1),
                card_id=payload.get("card_id"),
                reason=payload.get("reason", "admin_grant"),
                idempotency_key=payload.get("idempotency_key"),
            )
        )
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except (TypeError, ValueError) as error:
        return json_error(str(error), "invalid_admin_grant", status=400)


@app.route("/arena")
@app.route("/training")
@app.route("/training-legacy")
@app.route("/collection")
@app.route("/deck-builder")
@app.route("/shop")
@app.route("/ranking")
@app.route("/leaderboard")
@app.route("/missions")
@app.route("/progression")
@app.route("/profile")
@app.route("/campaign")
@app.route("/tutorial")
@app.route("/how-to-play")
@app.route("/inventory")
@app.route("/economy")
@app.route("/match-history")
def legacy_product_redirect():
    return redirect("/rebirth", code=302)


@app.route("/api/ascension/<path:_unused>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.route("/api/beta/<path:_unused>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.route("/api/booster/<path:_unused>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def legacy_api_disabled(_unused):
    return json_error(
        "Legacy Ambitionz systems are retired from the active product. Use /api/rebirth/start.",
        "legacy_disabled",
        status=410,
    )


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return json_error("Endpoint não encontrado.", "not_found", status=404)
    return redirect("/rebirth", code=302)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG_MODE") == "true")
