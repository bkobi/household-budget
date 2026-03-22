from flask import Blueprint, request, jsonify
from app.services.stats import monthly_summary, monthly_trend

stats_bp = Blueprint("stats", __name__)

@stats_bp.route("/summary", methods=["GET"])
def summary():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    if not month or not year:
        return jsonify({"error": "month and year required"}), 400
    return jsonify(monthly_summary(month, year))

@stats_bp.route("/trend", methods=["GET"])
def trend():
    year = request.args.get("year", type=int)
    if not year:
        return jsonify({"error": "year required"}), 400
    return jsonify(monthly_trend(year))
