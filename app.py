import os

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory

from services.rebirth_engine import (
    RebirthError,
    evolve_duplicate,
    next_turn,
    play_card,
    start_match,
)
from services.rebirth_state import public_state


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ambitionz-rebirth-dev")

REBIRTH_MATCHES = {}


def json_error(message, code="rebirth_error", status=400):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


def get_match(match_id):
    match = REBIRTH_MATCHES.get(str(match_id or ""))
    if not match:
        raise RebirthError("Match not found.", "match_not_found")
    return match


def request_json():
    return request.get_json(silent=True) or {}


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
    payload = request_json()
    match = start_match(seed=payload.get("seed"))
    REBIRTH_MATCHES[match["match_id"]] = match
    return jsonify({"ok": True, "match_id": match["match_id"], "state": public_state(match)})


@app.post("/api/rebirth/play-card")
def api_rebirth_play_card():
    payload = request_json()
    try:
        match = get_match(payload.get("match_id"))
        play_card(
            match,
            card_instance_id=payload.get("card_instance_id"),
            card_id=payload.get("card_id"),
        )
        return jsonify({"ok": True, "state": public_state(match)})
    except RebirthError as error:
        return json_error(str(error), error.code)


@app.post("/api/rebirth/evolve")
def api_rebirth_evolve():
    payload = request_json()
    try:
        match = get_match(payload.get("match_id"))
        evolved = evolve_duplicate(match, payload.get("card_id"))
        return jsonify({"ok": True, "evolved": evolved, "state": public_state(match)})
    except RebirthError as error:
        return json_error(str(error), error.code)


@app.post("/api/rebirth/next-turn")
def api_rebirth_next_turn():
    payload = request_json()
    try:
        match = get_match(payload.get("match_id"))
        next_turn(match)
        return jsonify({"ok": True, "state": public_state(match)})
    except RebirthError as error:
        return json_error(str(error), error.code)


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
