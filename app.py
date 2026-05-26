import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, make_response, redirect, render_template, request, send_from_directory, session

from services.rebirth_contracts import RebirthError
from services.rebirth_balance import simulate_balance
from services.rebirth_dispatcher import (
    DeclareAttackCommand,
    EndTurnCommand,
    EvolveDuplicateCommand,
    SummonCardCommand,
    dispatch_command,
)
from services.rebirth_engine import start_match
from services.rebirth_match_store import MATCH_STORE
from services.rebirth_persistence import (
    RebirthPersistenceError,
    RebirthRepository,
)
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


app = Flask(__name__)
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
app.config["REBIRTH_POSTGRES_SERIALIZATION_ATTEMPTS"] = min(3, max(1, int(os.environ.get("REBIRTH_POSTGRES_SERIALIZATION_ATTEMPTS", "3"))))
app.config["REBIRTH_POSTGRES_RETRY_BACKOFF_SECONDS"] = max(0.0, float(os.environ.get("REBIRTH_POSTGRES_RETRY_BACKOFF_SECONDS", "0.02")))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE") == "true"

REBIRTH_MATCHES = MATCH_STORE
AUTH_RATE_LIMITS = {}
AUTH_RATE_LIMIT_LOCK = threading.Lock()
_SCHEMA_BOOTSTRAP_LOCK = threading.Lock()
_SCHEMA_BOOTSTRAP_DONE = False


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
            engine = make_engine(normalized)
            try:
                status = validate_schema(engine)
            finally:
                engine.dispose()
            current_version = int(status.get("version", 0) or 0)
            if current_version >= SCHEMA_VERSION and not status.get("missing_tables"):
                app.logger.info("rebirth.schema already at v%s", current_version)
                _SCHEMA_BOOTSTRAP_DONE = True
                return
            app.logger.info(
                "rebirth.schema bootstrap upgrading: v%s -> v%s (missing=%s)",
                current_version,
                SCHEMA_VERSION,
                status.get("missing_tables"),
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
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https://images.unsplash.com",
        "font-src 'self' data:",
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
    if not after:
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
    outcome_label = {"Victory": "Vitória", "Defeat": "Derrota", "Clash": "Clash"}.get(outcome, outcome)
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


def rebirth_repo():
    database_url = app.config.get("REBIRTH_DATABASE_URL")
    retry_options = {
        "serialization_retry_attempts": app.config["REBIRTH_POSTGRES_SERIALIZATION_ATTEMPTS"],
        "serialization_retry_backoff_seconds": app.config["REBIRTH_POSTGRES_RETRY_BACKOFF_SECONDS"],
    }
    if database_url:
        return RebirthRepository(database_url=database_url, **retry_options)
    if app.config.get("TESTING") or app.config.get("REBIRTH_ALLOW_SQLITE_TESTING"):
        return RebirthRepository(app.config["REBIRTH_DB_PATH"], **retry_options)
    raise RebirthPersistenceError(
        "REBIRTH_DATABASE_URL e obrigatoria fora do ambiente de testes.",
        "database_not_configured",
        status=503,
    )


def guest_wallet_payload():
    return {"GOLD": 0, "COINZ": 0, "ledger_source": "wallet_ledger", "guest": True}


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


def current_user():
    token = session.get("rebirth_session_token")
    if not token:
        return None
    return rebirth_repo().user_for_session(token)


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
        "level": level,
        "xp": xp,
        "next_level_xp": next_level,
        "xp_percent": xp_percent,
        "gold": gold,
        "coinz": coinz,
        "wallet": {"GOLD": gold, "COINZ": coinz, "ledger_source": wallet.get("ledger_source", "wallet_ledger")},
    }


def require_user():
    user = current_user()
    if not user:
        raise RebirthPersistenceError("Entre para usar a coleção persistida do Rebirth.", "auth_required", status=401)
    return user


def enforce_auth_rate_limit(action, identifier="anonymous"):
    limit = int(app.config.get("REBIRTH_AUTH_RATE_LIMIT", 20))
    window_seconds = int(app.config.get("REBIRTH_AUTH_RATE_LIMIT_SECONDS", 300))
    if limit <= 0 or window_seconds <= 0:
        return

    now = time.time()
    key = f"{action}:{request.remote_addr or 'local'}:{str(identifier or 'anonymous').strip().lower()}"
    blocked = False
    with AUTH_RATE_LIMIT_LOCK:
        attempts = [stamp for stamp in AUTH_RATE_LIMITS.get(key, []) if now - stamp < window_seconds]
        if len(attempts) >= limit:
            blocked = True
        else:
            attempts.append(now)
        AUTH_RATE_LIMITS[key] = attempts
    if blocked:
        raise RebirthPersistenceError("Muitas tentativas de acesso. Tente novamente mais tarde.", "rate_limited", status=429)


