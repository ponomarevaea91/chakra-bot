import os
from xml.sax.saxutils import escape
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
    Image, Table, TableStyle, KeepTogether
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from data import CHAKRAS, CHAKRA_GUIDANCE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
ASSETS_DIR = os.path.join(BASE_DIR, "images")
COVERS_DIR = os.path.join(ASSETS_DIR, "covers")

REGULAR_FONT = "DejaVuSans"
BOLD_FONT = "DejaVuSans-Bold"
CHAKRA_KEYS = ["muladhara","svadhisthana","manipura","anahata","vishuddha","ajna","sahasrara"]

CHAKRA_COLORS = {
    1: "#C94A4A", 2: "#E89043", 3: "#D8AF35",
    4: "#4F9D69", 5: "#2D91C9", 6: "#5E66B8", 7: "#9A62C8"
}

def register_fonts():
    regular = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    bold = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
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

def _hex(h):
    return colors.HexColor(h)

def _safe(text):
    return escape(str(text or "")).replace("\n", "<br/>")

def make_energy_map(path, scores, leading_chakra=None):
    W, H = 1200, 1450
    im = PILImage.new("RGB", (W, H), "#F7F4EE")
    d = ImageDraw.Draw(im, "RGBA")
    # soft paper-like background
    for r, a in [(560, 22), (450, 16), (350, 10)]:
        d.ellipse((W//2-r, 400-r, W//2+r, 400+r), fill=(60,75,120,a))
    title = _font(52, True)
    body = _font(27, False)
    head = _font(31, True)
    d.text((70, 55), "ЛИЧНАЯ ЭНЕРГОКАРТА", font=title, fill="#18223A")
    d.text((70, 125), "Субъективная оценка состояния по шкале 1–5", font=body, fill="#5D6575")

    cx, cy = 280, 790
    # simple human silhouette
    d.ellipse((cx-55, cy-420, cx+55, cy-310), fill=(32,38,55,235))
    d.polygon([(cx-62,cy-305),(cx+62,cy-305),(cx+95,cy+30),(cx+45,cy+210),(cx-45,cy+210),(cx-95,cy+30)], fill=(32,38,55,235))
    d.line((cx-58,cy-260,cx-155,cy+20), fill=(32,38,55,235), width=32)
    d.line((cx+58,cy-260,cx+155,cy+20), fill=(32,38,55,235), width=32)
    d.line((cx-28,cy+190,cx-62,cy+455), fill=(32,38,55,235), width=38)
    d.line((cx+28,cy+190,cx+62,cy+455), fill=(32,38,55,235), width=38)

    ys = {1: cy+150, 2: cy+95, 3: cy+35, 4: cy-25, 5: cy-85, 6: cy-145, 7: cy-205}
    for i in range(1,8):
        col = CHAKRA_COLORS[i]
        rgb = tuple(int(col[j:j+2],16) for j in (1,3,5))
        yy = ys[i]
        score = float(scores.get(i,0))
        rad = 15 + int(max(0,min(score,5))*2)
        d.ellipse((cx-rad,yy-rad,cx+rad,yy+rad), fill=rgb+(235,), outline=(255,255,255,240), width=4)
        d.ellipse((cx-rad-12,yy-rad-12,cx+rad+12,yy+rad+12), outline=rgb+(90,), width=3)

    # score cards
    x0, y0 = 520, 205
    for i in range(1,8):
        y = y0 + (i-1)*165
        score = float(scores.get(i,0))
        col = CHAKRA_COLORS[i]
        d.rounded_rectangle((x0,y,x0+585,y+128), radius=22, fill=(255,255,255,235), outline=tuple(int(col[j:j+2],16) for j in (1,3,5))+(180,), width=3)
        d.text((x0+25,y+18), f"{i}. {CHAKRAS[i]['name']}", font=head, fill="#18223A")
        d.text((x0+25,y+62), f"{score:.2f} / 5", font=body, fill=col)
        barx0, barx1 = x0+260, x0+545
        d.rounded_rectangle((barx0,y+73,barx1,y+98), radius=12, fill="#E8E5DE")
        filled = barx0 + int((barx1-barx0)*max(0,min(score,5))/5)
        if filled>barx0:
            d.rounded_rectangle((barx0,y+73,filled,y+98), radius=12, fill=col)
    d.text((70, 1340), "1 — совсем не про меня    ·    5 — полностью про меня", font=body, fill="#5D6575")
    im.save(path, quality=95)

def _footer(c, doc):
    c.saveState()
    c.setStrokeColor(_hex("#DED8CB"))
    c.line(1.6*cm, 1.25*cm, A4[0]-1.6*cm, 1.25*cm)
    c.setFont(REGULAR_FONT, 7.5)
    c.setFillColor(_hex("#77736B"))
    c.drawString(1.6*cm, 0.75*cm, "Персональный энергетический отчёт · инструмент саморефлексии")
    c.drawRightString(A4[0]-1.6*cm, 0.75*cm, str(doc.page))
    c.restoreState()

def _cover_page(background_path, chakra_image_path, client_name, gender, chakra):
    def draw(c, doc):
        c.saveState()
        w,h=A4
        if os.path.exists(background_path):
            c.drawImage(background_path,0,0,width=w,height=h,mask='auto',preserveAspectRatio=False)
        else:
            c.setFillColor(_hex("#151D39")); c.rect(0,0,w,h,fill=1,stroke=0)
        # dark translucent veil
        c.setFillColor(colors.Color(0.02,0.04,0.12,alpha=0.20))
        c.rect(0,0,w,h,fill=1,stroke=0)
        c.setFillColor(colors.white)
        c.setFont(BOLD_FONT, 24)
        c.drawCentredString(w/2,h-2.7*cm,"ПЕРСОНАЛЬНЫЙ")
        c.setFont(BOLD_FONT, 28)
        c.drawCentredString(w/2,h-3.7*cm,"ЭНЕРГЕТИЧЕСКИЙ ОТЧЁТ")
        c.setFont(BOLD_FONT, 13)
        c.drawCentredString(w/2,h-5.0*cm,"Персональный разбор ведущей чакры и энергокарты")
        # chakra art panel
        if chakra_image_path and os.path.exists(chakra_image_path):
            c.setFillColor(colors.Color(1,1,1,alpha=0.90))
            c.roundRect(1.8*cm,3.0*cm,5.0*cm,10.0*cm,0.35*cm,fill=1,stroke=0)
            c.drawImage(chakra_image_path,2.0*cm,3.2*cm,width=4.6*cm,height=9.6*cm,preserveAspectRatio=True,anchor='c')
        # client name
        c.setFillColor(colors.white)
        c.setFont(BOLD_FONT, 26)
        c.drawCentredString(w/2,3.25*cm,client_name)
        c.setFont(REGULAR_FONT, 10)
        # Универсальная формулировка: один и тот же отчёт подходит для женщин и мужчин.
        c.drawCentredString(w/2,2.45*cm,"Персональный профиль")
        c.setFont(REGULAR_FONT, 8)
        c.setFillColor(colors.Color(1,1,1,alpha=0.88))
        c.drawCentredString(w/2,1.35*cm,"Материал предназначен для саморефлексии и не является медицинской,")
        c.drawCentredString(w/2,0.95*cm,"психологической или финансовой диагностикой.")
        c.restoreState()
    return draw

def _card(title, body, accent, width=17.0*cm):
    data=[[Paragraph(_safe(title), ParagraphStyle("ct", fontName=BOLD_FONT,fontSize=10.5,leading=14,textColor=_hex("#243047")))],
          [Paragraph(_safe(body), ParagraphStyle("cb", fontName=REGULAR_FONT,fontSize=9.2,leading=13,textColor=_hex("#4F5561")))]]
    t=Table(data,colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),_hex("#FBFAF7")),
        ("BOX",(0,0),(-1,-1),0.8,_hex(accent)),
        ("LINEBEFORE",(0,0),(0,-1),4,_hex(accent)),
        ("LEFTPADDING",(0,0),(-1,-1),13),
        ("RIGHTPADDING",(0,0),(-1,-1),13),
        ("TOPPADDING",(0,0),(-1,0),10),
        ("BOTTOMPADDING",(0,0),(-1,0),4),
        ("TOPPADDING",(0,1),(-1,1),4),
        ("BOTTOMPADDING",(0,1),(-1,1),10),
    ]))
    return t

