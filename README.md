# 🏠 משק הבית שלי

אפליקציית ווב לניהול הוצאות ותקציב משק הבית — בנויה עם Python Flask.

## מבנה הפרויקט

```
household-budget/
├── run.py                      # נקודת כניסה
├── requirements.txt
├── .env.example
├── .gitignore
├── app/
│   ├── __init__.py             # App factory
│   ├── models/
│   │   └── __init__.py         # Transaction, Budget, MonthlyIncome
│   ├── routes/
│   │   ├── main.py             # GET /
│   │   ├── transactions.py     # /api/transactions/
│   │   ├── budget.py           # /api/budget/
│   │   ├── stats.py            # /api/stats/
│   │   └── exports.py          # /api/exports/
│   ├── services/
│   │   ├── stats.py            # לוגיקת סיכום וטרנד
│   │   ├── excel_export.py     # ייצוא openpyxl
│   │   └── pdf_export.py       # ייצוא reportlab
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/main.css
│       └── js/
│           ├── api.js          # fetch wrapper
│           └── app.js          # לוגיקת UI
└── tests/
    └── test_api.py
```

## התקנה והרצה

```bash
# שכפל את הריפו
git clone <your-repo-url>
cd household-budget

# צור סביבה וירטואלית
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# התקן תלויות
pip install -r requirements.txt

# הגדר משתני סביבה
cp .env.example .env

# הרץ את האפליקציה
python run.py
```

פתח בדפדפן: [http://localhost:5000](http://localhost:5000)

## API Endpoints

| Method | Path | תיאור |
|--------|------|--------|
| GET | `/` | דף ראשי |
| GET | `/api/transactions/?month=&year=` | רשימת הוצאות |
| POST | `/api/transactions/` | הוספת הוצאה |
| PUT | `/api/transactions/<id>` | עדכון הוצאה |
| DELETE | `/api/transactions/<id>` | מחיקת הוצאה |
| GET | `/api/budget/?month=&year=` | תקציב והכנסה |
| POST | `/api/budget/category` | שמירת תקציב קטגוריה |
| POST | `/api/budget/income` | שמירת הכנסה |
| GET | `/api/budget/alerts?month=&year=` | התראות חריגה |
| GET | `/api/stats/summary?month=&year=` | סיכום חודשי |
| GET | `/api/stats/trend?year=` | מגמה שנתית |
| GET | `/api/exports/excel?month=&year=` | הורדת קובץ Excel |
| GET | `/api/exports/pdf?month=&year=` | הורדת דוח PDF |

## הרצת בדיקות

```bash
pytest tests/ -v
```

## קטגוריות

מזון וסופר · דיור ושכירות · תחבורה · בריאות · בילויים · ביגוד · חינוך · אחר

## טכנולוגיות

- **Backend**: Python 3.11+, Flask 3, SQLAlchemy, SQLite
- **Frontend**: HTML5, CSS3, Vanilla JS, Chart.js
- **ייצוא**: openpyxl (Excel), ReportLab (PDF)
