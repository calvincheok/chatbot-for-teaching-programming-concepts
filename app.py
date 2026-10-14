"""Flask backend for the FYP1 teaching engine prototype.

Serves the chat page at / and this JSON API:
    GET  /api/concepts                      topics and which are enabled
    POST /api/sessions                      start a session {concept}
    GET  /api/sessions                      this learner's sessions
    GET  /api/sessions/<id>                 one session's messages and state
    POST /api/sessions/<id>/messages        send a learner message {text}

Every POST carries a request_id. If the same request arrives twice (a double
click or a network retry), the first result is returned instead of calling
the AI again.

Run:  python app.py   (http://127.0.0.1:5050)
"""

from __future__ import annotations

import json
import os
import secrets
import threading
from functools import wraps

from flask import Flask, g, jsonify, render_template, request

from teaching import storage
from teaching.concepts import CONCEPTS
from teaching.engine import EngineError, TeachingEngine
from teaching.providers import get_provider

COOKIE = "fyp_learner"
HERE = os.path.dirname(os.path.abspath(__file__))


def create_app(db_path: str | None = None, provider=None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
    path = db_path or os.environ.get("FYP_DB", os.path.join(HERE, "data", "teaching.db"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    engine = TeachingEngine(path, provider or get_provider())
    in_flight: set[str] = set()
    in_flight_lock = threading.Lock()

    # No accounts in this prototype: each browser gets a random learner id cookie.
    @app.before_request
    def identify():
        token = request.cookies.get(COOKIE, "")
        g.new_cookie = None
        if len(token) != 32 or not token.isalnum():
            token = secrets.token_hex(16)
            g.new_cookie = token
        g.learner = token

    @app.after_request
    def remember(response):
        if g.get("new_cookie"):
            response.set_cookie(COOKIE, g.new_cookie, max_age=60 * 60 * 24 * 365, httponly=True, samesite="Lax")
        return response

    def api(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if request.method != "POST":
                try:
                    return jsonify(fn(*args, **kwargs))
                except EngineError as exc:
                    return jsonify(error=exc.message, retryable=exc.retryable), exc.status
            # Simple protection against requests made by other websites.
            if request.headers.get("X-Requested-With") != "fyp-chat":
                return jsonify(error="Request blocked."), 403
            body = request.get_json(silent=True) or {}
            rid = str(body.get("request_id") or "")
            if not 8 <= len(rid) <= 64:
                return jsonify(error="Missing request id."), 400
            with engine._db() as conn:
                seen = conn.execute("SELECT response FROM requests WHERE request_id = ? AND learner_id = ?", (rid, g.learner)).fetchone()
            if seen:
                return app.response_class(seen["response"], mimetype="application/json")
            with in_flight_lock:
                if rid in in_flight:
                    return jsonify(error="Still working on this message.", retryable=True), 409
                in_flight.add(rid)
            try:
                g.body = body
                result = fn(*args, **kwargs)
            except EngineError as exc:
                return jsonify(error=exc.message, retryable=exc.retryable), exc.status
            finally:
                with in_flight_lock:
                    in_flight.discard(rid)
            payload = json.dumps(result, ensure_ascii=False)
            with engine._db() as conn:
                conn.execute("INSERT OR IGNORE INTO requests (request_id, learner_id, response, created_at) VALUES (?, ?, ?, ?)",
                             (rid, g.learner, payload, storage.now()))
            return app.response_class(payload, mimetype="application/json")
        return wrapper

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/concepts")
    @api
    def concepts():
        return [{"id": k, "title": v["title"], "subtopics": v["subtopics"], "enabled": v["enabled"]} for k, v in CONCEPTS.items()]

    @app.post("/api/sessions")
    @api
    def start_session():
        return engine.start(g.learner, str(g.body.get("concept", "variables")))

    @app.get("/api/sessions")
    @api
    def list_sessions():
        return engine.sessions(g.learner)

    @app.get("/api/sessions/<session_id>")
    @api
    def get_session(session_id):
        return engine.state(session_id, g.learner)

    @app.post("/api/sessions/<session_id>/messages")
    @api
    def send_message(session_id):
        return engine.send(session_id, g.learner, str(g.body.get("text", "")))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5050)))