def _bullets(items, style):
    return [Paragraph("• " + _safe(x), style) for x in items]

def create_report(uid, name, num, ch, rid, energy_scores=None, sphere_analysis=None, gender="unknown"):
    register_fonts()
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path=os.path.join(REPORTS_DIR,f"report_{uid}_{rid}.pdf")
    client_name=(name or "Клиент").strip()
    accent=CHAKRA_COLORS.get(num,"#6C6F78")

    styles=getSampleStyleSheet()
    title=ParagraphStyle("T",fontName=BOLD_FONT,fontSize=21,leading=26,textColor=_hex("#1C2740"),alignment=TA_CENTER,spaceAfter=10)
    h1=ParagraphStyle("H1",fontName=BOLD_FONT,fontSize=17,leading=21,textColor=_hex("#1C2740"),spaceBefore=5,spaceAfter=8)
    h2=ParagraphStyle("H2",fontName=BOLD_FONT,fontSize=11.5,leading=15,textColor=_hex(accent),spaceBefore=7,spaceAfter=5)
    body=ParagraphStyle("B",fontName=REGULAR_FONT,fontSize=9.4,leading=13.8,textColor=_hex("#414754"),spaceAfter=5)
    small=ParagraphStyle("S",fontName=REGULAR_FONT,fontSize=8.2,leading=11.5,textColor=_hex("#6B6D73"))
    quote=ParagraphStyle("Q",fontName=BOLD_FONT,fontSize=13,leading=18,textColor=_hex("#26324C"),alignment=TA_CENTER,spaceAfter=8)
    center=ParagraphStyle("C",parent=body,alignment=TA_CENTER)

    chakra_image=os.path.join(ASSETS_DIR,"chakras",f"{num:02d}_{CHAKRA_KEYS[num-1]}.jpg")
    cover_bg=os.path.join(COVERS_DIR,"female_background.jpg" if gender=="female" else "male_background.jpg" if gender=="male" else "universal_background.jpg")
    map_path=os.path.join(REPORTS_DIR,f"energy_map_{uid}_{rid}.jpg")
    if energy_scores:
        make_energy_map(map_path,energy_scores,num)

    frame=Frame(1.6*cm,1.55*cm,A4[0]-3.2*cm,A4[1]-3.05*cm,id="normal",leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    doc=BaseDocTemplate(path,pagesize=A4,leftMargin=1.6*cm,rightMargin=1.6*cm,topMargin=1.5*cm,bottomMargin=1.5*cm,title="Персональный энергетический отчёт",author="Chakra Bot")
    doc.addPageTemplates([PageTemplate(id="all",frames=frame,onPage=_footer)])

    story=[]
    # cover is rendered by a dedicated first-page callback
    story.append(Spacer(1,22.8*cm))
    story.append(PageBreak())

    # Main focus
    story += [Paragraph("ВАШ ГЛАВНЫЙ ЭНЕРГЕТИЧЕСКИЙ ФОКУС",title)]
    focus = [
        [Paragraph(f"<font size='34'><b>{num}</b></font>", center)],
        [Paragraph(_safe(ch["name"]), ParagraphStyle("fc",fontName=BOLD_FONT,fontSize=16,leading=20,textColor=_hex(accent),alignment=TA_CENTER))],
        [Paragraph(_safe(ch["question"]), quote)],
        [Paragraph(_safe(ch["responsibility"]), center)]
    ]
    t=Table(focus,colWidths=[16.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),_hex("#F7F5EF")),
        ("BOX",(0,0),(-1,-1),1.1,_hex(accent)),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),16),("RIGHTPADDING",(0,0),(-1,-1),16),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
    ]))
    story += [t,Spacer(1,0.45*cm),_card("Ключевая тема", f"{ch['responsibility']} Этот отчёт помогает увидеть тему ведущей чакры вместе с общей картиной энергокарты.",accent)]
    story += [Spacer(1,0.6*cm),Paragraph("<b>Имя клиента:</b> "+_safe(client_name),body),
              Paragraph("<b>Профиль:</b> персональный, универсальный для женщин и мужчин",body)]

    # Leading chakra
    story += [PageBreak(),Paragraph("1. ВЕДУЩАЯ ЧАКРА — ПОДРОБНЫЙ РАЗБОР",title)]
    if os.path.exists(chakra_image):
        story.append(Image(chakra_image,width=5.0*cm,height=13.5*cm,hAlign="CENTER"))
        story.append(Spacer(1,0.2*cm))
    story.append(Paragraph("Как это может проявляться",h2))
    story.append(Paragraph(_safe(CHAKRA_GUIDANCE[num]["recognition"]),body))
    story.append(Paragraph("Сильные стороны",h2))
    for x in ch["strengths"]: story.append(Paragraph("• "+_safe(x),body))
    story.append(_card("Деньги и реализация",ch["money"],accent))
    story.append(Spacer(1,0.25*cm))
    story.append(Paragraph("Что может мешать доходу",h2))
    for x in (ch["money_risks"] if isinstance(ch["money_risks"],list) else [ch["money_risks"]]): story.append(Paragraph("• "+_safe(x),body))
    story.append(Paragraph("Подходящие направления",h2))
    for x in ch["professions"]: story.append(Paragraph("• "+_safe(x),body))
    story.append(_card("Что лучше избегать",ch["avoid"],accent))

    for sphere,label in [("health","Здоровье и ресурс"),("relationships","Отношения"),("money","Деньги и реализация")]:
        story.append(Paragraph(label,h2))
        for x in CHAKRA_GUIDANCE[num][sphere]: story.append(Paragraph("• "+_safe(x),body))

    story += [PageBreak(),Paragraph("2. ВАША ЛИЧНАЯ ЭНЕРГОКАРТА",title)]
    if os.path.exists(map_path):
        story.append(Image(map_path,width=15.7*cm,height=18.95*cm,hAlign="CENTER"))
    story.append(Paragraph("Показатели отражают субъективную самооценку по 21 утверждению. Чем ниже значение, тем больше внимания методика предлагает направить на соответствующую тему.",small))

    # Seven chakra pages
    for i in range(1,8):
        score=float((energy_scores or {}).get(i,0))
        acc=CHAKRA_COLORS[i]
        story += [PageBreak(),Paragraph(f"{i:02d} · {CHAKRAS[i]['name'].upper()}",title)]
        img=os.path.join(ASSETS_DIR,"chakras",f"{i:02d}_{CHAKRA_KEYS[i-1]}.jpg")
        if os.path.exists(img):
            story.append(Image(img,width=4.4*cm,height=11.0*cm,hAlign="CENTER"))
        story.append(Paragraph(f"Показатель: <b>{score:.2f} / 5</b>",ParagraphStyle("score",parent=body,fontSize=12,textColor=_hex(acc),alignment=TA_CENTER)))
        story.append(_card("Ответственность чакры",CHAKRAS[i]["responsibility"],acc))
        if score < 2.5:
            status="ЗОНА ВНИМАНИЯ"
            recs=CHAKRA_GUIDANCE[i]["health"][:2]+CHAKRA_GUIDANCE[i]["relationships"][:1]+CHAKRA_GUIDANCE[i]["money"][:1]
        elif score < 3.8:
            status="ЗОНА БАЛАНСА"
            recs=CHAKRAS[i]["recovery"][:3]
        else:
            status="РЕСУРСНАЯ ЗОНА"
            recs=CHAKRAS[i]["recovery"][:3]
        story.append(Paragraph(status,h2))
        for x in recs: story.append(Paragraph("• "+_safe(x),body))

    # Top growth
    story += [PageBreak(),Paragraph("ВАШИ ТРИ ГЛАВНЫЕ ТОЧКИ РОСТА",title)]
    ranked=sorted(range(1,8), key=lambda i: float((energy_scores or {}).get(i,0)))
    for idx,i in enumerate(ranked[:3],1):
        score=float((energy_scores or {}).get(i,0))
        story.append(_card(f"{idx:02d} · {CHAKRAS[i]['name']} · {score:.2f}/5", CHAKRA_GUIDANCE[i]["recognition"], CHAKRA_COLORS[i]))
        story.append(Spacer(1,0.25*cm))

    # Sphere analysis
    if sphere_analysis:
        story += [PageBreak(),Paragraph("АНАЛИЗ СФЕР ЖИЗНИ",title)]
        for key,label in [("health","Здоровье и ресурс"),("relationships","Отношения"),("money","Деньги и реализация")]:
            item=sphere_analysis[key]
            acc={"health":"#4F9D69","relationships":"#C66A86","money":"#C29A39"}[key]
            story.append(_card(f"{label} · {item['score']}/5 · {item['level']}",
                               f"Опора: {', '.join(CHAKRAS[c]['name'] for c in item['strongest'])}. Зона внимания: {', '.join(CHAKRAS[c]['name'] for c in item['weakest'])}.",
                               acc))
            recs=[]
            for c in item["weakest"]: recs.extend(CHAKRA_GUIDANCE[c][key])
            story.append(Paragraph("Что поможет",h2))
            for x in recs[:4]: story.append(Paragraph("• "+_safe(x),body))
            story.append(Spacer(1,0.25*cm))

    story += [PageBreak(),Paragraph("ВАШ ГЛАВНЫЙ ВЫВОД",title)]
    weakest=ranked[:2] if ranked else [num]
    names=", ".join(CHAKRAS[i]["name"] for i in weakest)
    conclusion=(f"{client_name}, ваша энергокарта предлагает обратить особое внимание на темы {names}. "
                f"Ведущая чакра — {CHAKRAS[num]['name']}: начните не с попытки изменить всё сразу, "
                f"а с одного небольшого действия, которое возвращает ощущение опоры и ясности.")
    story.append(_card("Следующий шаг",conclusion,accent))
    story.append(Spacer(1,0.6*cm))
    story.append(Paragraph("НА ЭТУ НЕДЕЛЮ",h2))
    for x in ["Выберите одну зону внимания.","Выберите одно конкретное действие.","Наблюдайте за состоянием без оценки.","Через неделю сравните ощущения и при желании повторите энергокарту."]:
        story.append(Paragraph("□ "+_safe(x),body))

    story += [PageBreak(),Paragraph("КАК ПОЛЬЗОВАТЬСЯ ОТЧЁТОМ",title)]
    story.append(Paragraph("Отчёт создан как инструмент саморефлексии. Используйте его для наблюдения за своими состояниями, выбора небольших практических шагов и повторной оценки динамики.",body))
    story.append(Paragraph("Ограничения методики",h1))
    story.append(Paragraph("Материал не является медицинской, психологической или финансовой диагностикой. Описания сфер жизни и рекомендации не заменяют профессиональную помощь специалиста.",small))
    story.append(Spacer(1,1.2*cm))
    story.append(Paragraph("Ваш путь не требует спешки.",quote))
    story.append(Paragraph("Начните с одной небольшой перемены. Наблюдайте за собой и возвращайтесь к себе снова.",center))

    # Need first page callback with cover.
    cover_draw = _cover_page(cover_bg, chakra_image, client_name, gender, ch)
    def draw_page(c, d):
        if d.page == 1:
            cover_draw(c, d)
        else:
            _footer(c, d)
    doc.pageTemplates[0].onPage = draw_page
    doc.build(story)
    return path
