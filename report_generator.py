import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
REGULAR_FONT = "DejaVuSans"
BOLD_FONT = "DejaVuSans-Bold"

def register_fonts():
    regular = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    bold = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
    if not os.path.isfile(regular) or not os.path.isfile(bold):
        raise FileNotFoundError(f"Шрифты PDF не найдены. Ожидаются: {regular} и {bold}")
    if REGULAR_FONT not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont(REGULAR_FONT, regular))
    if BOLD_FONT not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont(BOLD_FONT, bold))

def create_report(uid, name, num, ch, rid, energy_scores=None, sphere_analysis=None):
    register_fonts(); os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"report_{uid}_{rid}.pdf")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName=BOLD_FONT, alignment=TA_CENTER, fontSize=22, leading=28, spaceAfter=12)
    heading = ParagraphStyle("ReportHeading", parent=styles["Heading1"], fontName=BOLD_FONT, fontSize=16, leading=21, spaceBefore=8, spaceAfter=8)
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName=REGULAR_FONT, fontSize=10.5, leading=16, spaceAfter=6)
    story = []
    image_path = os.path.join(BASE_DIR, "images", "chakras", f"{num:02d}_{['muladhara','svadhisthana','manipura','anahata','vishuddha','ajna','sahasrara'][num-1]}.jpg")
    if os.path.exists(image_path): story.append(Image(image_path, width=9*cm, height=9*cm))
    story += [Spacer(1, .5*cm), Paragraph("ПЕРСОНАЛЬНЫЙ ЭНЕРГЕТИЧЕСКИЙ ОТЧЁТ", title), Paragraph(name or "Пользователь", body), Paragraph(ch["name"], heading), Paragraph(ch["question"], body), PageBreak()]
    sections = [
        ("О вашей ведущей чакре", [ch["responsibility"]]),
        ("Сильные стороны", ch["strengths"]),
        ("Стратегия заработка", [ch["money"]]),
        ("Что может мешать доходу", ch["money_risks"] if isinstance(ch["money_risks"], list) else [ch["money_risks"]]),
        ("Подходящие направления и профессии", ch["professions"]),
        ("Что лучше избегать", [ch["avoid"]]),
        ("Когда чакра уходит в минус", ch["minus"]),
        ("Как вернуть чакру в ресурс и плюс", ch["recovery"]),
    ]
    for section_title, items in sections:
        story.append(Paragraph(section_title, heading))
        for item in items: story.append(Paragraph("• " + str(item), body))
        story.append(Spacer(1, .35*cm))
    if energy_scores:
        story += [PageBreak(), Paragraph("ВАША ЭНЕРГОКАРТА", title)]
        names = ["Чакра 1","Чакра 2","Чакра 3","Чакра 4","Чакра 5","Чакра 6","Чакра 7"]
        for i in range(1,8): story.append(Paragraph(f"<b>{names[i-1]}</b>: {energy_scores.get(i,0)}/5", body))
    if sphere_analysis:
        story.append(Paragraph("АНАЛИЗ СФЕР ЖИЗНИ", title))
        labels = {"health":"Здоровье и ресурс", "relationships":"Отношения", "money":"Деньги и реализация"}
        for key in ("health","relationships","money"):
            item = sphere_analysis[key]
            story.append(Paragraph(f"<b>{labels[key]}</b>: {item['score']}/5 — {item['level']}", body))
    story += [PageBreak(), Paragraph("Важно", heading), Paragraph("Материалы отчёта предназначены для саморефлексии и не являются медицинской, психологической или финансовой диагностикой.", body)]
    SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm, title="Персональный энергетический отчёт").build(story)
    return path