def get_match(match_id, user=None):
    try:
        return MATCH_STORE.get(match_id)
    except RebirthError as error:
        if error.code != "missing_match" or not user:
            raise
        restored = rebirth_repo().runtime_match_state(user["id"], match_id)
        return MATCH_STORE.save(restored)


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


def start_memory_rebirth_match(payload):
    player_card_ids = DEFAULT_LOADOUT if payload.get("tutorial") else None
    bot_profile_id = "aggressive" if payload.get("tutorial") else None
    requested_seed = payload.get("seed")
    if payload.get("tutorial") and requested_seed is None:
        requested_seed = "guided-first-match"
    match = start_match(
        seed=requested_seed,
        player_card_ids=player_card_ids,
        player_name="Você",
        bot_profile_id=bot_profile_id,
        runtime_mode="singleplayer",
        apply_reducers_inline=False,
    )
    match = MATCH_STORE.save(match)
    state = public_state(match)
    return json_success(state, match.get("result"), match_id=match["match_id"])


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


def reject_authoritative_combat_fields(payload):
    pending = [payload]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if AUTHORITATIVE_COMBAT_FIELDS.intersection(value):
                raise RebirthError(
                    "O estado de acao e controlado exclusivamente pelo servidor.",
                    "authoritative_state_violation",
                    status=400,
                )
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)


@app.context_processor
def inject_rebirth_security():
    user = current_user()
    return {
        "csrf_token": csrf_token,
        "rebirth_navbar": rebirth_navbar_payload(user),
    }


@app.before_request
def protect_rebirth_mutations():
    if not app.config.get("REBIRTH_REQUIRE_CSRF", True):
        return None
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if not request.path.startswith("/api/rebirth/"):
        return None

    expected = session.get("rebirth_csrf_token")
    supplied = request.headers.get("X-Rebirth-CSRF")
    if not expected or not supplied or not secrets.compare_digest(str(expected), str(supplied)):
        return json_error("O token CSRF do Rebirth é obrigatório.", "csrf_required", status=403)
    return None


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


@app.get("/rebirth")
def rebirth():
    user = current_user()
    progress = rebirth_repo().progression(user["id"]) if user else None
    return render_template("rebirth.html", account=account_payload(user), progression=progress or {})


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
    return render_template("rebirth_product.html", page=balance_payload(simulation=simulate_balance(matches=24)))


@app.get("/rebirth/release")
def rebirth_release():
    return render_template("rebirth_product.html", page=release_payload())


@app.get("/rebirth/support")
def rebirth_support():
    user = current_user()
    return render_template("rebirth_product.html", page=support_payload(account=account_payload(user)))


@app.get("/rebirth/lab")
def rebirth_lab():
    return render_template("rebirth_product.html", page=lab_payload())


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
        repo = rebirth_repo()
        player_card_ids = None
        player_name = "Você"
        bot_profile_id = None
        progress = None
        if user:
            progress = repo.progression(user["id"])
            player_card_ids = repo.loadout_card_ids(user["id"])
            player_name = user["username"]
            if payload.get("tutorial"):
                player_card_ids = DEFAULT_LOADOUT
                bot_profile_id = "aggressive"
            elif progress and int(progress.get("clashes", 0) or 0) < 3:
                bot_profile_id = "aggressive"
        requested_seed = payload.get("seed")
        if payload.get("tutorial") and requested_seed is None:
            requested_seed = "guided-first-match"
        engine_seed = f"user:{user['id']}:{requested_seed}" if user and requested_seed is not None else requested_seed
        match = start_match(
            seed=engine_seed,
            player_card_ids=player_card_ids,
            player_name=player_name,
            bot_profile_id=bot_profile_id,
            runtime_mode="singleplayer",
            apply_reducers_inline=False,
        )
        if user:
            match["owner_user_id"] = user["id"]
            match["seed"] = str(requested_seed or "")
        match = MATCH_STORE.save(match)
        if user:
            repo.upsert_match_history(user["id"], match)
        state = public_state(match)
        return json_success(state, match.get("result"), match_id=match["match_id"])
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/play-card")
def api_rebirth_play_card():
    try:
        payload = request_json(required=True)
        reject_authoritative_combat_fields(payload)
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        repo = rebirth_repo()
        ensure_match_access(match, user=user)
        if payload.get("attacker_instance_id"):
            dispatch_command(
                match,
                DeclareAttackCommand(
                    attacker_instance_id=payload.get("attacker_instance_id"),
                    target_instance_id=payload.get("target_instance_id"),
                ),
            )
        else:
            dispatch_command(
                match,
                SummonCardCommand(
                    card_instance_id=payload.get("card_instance_id"),
                    card_id=payload.get("card_id"),
                    field_slot=payload.get("field_slot", payload.get("slot")),
                ),
            )
        state = public_state(match)
        progress = None
        reward = match_reward_payload(None, None, state)
        if user:
            if state.get("last_clash") and state.get("phase") in {"result", "finished"}:
                before = repo.progression(user["id"])
                progress = repo.record_clash_result(user["id"], state)
                reward = clash_reward_payload_from_progress(before, progress, state)
            repo.upsert_match_history(user["id"], match)
        return json_success(state, match.get("result"), progression=progress, match_reward=reward)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/attack")
