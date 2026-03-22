from flask import Blueprint, request, send_file, jsonify
from app.services.stats import monthly_summary
from app.services.excel_export import export_excel
from app.services.pdf_export import export_pdf

exports_bp = Blueprint("exports", __name__)

@exports_bp.route("/excel", methods=["GET"])
def download_excel():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    if not month or not year:
        return jsonify({"error": "month and year required"}), 400
    summary = monthly_summary(month, year)
    path    = export_excel(month, year, summary)
    return send_file(path, as_attachment=True,
                     download_name=f"budget_{year}_{month:02d}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@exports_bp.route("/pdf", methods=["GET"])
def download_pdf():
    month = request.args.get("month", type=int)
    year  = request.args.get("year",  type=int)
    if not month or not year:
        return jsonify({"error": "month and year required"}), 400
    summary = monthly_summary(month, year)
    path    = export_pdf(month, year, summary)
    return send_file(path, as_attachment=True,
                     download_name=f"budget_{year}_{month:02d}.pdf",
                     mimetype="application/pdf")
