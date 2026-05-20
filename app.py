import os
import secrets
import threading
import time

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session

from services.rebirth_contracts import RebirthError
from services.rebirth_balance import simulate_balance
from services.rebirth_engine import (
    evolve_duplicate,
    next_turn,
    play_card,
    start_match,
)
from services.rebirth_match_store import MATCH_STORE
from services.rebirth_persistence import RebirthPersistenceError, RebirthRepository
from services.rebirth_product import (
    account_payload,
    auth_plan_payload,
    balance_payload,
    collection_payload,
    desktop_payload,
    onboarding_payload,
    open_booster,
    profile_payload,
    product_shell_payload,
    progression_payload,
    release_payload,
    shop_payload,
    validate_loadout,
)
from services.rebirth_serializers import public_state


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ambitionz-rebirth-dev")
app.config["REBIRTH_DB_PATH"] = os.environ.get(
    "REBIRTH_DB_PATH",
    os.path.join(app.instance_path, "rebirth.db"),
)
app.config["REBIRTH_REQUIRE_CSRF"] = os.environ.get("REBIRTH_REQUIRE_CSRF", "true") == "true"
app.config["REBIRTH_AUTH_RATE_LIMIT"] = int(os.environ.get("REBIRTH_AUTH_RATE_LIMIT", "20"))
app.config["REBIRTH_AUTH_RATE_LIMIT_SECONDS"] = int(os.environ.get("REBIRTH_AUTH_RATE_LIMIT_SECONDS", "300"))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE") == "true"

REBIRTH_MATCHES = MATCH_STORE
AUTH_RATE_LIMITS = {}
AUTH_RATE_LIMIT_LOCK = threading.Lock()

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
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


def csrf_token():
    token = session.get("rebirth_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["rebirth_csrf_token"] = token
    return token


def establish_rebirth_session(user):
    session.clear()
    session["rebirth_user_id"] = user["id"]
    session["rebirth_csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True
    return session["rebirth_csrf_token"]


def clear_rebirth_session():
    session.clear()
    return csrf_token()


def csrf_payload():
    return {"csrf": csrf_token()}


def rebirth_repo():
    return RebirthRepository(app.config["REBIRTH_DB_PATH"])


def current_user():
    user_id = session.get("rebirth_user_id")
    if not user_id:
        return None
    return rebirth_repo().get_user(user_id)


def current_account():
    return account_payload(current_user())


def require_user():
    user = current_user()
    if not user:
        raise RebirthPersistenceError("Sign in to use persisted Rebirth ownership.", "auth_required", status=401)
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
        raise RebirthPersistenceError("Too many auth attempts. Try again later.", "rate_limited", status=429)


def get_match(match_id):
    return MATCH_STORE.get(match_id)


def request_json(required=False):
    payload = request.get_json(silent=True)
    if payload is None:
        if required and request.data:
            raise RebirthError("Request body must be valid JSON.", "malformed_request")
        return {}
    if not isinstance(payload, dict):
        raise RebirthError("Request body must be a JSON object.", "malformed_request")
    return payload


@app.context_processor
def inject_rebirth_security():
    return {"csrf_token": csrf_token}


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
        return json_error("Rebirth CSRF token is required.", "csrf_required", status=403)
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
    return render_template("rebirth.html")


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
    history = rebirth_repo().booster_history(user["id"]) if user else []
    return render_template("rebirth_product.html", page=shop_payload(account=account_payload(user), booster_history=history))


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


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "status": "healthy",
            "product": "Ambitionz Rebirth",
            "architecture": "Ambitionz Rebirth",
        }
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
        user = current_user()
        player_card_ids = None
        player_name = "You"
        if user:
            player_card_ids = rebirth_repo().loadout_card_ids(user["id"])
            player_name = user["username"]
        match = MATCH_STORE.save(
            start_match(
                seed=payload.get("seed"),
                player_card_ids=player_card_ids,
                player_name=player_name,
            )
        )
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
        match = get_match(payload.get("match_id"))
        play_card(
            match,
            card_instance_id=payload.get("card_instance_id"),
            card_id=payload.get("card_id"),
        )
        state = public_state(match)
        user = current_user()
        progress = rebirth_repo().record_clash_result(user["id"], state) if user else None
        return json_success(state, match.get("result"), progression=progress)
    except RebirthPersistenceError as error:
        return json_from_persistence_error(error)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/evolve")
def api_rebirth_evolve():
    try:
        payload = request_json(required=True)
        match = get_match(payload.get("match_id"))
        evolved = evolve_duplicate(match, payload.get("card_id"))
        return json_success(public_state(match), match.get("result"), evolved=evolved)
    except RebirthError as error:
        return json_from_rebirth_error(error)


@app.post("/api/rebirth/next-turn")
def api_rebirth_next_turn():
    try:
        payload = request_json(required=True)
        match = get_match(payload.get("match_id"))
        next_turn(match)
        return json_success(public_state(match), match.get("result"))
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
    return json_payload(account=current_account(), **csrf_payload())


@app.get("/api/rebirth/csrf")
def api_rebirth_csrf():
    return json_payload(**csrf_payload())


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
        return json_payload(account=account_payload(user), csrf=token)
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
        return json_payload(account=account_payload(user), csrf=token)
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
        return json_payload(account=account_payload(user), message="Password updated.")
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
    history = rebirth_repo().booster_history(user["id"]) if user else []
    return json_payload(shop=shop_payload(account=account_payload(user), booster_history=history))


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
        return json_error("Endpoint not found.", "not_found", status=404)
    return redirect("/rebirth", code=302)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG_MODE") == "true")