def api_rebirth_attack():
    try:
        payload = request_json(required=True)
        reject_authoritative_combat_fields(payload)
        user = current_user()
        match = get_match(payload.get("match_id"), user=user)
        repo = rebirth_repo()
        ensure_match_access(match, user=user)
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
        if user:
            if state.get("last_clash") and state.get("phase") in {"result", "finished"}:
                before = repo.progression(user["id"])
                progress = repo.record_clash_result(user["id"], state)
                reward = clash_reward_payload_from_progress(before, progress, state)
            repo.upsert_match_history(user["id"], match)
        return json_success(state, match.get("result"), progression=progress, match_reward=reward)
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
        evolved = dispatch_command(match, EvolveDuplicateCommand(card_id=payload.get("card_id")))
        persist_match_if_owned(rebirth_repo(), user, match)
        return json_success(public_state(match), match.get("result"), evolved=evolved)
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
        dispatch_command(match, EndTurnCommand(turn=match.get("turn")))
        persist_match_if_owned(rebirth_repo(), user, match)
        return json_success(public_state(match), match.get("result"))
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
    return json_payload(account=account_payload(user), wallet=wallet, **csrf_payload())


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


@app.post("/api/rebirth/auth/register")
def api_rebirth_auth_register():
    try:
        payload = request_json(required=True)
        enforce_auth_rate_limit("register", payload.get("email") or payload.get("username"))
        user = rebirth_repo().create_user(
            payload.get("username"),
            payload.get("email"),
            payload.get("password"),
        )
        token = establish_rebirth_session(user)
        return json_payload(account=account_payload(user), csrf=token, **auth_sync_payload(user))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


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
        return json_payload(
            booster=booster,
            collection=collection_payload(
                account=account_payload(user),
                collection_counts=repo.collection_counts(user["id"]),
                loadout_card_ids=repo.loadout_card_ids(user["id"]),
            ),
            progression=repo.progression(user["id"]),
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
        return json_payload(history=rebirth_repo().match_history(user["id"], limit=request.args.get("limit", 12)))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.get("/api/rebirth/match-history/<match_id>/events")
def api_rebirth_match_events(match_id):
    try:
        user = require_user()
        return json_payload(events=rebirth_repo().match_events(user["id"], match_id, limit=request.args.get("limit", 50)))
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


@app.get("/api/rebirth/economy-ledger")
def api_rebirth_economy_ledger():
    try:
        user = require_user()
        return json_payload(ledger=rebirth_repo().economy_ledger(user["id"], limit=request.args.get("limit", 30)))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)


@app.post("/api/rebirth/progression/claim-daily")
def api_rebirth_progression_claim_daily():
    try:
        user = require_user()
        return json_payload(claim=rebirth_repo().claim_daily_reward(user["id"]))
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


@app.post("/api/rebirth/onboarding/complete")
def api_rebirth_onboarding_complete():
    try:
        payload = request_json(required=True)
        user = require_user()
        return json_payload(tutorial=rebirth_repo().complete_tutorial_step(user["id"], payload.get("step", 4)))
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.get("/api/rebirth/balance/simulate")
def api_rebirth_balance_simulate():
    return json_payload(balance=simulate_balance(matches=request.args.get("matches", 40)))


@app.get("/api/rebirth/release")
def api_rebirth_release():
    return json_payload(release=release_payload())


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
