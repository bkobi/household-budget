from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import get_db
from app.models import CATEGORY_IDS

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.before_request
@login_required
def require_login():
    pass


def row_to_dict(row):
    return {"id": row["id"], "description": row["description"],
            "amount": row["amount"], "category": row["category"], "date": row["date"]}


@transactions_bp.route("/", methods=["GET"])
def list_transactions():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    if month is not None and not (1 <= month <= 12):
        return jsonify({"error": "month must be 1–12"}), 400
    if year is not None and not (2000 <= year <= 2100):
        return jsonify({"error": "year out of range"}), 400
    try:
        conn = get_db()
        if month and year:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE strftime('%m', date) = ? AND strftime('%Y', date) = ?"
                " ORDER BY date DESC",
                (f"{month:02d}", str(year))
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()
        conn.close()
        return jsonify([row_to_dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": "Database error"}), 500


@transactions_bp.route("/", methods=["POST"])
def create_transaction():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    for f in ("description", "amount", "category", "date"):
        if f not in data:
            return jsonify({"error": f"Missing: {f}"}), 400
    if data["category"] not in CATEGORY_IDS:
        return jsonify({"error": "Invalid category"}), 400
    if float(data["amount"]) <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    try:
        conn = get_db()
        cur  = conn.execute(
            "INSERT INTO transactions (description, amount, category, date) VALUES (?, ?, ?, ?)",
            (data["description"], float(data["amount"]), data["category"], data["date"])
        )
        conn.commit()
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (cur.lastrowid,)).fetchone()
        conn.close()
        return jsonify(row_to_dict(row)), 201
    except Exception as e:
        return jsonify({"error": "Database error"}), 500


@transactions_bp.route("/<int:txn_id>", methods=["DELETE"])
def delete_transaction(txn_id):
    try:
        conn = get_db()
        row  = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Not found"}), 404
        conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
        conn.commit()
        conn.close()
        return jsonify({"deleted": txn_id})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500


@transactions_bp.route("/<int:txn_id>", methods=["PUT"])
def update_transaction(txn_id):
    try:
        conn = get_db()
        row  = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Not found"}), 404
        data   = request.get_json()
        desc   = data.get("description", row["description"])
        amount = float(data.get("amount", row["amount"]))
        cat    = data.get("category", row["category"])
        date   = data.get("date", row["date"])
        if amount <= 0:
            conn.close()
            return jsonify({"error": "Amount must be positive"}), 400
        if cat not in CATEGORY_IDS:
            conn.close()
            return jsonify({"error": "Invalid category"}), 400
        conn.execute(
            "UPDATE transactions SET description=?, amount=?, category=?, date=? WHERE id=?",
            (desc, amount, cat, date, txn_id)
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
        conn.close()
        return jsonify(row_to_dict(updated))
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
