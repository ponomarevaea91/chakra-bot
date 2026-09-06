import os
from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from data import CHAKRAS, CHAKRA_GUIDANCE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
REGULAR_FONT = "DejaVuSans"
BOLD_FONT = "DejaVuSans-Bold"
CHAKRA_KEYS = ["muladhara","svadhisthana","manipura","anahata","vishuddha","ajna","sahasrara"]

def register_fonts():
    regular = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    bold = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
    if not os.path.isfile(regular) or not os.path.isfile(bold):
        raise FileNotFoundError(f"Шрифты PDF не найдены: {regular}, {bold}")
    if REGULAR_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(REGULAR_FONT, regular))
    if BOLD_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(BOLD_FONT, bold))

def _font(size=28, bold=False):
    candidates = [
        os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def make_energy_map_jpg(path, scores):
    """Создаёт JPG-карту из фактических оценок пользователя для вставки в PDF."""
    w, h = 1200, 1500
    im = PILImage.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    title_font = _font(54, True)
    head_font = _font(30, True)
    body_font = _font(28, False)
    d.text((70, 55), "ЛИЧНАЯ ЭНЕРГОКАРТА", font=title_font, fill="black")
    d.text((70, 130), "Субъективная оценка состояния чакр по шкале 1–5", font=body_font, fill="black")
    names = [f"Чакра {i}" for i in range(1, 8)]
    y = 230
    for i, name in enumerate(names, 1):
        score = float(scores.get(i, 0))
        d.text((80, y), name, font=head_font, fill="black")
        d.text((80, y+50), f"{score:.2f}/5", font=body_font, fill="black")
        x0, x1 = 300, 1080
        bar_y = y + 25
        d.rounded_rectangle((x0, bar_y, x1, bar_y+34), radius=16, outline="#777777", width=2, fill="#eeeeee")
        d.rounded_rectangle((x0, bar_y, x0 + int((x1-x0)*max(0,min(score,5))/5), bar_y+34), radius=16, fill="#777777")
        y += 170
    d.text((80, 1410), "1 — совсем не про меня · 5 — полностью про меня", font=body_font, fill="black")
    im.save(path, "JPEG", quality=94, optimize=True)

def _bullets(story, items, body):
    for item in items:
        story.append(Paragraph("• " + str(item), body))
        story.append(Spacer(1, 0.06*cm))

def create_report(uid, name, num, ch, rid, energy_scores=None, sphere_analysis=None):
    register_fonts()
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"report_{uid}_{rid}.pdf")

    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName=BOLD_FONT, alignment=TA_CENTER,
                           fontSize=21, leading=27, spaceAfter=12)
    heading = ParagraphStyle("ReportHeading", parent=styles["Heading1"], fontName=BOLD_FONT,
                             fontSize=15, leading=20, spaceBefore=8, spaceAfter=7)
    subheading = ParagraphStyle("ReportSub", parent=styles["Heading2"], fontName=BOLD_FONT,
                                fontSize=12, leading=16, spaceBefore=7, spaceAfter=5)
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName=REGULAR_FONT,
                          fontSize=9.6, leading=14, spaceAfter=5)
    small = ParagraphStyle("ReportSmall", parent=body, fontSize=8.5, leading=12)
    note = ParagraphStyle("ReportNote", parent=body, fontSize=8.5, leading=12, leftIndent=8, rightIndent=8)

    story = []

    # Cover / leading chakra image
    image_path = os.path.join(BASE_DIR, "images", "chakras", f"{num:02d}_{CHAKRA_KEYS[num-1]}.jpg")
    if os.path.exists(image_path):
        story.append(Image(image_path, width=8.3*cm, height=8.3*cm))
        story.append(Spacer(1, .25*cm))
    story += [
        Paragraph("ПЕРСОНАЛЬНЫЙ ЭНЕРГЕТИЧЕСКИЙ ОТЧЁТ", title),
        Paragraph(name or "Пользователь", body),
        Paragraph(ch["name"], heading),
        Paragraph("«" + ch["question"] + "»", body),
        Paragraph(ch["responsibility"], body),
        Paragraph("<b>Важно:</b> это материал для саморефлексии. Описания здоровья не являются медицинским диагнозом.", note),
        PageBreak(),
    ]

    # Leading chakra: extended content from the method pages 18–38
    story.append(Paragraph("1. Ведущая чакра — подробный разбор", heading))
    story.append(Paragraph("Как это может проявляться", subheading))
    story.append(Paragraph(CHAKRA_GUIDANCE[num]["recognition"], body))
    story.append(Paragraph("Сильные стороны", subheading))
    _bullets(story, ch["strengths"], body)
    story.append(Paragraph("Деньги и реализация", subheading))
    story.append(Paragraph(ch["money"], body))
    story.append(Paragraph("Что может мешать доходу", subheading))
    _bullets(story, ch["money_risks"] if isinstance(ch["money_risks"], list) else [ch["money_risks"]], body)
    story.append(Paragraph("Подходящие направления", subheading))
    _bullets(story, ch["professions"], body)
    story.append(Paragraph("Что лучше избегать", subheading))
    story.append(Paragraph(ch["avoid"], body))

    for sphere, title_text in (
        ("health", "❤️ Что делать, если чакра в минусе — здоровье"),
        ("relationships", "🤝 Что делать, если чакра в минусе — отношения"),
        ("money", "💰 Что делать, если чакра в минусе — деньги"),
    ):
        story.append(Paragraph(title_text, subheading))
        _bullets(story, CHAKRA_GUIDANCE[num][sphere], body)

    story.append(Paragraph("Признаки зоны внимания", subheading))
    _bullets(story, ch["minus"], body)

    # Energy map visual
    if energy_scores:
        map_jpg = os.path.join(REPORTS_DIR, f"energy_map_{uid}_{rid}.jpg")
        make_energy_map_jpg(map_jpg, energy_scores)
        story += [PageBreak(), Paragraph("2. Ваша личная энергокарта", title)]
        story.append(Image(map_jpg, width=15.8*cm, height=19.75*cm))
        story.append(Spacer(1, .2*cm))
        story.append(Paragraph("Чем ниже значение, тем больше внимания методика предлагает направить на соответствующую тему. Значение ниже 3 — зона, для которой в отчёте ниже добавлена сжатая выдержка рекомендаций по этой чакре.", note))

        # Every chakra score; expanded excerpt for each score < 3
        for i in range(1, 8):
            score = float(energy_scores.get(i, 0))
            story.append(PageBreak())
            story.append(Paragraph(f"3.{i} {CHAKRAS[i]['name']} — {score:.2f}/5", heading))
            story.append(Paragraph(CHAKRAS[i]["responsibility"], body))
            if score < 3:
                story.append(Paragraph("Краткая выдержка, если значение ниже 3", subheading))
                story.append(Paragraph(CHAKRA_GUIDANCE[i]["recognition"], body))
                for sphere, label in (("health","Здоровье"),("relationships","Отношения"),("money","Деньги")):
                    story.append(Paragraph(label, subheading))
                    _bullets(story, CHAKRA_GUIDANCE[i][sphere][:2], body)
            else:
                story.append(Paragraph("Поддержание ресурса", subheading))
                _bullets(story, CHAKRAS[i]["recovery"][:3], body)

    # Sphere analysis with actual recommendations
    if sphere_analysis:
        story += [PageBreak(), Paragraph("4. Анализ сфер жизни и рекомендации", title)]
        labels = {
            "health": ("❤️ Здоровье и ресурс", "health"),
            "relationships": ("🤝 Отношения", "relationships"),
            "money": ("💰 Деньги и реализация", "money"),
        }
        for key in ("health", "relationships", "money"):
            item = sphere_analysis[key]
            story.append(Paragraph(f"{labels[key][0]} — {item['score']}/5 — {item['level']}", heading))
            strong = ", ".join(CHAKRAS[c]["name"] for c in item["strongest"])
            weak = ", ".join(CHAKRAS[c]["name"] for c in item["weakest"])
            story.append(Paragraph(f"<b>Опора:</b> {strong}.", body))
            story.append(Paragraph(f"<b>Зона внимания:</b> {weak}.", body))
            # Combine recommendations from the two weakest chakras to make this section actionable.
            recs = []
            for c in item["weakest"]:
                recs.extend(CHAKRA_GUIDANCE[c][key])
            story.append(Paragraph("Что делать:", subheading))
            _bullets(story, recs[:4], body)

    story += [
        PageBreak(),
        Paragraph("5. Как пользоваться отчётом", title),
        Paragraph("Начните с одной зоны внимания, а не пытайтесь менять всё сразу. Выберите 1–2 действия из рекомендаций на ближайшую неделю, затем наблюдайте за своим состоянием и повторяйте энергокарту позже для сравнения.", body),
        Paragraph("Ограничения методики", heading),
        Paragraph("Материалы отчёта предназначены для саморефлексии и не являются медицинской, психологической или финансовой диагностикой. При симптомах или финансовых/психологических трудностях, требующих профессиональной помощи, обращайтесь к соответствующему специалисту.", note),
    ]

    SimpleDocTemplate(path, pagesize=A4, leftMargin=1.7*cm, rightMargin=1.7*cm,
                      topMargin=1.6*cm, bottomMargin=1.6*cm,
                      title="Персональный энергетический отчёт").build(story)
    return path
