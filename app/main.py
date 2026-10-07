import os
import secrets
import sqlite3
import string
import time

from flask import Flask, g, jsonify, redirect, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

ALPHABET = string.ascii_letters + string.digits

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "endpoint", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["endpoint"])


def init_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS links (code TEXT PRIMARY KEY, url TEXT NOT NULL)")


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.getenv("DB_PATH", "/tmp/shortener.db")
    init_db(app.config["DB_PATH"])

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.before_request
    def start_timer():
        g.start = time.perf_counter()

    @app.after_request
    def record_metrics(response):
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        LATENCY.labels(endpoint).observe(time.perf_counter() - g.start)
        REQUESTS.labels(request.method, endpoint, response.status_code).inc()
        return response

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/metrics")
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    @app.post("/api/shorten")
    def shorten():
        data = request.get_json(silent=True) or {}
        url = data.get("url", "")
        if not url.startswith(("http://", "https://")):
            return jsonify(error="url must start with http:// or https://"), 400
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        db = get_db()
        db.execute("INSERT INTO links (code, url) VALUES (?, ?)", (code, url))
        db.commit()
        return jsonify(code=code, short_url=f"{request.host_url}{code}"), 201

    @app.get("/<code>")
    def follow(code):
        row = get_db().execute("SELECT url FROM links WHERE code = ?", (code,)).fetchone()
        if row is None:
            return jsonify(error="not found"), 404
        return redirect(row[0], code=302)

    return app

