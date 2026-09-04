import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

REGULAR_FONT = "DejaVuSans"
BOLD_FONT = "DejaVuSans-Bold"


def register_fonts():
    """Registers bundled Unicode fonts so Cyrillic is displayed correctly in PDFs."""
    if REGULAR_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont(REGULAR_FONT, os.path.join(FONTS_DIR, "DejaVuSans.ttf"))
        )
    if BOLD_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont(BOLD_FONT, os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"))
        )


def create_report(uid, name, num, ch, rid):
    register_fonts()
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"report_{uid}_{rid}.pdf")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=BOLD_FONT,
        alignment=TA_CENTER,
        fontSize=25,
        leading=32,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading1"],
        fontName=BOLD_FONT,
        fontSize=18,
        leading=24,
        spaceBefore=8,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName=REGULAR_FONT,
        fontSize=10.5,
        leading=16,
        spaceAfter=6,
    )

    story = []
    image_path = os.path.join(BASE_DIR, "images", f"chakra_{num}.jpg")
    if os.path.exists(image_path):
        story.append(Image(image_path, width=10 * cm, height=10 * cm))

    story += [
        Spacer(1, 1 * cm),
        Paragraph("ПЕРСОНАЛЬНЫЙ ЭНЕРГЕТИЧЕСКИЙ ОТЧЁТ", title_style),
        Spacer(1, 1 * cm),
        Paragraph(name or "Пользователь", body_style),
        Paragraph(ch["name"], heading_style),
        Paragraph(ch["question"], body_style),
        PageBreak(),
    ]

    sections = [
        ("О вашей ведущей чакре", [ch["responsibility"]]),
        ("Сильные стороны", ch["strengths"]),
        ("Стратегия заработка", [ch["money"]]),
        ("Что может мешать доходу", ch["money_risks"] if isinstance(ch["money_risks"], list) else [ch["money_risks"]]),
        ("Подходящие направления и профессии", ch["professions"]),
        ("Что лучше избегать", [ch["avoid"]]),
        ("Когда чакра уходит в минус", [ch["minus"]]),
        ("Как вернуть чакру в ресурс и плюс", ch["recovery"]),
        ("Качества состояния в плюсе", ch["strengths"]),
    ]

    for section_title, items in sections:
        story.append(Paragraph(section_title, heading_style))
        for item in items:
            story.append(Paragraph("• " + str(item), body_style))
        story.append(Spacer(1, 0.5 * cm))

    story += [
        PageBreak(),
        Paragraph("Важно", heading_style),
        Paragraph(
            "Материалы отчёта основаны на предоставленной методике и предназначены "
            "для саморефлексии. Они не являются медицинской, психологической или "
            "финансовой диагностикой.",
            body_style,
        ),
    ]

    document = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Персональный энергетический отчёт",
        author="Chakra Bot",
    )
    document.build(story)
    return path
