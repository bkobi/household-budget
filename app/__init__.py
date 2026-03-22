from flask import Flask
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "budget.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(app):
    conn = get_db()
    conn.executescript("""
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
    app.config["SECRET_KEY"] = "dev-secret-change-in-production"

    if config:
        app.config.update(config)
        if "DB_PATH" in config:
            import app as _app_mod
            _app_mod.DB_PATH = config["DB_PATH"]

    from app.routes.main         import main_bp
    from app.routes.transactions import transactions_bp
    from app.routes.budget       import budget_bp
    from app.routes.exports      import exports_bp
    from app.routes.stats        import stats_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(budget_bp,       url_prefix="/api/budget")
    app.register_blueprint(exports_bp,      url_prefix="/api/exports")
    app.register_blueprint(stats_bp,        url_prefix="/api/stats")

    init_db(app)
    return app
