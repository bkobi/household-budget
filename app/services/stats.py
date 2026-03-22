from app import get_db
from app.models import CATEGORIES


def spending_by_category(month: int, year: int) -> dict:
    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM transactions"
        " WHERE strftime('%m', date) = ? AND strftime('%Y', date) = ?"
        " GROUP BY category",
        (f"{month:02d}", str(year))
    ).fetchall()
    conn.close()
    return {r["category"]: float(r["total"]) for r in rows}


def monthly_summary(month: int, year: int) -> dict:
    spent_by_cat = spending_by_category(month, year)
    total_spent  = sum(spent_by_cat.values())

    conn     = get_db()
    budgets  = conn.execute("SELECT * FROM budgets WHERE month=? AND year=?", (month, year)).fetchall()
    income_r = conn.execute("SELECT * FROM monthly_income WHERE month=? AND year=?", (month, year)).fetchone()
    conn.close()

    budget_map = {b["category"]: b["amount"] for b in budgets}
    income     = income_r["amount"] if income_r else 0

    categories = []
    for cat in CATEGORIES:
        cid    = cat["id"]
        spent  = spent_by_cat.get(cid, 0)
        budget = budget_map.get(cid, 0)
        categories.append({
            **cat,
            "spent":   spent,
            "budget":  budget,
            "diff":    budget - spent,
            "percent": round(spent / budget * 100, 1) if budget > 0 else None,
        })

    return {
        "month": month, "year": year,
        "income": income, "total_spent": total_spent,
        "remaining": income - total_spent,
        "categories": categories,
    }


def monthly_trend(year: int) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT CAST(strftime('%m', date) AS INTEGER) as month, SUM(amount) as total"
        " FROM transactions WHERE strftime('%Y', date) = ?"
        " GROUP BY month ORDER BY month",
        (str(year),)
    ).fetchall()
    conn.close()
    by_month = {r["month"]: float(r["total"]) for r in rows}
    return [{"month": m, "total": by_month.get(m, 0)} for m in range(1, 13)]
