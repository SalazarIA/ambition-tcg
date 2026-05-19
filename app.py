import os

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory

from services.rebirth_contracts import RebirthError
from services.rebirth_engine import (
    evolve_duplicate,
    next_turn,
    play_card,
    start_match,
)
from services.rebirth_match_store import MATCH_STORE
from services.rebirth_serializers import public_state


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ambitionz-rebirth-dev")

REBIRTH_MATCHES = MATCH_STORE.raw()


def json_error(message, code="malformed_request", status=400):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


def json_success(state, result=None, **extra):
    payload = {"ok": True, "state": state, "result": result}
    payload.update(extra)
    return jsonify(payload)


def json_from_rebirth_error(error):
    return json_error(str(error), error.code, status=getattr(error, "status", 400))


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


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/rebirth")
def rebirth():
    return render_template("rebirth.html")


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
    return response


@app.get("/manifest.webmanifest")
def webmanifest():
    return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")


@app.post("/api/rebirth/start")
def api_rebirth_start():
    try:
        payload = request_json(required=False)
        match = MATCH_STORE.save(start_match(seed=payload.get("seed")))
        state = public_state(match)
        return json_success(state, match.get("result"), match_id=match["match_id"])
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
        return json_success(public_state(match), match.get("result"))
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
