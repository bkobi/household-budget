from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from app import get_db
from app.models import CATEGORIES
import os

FONT      = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GREEN     = colors.HexColor("#217346")
GREEN_L   = colors.HexColor("#E8F5EE")
RED       = colors.HexColor("#E24B4A")
RED_L     = colors.HexColor("#FDE8E8")
GRAY_L    = colors.HexColor("#F2F2F2")
WHITE     = colors.white
MONTHS_HE = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
             "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]

def _reg():
    if "Heb" not in pdfmetrics.getRegisteredFontNames():
        if os.path.exists(FONT):      pdfmetrics.registerFont(TTFont("Heb",     FONT))
        if os.path.exists(FONT_BOLD): pdfmetrics.registerFont(TTFont("Heb-Bold",FONT_BOLD))

def _fmt(n): return f"₪{n:,.0f}"

def export_pdf(month: int, year: int, summary: dict) -> str:
    _reg()
    fn = "Heb" if "Heb" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    fb = "Heb-Bold" if "Heb-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"

    path = f"/tmp/budget_{year}_{month:02d}.pdf"
    doc  = SimpleDocTemplate(path, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm,   bottomMargin=2*cm)

    s_title   = ParagraphStyle("t",  fontName=fb, fontSize=18, alignment=TA_CENTER, textColor=GREEN, spaceAfter=4)
    s_sub     = ParagraphStyle("s",  fontName=fn, fontSize=11, alignment=TA_CENTER, textColor=colors.gray, spaceAfter=16)
    s_section = ParagraphStyle("h2", fontName=fb, fontSize=13, textColor=colors.HexColor("#333333"), spaceBefore=14, spaceAfter=8)

    story = [
        Paragraph("דוח משק בית", s_title),
        Paragraph(f"{MONTHS_HE[month]} {year}", s_sub),
        HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=14),
    ]

    # KPI
    rem      = summary["income"] - summary["total_spent"]
    rem_col  = GREEN if rem >= 0 else RED
    kpi = Table(
        [[_fmt(summary["income"]), _fmt(summary["total_spent"]), _fmt(rem)],
         ["הכנסה", "הוצאות", "יתרה"]],
        colWidths=[5*cm, 5*cm, 5*cm]
    )
    kpi.setStyle(TableStyle([
        ("FONTNAME",      (0,0),(-1,-1), fn),
        ("FONTNAME",      (0,0),(-1, 0), fb),
        ("FONTSIZE",      (0,0),(-1, 0), 16),
        ("FONTSIZE",      (0,1),(-1, 1), 10),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BACKGROUND",    (0,0),(0,-1),  GREEN_L),
        ("BACKGROUND",    (1,0),(1,-1),  RED_L),
        ("BACKGROUND",    (2,0),(2,-1),  GREEN_L if rem>=0 else RED_L),
        ("TEXTCOLOR",     (0,0),(0, 0),  GREEN),
        ("TEXTCOLOR",     (1,0),(1, 0),  RED),
        ("TEXTCOLOR",     (2,0),(2, 0),  rem_col),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("INNERGRID",     (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    story += [kpi, Spacer(1, 18)]

    # Categories
    story.append(Paragraph("פירוט לפי קטגוריה", s_section))
    cat_rows = [["קטגוריה", "תקציב", "בפועל", "הפרש", "ניצול"]]
    active_cats = [c for c in summary["categories"] if c["spent"] > 0 or c["budget"] > 0]
    for cat in active_cats:
        cat_rows.append([
            cat["name"], _fmt(cat["budget"]), _fmt(cat["spent"]),
            _fmt(cat["budget"] - cat["spent"]),
            f"{cat['percent']:.1f}%" if cat["percent"] is not None else "–",
        ])
    ct = Table(cat_rows, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 2.5*cm])
    cmds = [
        ("FONTNAME",      (0,0),(-1,-1), fn),
        ("FONTNAME",      (0,0),(-1, 0), fb),
        ("FONTSIZE",      (0,0),(-1,-1), 10),
        ("ALIGN",         (1,0),(-1,-1), "CENTER"),
        ("ALIGN",         (0,1),(0,-1),  "RIGHT"),
        ("BACKGROUND",    (0,0),(-1, 0), GREEN),
        ("TEXTCOLOR",     (0,0),(-1, 0), WHITE),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("INNERGRID",     (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ]
    for i, cat in enumerate(active_cats, 1):
        over = cat["budget"] > 0 and cat["spent"] > cat["budget"]
        warn = not over and cat["percent"] and cat["percent"] >= 80
        bg   = RED_L if over else (colors.HexColor("#FFF8E8") if warn else (GRAY_L if i%2==0 else WHITE))
        cmds.append(("BACKGROUND", (0,i),(-1,i), bg))
    ct.setStyle(TableStyle(cmds))
    story += [ct, Spacer(1, 18)]

    # Transactions
    conn = get_db()
    txns = conn.execute(
        "SELECT * FROM transactions WHERE strftime('%m',date)=? AND strftime('%Y',date)=? ORDER BY date",
        (f"{month:02d}", str(year))
    ).fetchall()
    conn.close()

    if txns:
        story.append(Paragraph("רשימת הוצאות", s_section))
        txn_rows = [["תאריך", "תיאור", "קטגוריה", "סכום"]]
        for t in txns:
            cat_name = next((c["name"] for c in CATEGORIES if c["id"]==t["category"]), t["category"])
            txn_rows.append([t["date"], t["description"], cat_name, _fmt(t["amount"])])
        tt = Table(txn_rows, colWidths=[3*cm, 6.5*cm, 4*cm, 3*cm])
        tt.setStyle(TableStyle([
            ("FONTNAME",       (0,0),(-1,-1), fn),
            ("FONTNAME",       (0,0),(-1, 0), fb),
            ("FONTSIZE",       (0,0),(-1,-1), 9),
            ("ALIGN",          (0,0),(-1,-1), "CENTER"),
            ("ALIGN",          (1,1),(2,-1),  "RIGHT"),
            ("BACKGROUND",     (0,0),(-1, 0), GREEN),
            ("TEXTCOLOR",      (0,0),(-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [WHITE, GRAY_L]),
            ("BOX",            (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ("INNERGRID",      (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ("TOPPADDING",     (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
        ]))
        story.append(tt)

    doc.build(story)
    return path
