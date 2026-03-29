from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.services.stats import monthly_summary, monthly_trend

stats_bp = Blueprint("stats", __name__)


@stats_bp.before_request
@login_required
def require_login():
    pass

@stats_bp.route("/summary", methods=["GET"])
def summary():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    if not month or not year:
        return jsonify({"error": "month and year required"}), 400
    if not (1 <= month <= 12):
        return jsonify({"error": "month must be 1–12"}), 400
    if not (2000 <= year <= 2100):
        return jsonify({"error": "year out of range"}), 400
    return jsonify(monthly_summary(month, year))

@stats_bp.route("/trend", methods=["GET"])
def trend():
    year = request.args.get("year", type=int)
    if not year:
        return jsonify({"error": "year required"}), 400
    if not (2000 <= year <= 2100):
        return jsonify({"error": "year out of range"}), 400
    return jsonify(monthly_trend(year))
