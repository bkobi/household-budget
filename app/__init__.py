from flask import Flask, redirect, url_for
from flask_login import LoginManager
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "budget.db")

# Set ES_LOGGING=0 in .env to disable (e.g. during tests)
_ES_LOGGING = os.getenv("ES_LOGGING", "1") == "1"

login_manager = LoginManager()


def get_db():
    if _ES_LOGGING:
        from app.db import get_instrumented_db
        return get_instrumented_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(app):
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS budgets (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            month    INTEGER NOT NULL,
            year     INTEGER NOT NULL,
            category TEXT    NOT NULL,
            amount   REAL    NOT NULL DEFAULT 0,
            UNIQUE(month, year, category)
        );
        CREATE TABLE IF NOT EXISTS monthly_income (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            month  INTEGER NOT NULL,
            year   INTEGER NOT NULL,
            amount REAL    NOT NULL DEFAULT 0,
            UNIQUE(month, year)
        );
    """)
    conn.commit()
    conn.close()


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

    if config:
        app.config.update(config)
        if "DB_PATH" in config:
            import app as _app_mod
            _app_mod.DB_PATH = config["DB_PATH"]

    # ── Flask-Login ───────────────────────────────────────────────────────────
    login_manager.login_view = "auth.login_page"
    login_manager.login_message = None
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.auth_model import User
        conn = get_db()
        row  = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
        conn.close()
        return User(row["id"], row["username"]) if row else None

    # Redirect to /setup when no users exist yet
    @app.before_request
    def _auto_setup():
        from flask import request
        if request.endpoint in ("auth.setup", "auth.setup_page", "static"):
            return
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        if count == 0:
            return redirect(url_for("auth.setup_page"))

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.main         import main_bp
    from app.routes.transactions import transactions_bp
    from app.routes.budget       import budget_bp
    from app.routes.exports      import exports_bp
    from app.routes.stats        import stats_bp
    from app.routes.auth         import auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(budget_bp,       url_prefix="/api/budget")
    app.register_blueprint(exports_bp,      url_prefix="/api/exports")
    app.register_blueprint(stats_bp,        url_prefix="/api/stats")

    init_db(app)

    if _ES_LOGGING and not app.config.get("TESTING"):
        from app.logger import setup_logging
        setup_logging(app)

    return app
