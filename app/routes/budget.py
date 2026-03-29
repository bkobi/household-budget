from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import get_db
from app.models import CATEGORY_IDS
from app.services.stats import spending_by_category

budget_bp = Blueprint("budget", __name__)


@budget_bp.before_request
@login_required
def require_login():
    pass


def _validate_month_year(month, year):
    if not month or not year:
        return "month and year required"
    if not (1 <= month <= 12):
        return "month must be 1–12"
    if not (2000 <= year <= 2100):
        return "year out of range"
    return None


@budget_bp.route("/", methods=["GET"])
def get_budget():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    err = _validate_month_year(month, year)
    if err:
        return jsonify({"error": err}), 400
    try:
        conn    = get_db()
        budgets = conn.execute("SELECT * FROM budgets WHERE month=? AND year=?", (month, year)).fetchall()
        income  = conn.execute("SELECT * FROM monthly_income WHERE month=? AND year=?", (month, year)).fetchone()
        conn.close()
        return jsonify({
            "budgets": [dict(b) for b in budgets],
            "income":  dict(income) if income else {"month": month, "year": year, "amount": 0},
        })
    except Exception:
        return jsonify({"error": "Database error"}), 500


@budget_bp.route("/category", methods=["POST"])
def set_category_budget():
    data = request.get_json()
    for f in ("month", "year", "category", "amount"):
        if f not in data:
            return jsonify({"error": f"Missing: {f}"}), 400
    err = _validate_month_year(data.get("month"), data.get("year"))
    if err:
        return jsonify({"error": err}), 400
    if data["category"] not in CATEGORY_IDS:
        return jsonify({"error": "Invalid category"}), 400
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO budgets (month, year, category, amount) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(month, year, category) DO UPDATE SET amount=excluded.amount",
            (data["month"], data["year"], data["category"], float(data["amount"]))
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM budgets WHERE month=? AND year=? AND category=?",
            (data["month"], data["year"], data["category"])
        ).fetchone()
        conn.close()
        return jsonify(dict(row))
    except Exception:
        return jsonify({"error": "Database error"}), 500


@budget_bp.route("/income", methods=["POST"])
def set_income():
    data = request.get_json()
    for f in ("month", "year", "amount"):
        if f not in data:
            return jsonify({"error": f"Missing: {f}"}), 400
    err = _validate_month_year(data.get("month"), data.get("year"))
    if err:
        return jsonify({"error": err}), 400
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO monthly_income (month, year, amount) VALUES (?, ?, ?)"
            " ON CONFLICT(month, year) DO UPDATE SET amount=excluded.amount",
            (data["month"], data["year"], float(data["amount"]))
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM monthly_income WHERE month=? AND year=?", (data["month"], data["year"])
        ).fetchone()
        conn.close()
        return jsonify(dict(row))
    except Exception:
        return jsonify({"error": "Database error"}), 500


@budget_bp.route("/alerts", methods=["GET"])
def get_alerts():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    err = _validate_month_year(month, year)
    if err:
        return jsonify({"error": err}), 400
    try:
        conn    = get_db()
        budgets = conn.execute("SELECT * FROM budgets WHERE month=? AND year=?", (month, year)).fetchall()
        conn.close()
        spent   = spending_by_category(month, year)
        alerts  = []
        for b in budgets:
            if b["amount"] <= 0:
                continue
            sp  = spent.get(b["category"], 0)
            pct = sp / b["amount"] * 100
            if pct >= 80:
                alerts.append({
                    "category": b["category"],
                    "budget":   b["amount"],
                    "spent":    sp,
                    "percent":  round(pct, 1),
                    "level":    "danger" if pct >= 100 else "warning",
                })
        return jsonify(sorted(alerts, key=lambda a: a["percent"], reverse=True))
    except Exception:
        return jsonify({"error": "Database error"}), 500
