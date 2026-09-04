import os
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
def create_report(uid,name,num,ch,rid):
 os.makedirs("reports",exist_ok=True); path=f"reports/report_{uid}_{rid}.pdf"
 s=getSampleStyleSheet(); title=ParagraphStyle("T",parent=s["Title"],alignment=TA_CENTER,fontSize=25,leading=32); h=ParagraphStyle("H",parent=s["Heading1"],fontSize=18,leading=24); b=ParagraphStyle("B",parent=s["BodyText"],fontSize=10.5,leading=16)
 story=[]; img=f"images/chakra_{num}.jpg"
 if os.path.exists(img): story.append(Image(img,width=10*cm,height=10*cm))
 story += [Spacer(1,1*cm),Paragraph("ПЕРСОНАЛЬНЫЙ ЭНЕРГЕТИЧЕСКИЙ ОТЧЁТ",title),Spacer(1,1*cm),Paragraph(name or "Пользователь",b),Paragraph(ch["name"],h),Paragraph(ch["question"],b),PageBreak()]
 sections=[("О вашей ведущей чакре",[ch["responsibility"]]),("Сильные стороны",ch["strengths"]),("Стратегия заработка",[ch["money"]]),("Что может мешать доходу",ch["money_risks"]),("Подходящие направления и профессии",ch["professions"]),("Что лучше избегать",[ch["avoid"]]),("Когда ресурс снижается",ch["minus"]),("Рекомендации и хобби",ch["recovery"])]
 for title,items in sections:
  story.append(Paragraph(title,h))
  for x in items: story.append(Paragraph("• "+x,b))
  story.append(Spacer(1,.5*cm))
 story += [PageBreak(),Paragraph("Важно",h),Paragraph("Материалы отчёта основаны на предоставленной методике и предназначены для саморефлексии. Они не являются медицинской, психологической или финансовой диагностикой.",b)]
 SimpleDocTemplate(path,pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,topMargin=2*cm,bottomMargin=2*cm).build(story);return path
