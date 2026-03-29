"""
Elasticsearch logging for the household-budget Flask app.

Emits four event types to ES index  budget-logs-YYYY.MM.DD:
  - http_request   : every incoming API call + response time & status
  - app_error      : unhandled exceptions (with traceback)
  - slow_query     : SQLite queries that exceed SLOW_QUERY_MS
  - lifecycle      : app startup / shutdown
"""

import json
import logging
import os
import socket
import ssl
import time
import traceback
import urllib.request
import urllib.error
from base64 import b64encode
from datetime import datetime, timezone
from threading import Thread
from queue import Queue, Full


# ── Configuration ─────────────────────────────────────────────────────────────
ES_HOST        = os.getenv("ES_HOST",        "http://localhost:9200")
ES_USER        = os.getenv("ES_USER",        "elastic")
ES_PASSWORD    = os.getenv("ES_PASSWORD",    "changeme")
ES_INDEX_PREFIX= os.getenv("ES_INDEX",       "budget-logs")
ES_VERIFY_SSL  = os.getenv("ES_VERIFY_SSL",  "1") == "1"
SLOW_QUERY_MS  = int(os.getenv("SLOW_QUERY_MS", "100"))
LOG_LEVEL      = os.getenv("LOG_LEVEL",      "INFO")
QUEUE_MAX      = 1000
HOSTNAME       = socket.gethostname()


# ── Internal async shipper ────────────────────────────────────────────────────
_queue: Queue = Queue(maxsize=QUEUE_MAX)
_auth_header  = b64encode(f"{ES_USER}:{ES_PASSWORD}".encode()).decode()

_fallback_log = logging.getLogger("es_fallback")
_fallback_log.setLevel(logging.WARNING)
_fallback_log.propagate = False
_fh = logging.FileHandler(os.getenv("ES_FALLBACK_LOG", "es_fallback.log"))
_fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
_fallback_log.addHandler(_fh)


def _ssl_ctx():
    if ES_VERIFY_SSL:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _index_name() -> str:
    return f"{ES_INDEX_PREFIX}-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}"


def _ship(doc: dict) -> None:
    url  = f"{ES_HOST}/{_index_name()}/_doc"
    body = json.dumps(doc, ensure_ascii=False, default=str).encode()
    req  = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {_auth_header}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3, context=_ssl_ctx()):
            pass
    except Exception as e:
        _fallback_log.warning("ES unavailable (%s): %s", e, json.dumps(doc, ensure_ascii=False, default=str))


def _worker() -> None:
    while True:
        doc = _queue.get()
        if doc is None:
            break
        _ship(doc)
        _queue.task_done()


_shipper = Thread(target=_worker, daemon=True, name="es-log-shipper")
_shipper.start()


def _enqueue(doc: dict) -> None:
    doc.setdefault("@timestamp", datetime.now(timezone.utc).isoformat())
    doc["host"] = HOSTNAME
    try:
        _queue.put_nowait(doc)
    except Full:
        pass


# ── Public logging functions ──────────────────────────────────────────────────

def log_lifecycle(event: str, detail: str = "") -> None:
    _enqueue({"type": "lifecycle", "event": event, "detail": detail, "level": "INFO"})


def log_error(error: Exception, context: dict | None = None) -> None:
    _enqueue({
        "type":      "app_error",
        "level":     "ERROR",
        "error":     type(error).__name__,
        "message":   str(error),
        "traceback": traceback.format_exc(),
        "context":   context or {},
    })


def log_slow_query(sql: str, duration_ms: float, params=None) -> None:
    _enqueue({
        "type":         "slow_query",
        "level":        "WARNING",
        "sql":          sql,
        "duration_ms":  round(duration_ms, 2),
        "params":       str(params) if params else None,
        "threshold_ms": SLOW_QUERY_MS,
    })


def log_request(method, path, status, duration_ms, remote_addr, user_agent="", response_size=0):
    level = "ERROR" if status >= 500 else "WARNING" if status >= 400 else "INFO"
    _enqueue({
        "type":          "http_request",
        "level":         level,
        "method":        method,
        "path":          path,
        "status":        status,
        "duration_ms":   round(duration_ms, 2),
        "remote_addr":   remote_addr,
        "user_agent":    user_agent,
        "response_size": response_size,
    })


# ── Flask integration ─────────────────────────────────────────────────────────

def setup_logging(app) -> None:
    @app.before_request
    def _before():
        from flask import g
        g._t0 = time.perf_counter()

    @app.after_request
    def _after(response):
        from flask import g, request
        duration_ms = (time.perf_counter() - getattr(g, "_t0", time.perf_counter())) * 1000
        log_request(
            method        = request.method,
            path          = request.path,
            status        = response.status_code,
            duration_ms   = duration_ms,
            remote_addr   = request.remote_addr or "",
            user_agent    = request.headers.get("User-Agent", ""),
            response_size = response.calculate_content_length() or 0,
        )
        return response

    @app.errorhandler(Exception)
    def _on_error(exc):
        from flask import request, jsonify
        log_error(exc, context={"method": request.method, "path": request.path})
        app.logger.exception("Unhandled exception")
        return jsonify({"error": "Internal server error"}), 500

    log_lifecycle("startup", f"Flask app starting — ES→{ES_HOST}")

    import atexit
    atexit.register(lambda: (
        log_lifecycle("shutdown", "Flask app shutting down"),
        _queue.join(),
        _queue.put(None),
    ))
