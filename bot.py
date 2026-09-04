import os
from collections import Counter
from dotenv import load_dotenv
import telebot
from telebot import types
from data import CHAKRAS,QUESTIONS
from database import *
from report_generator import create_report

load_dotenv(); TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN: raise RuntimeError("Создайте .env и укажите TELEGRAM_BOT_TOKEN")
ADMINS={int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()}
bot=telebot.TeleBot(TOKEN); create_tables(); sessions={}

def menu():
 m=types.ReplyKeyboardMarkup(resize_keyboard=True)
 m.row("🔮 Пройти тест","📊 Мой результат");m.row("📜 История","💎 Мои отчёты");m.row("ℹ️ О методике");return m
def result_buttons(rid):
 m=types.InlineKeyboardMarkup();m.add(types.InlineKeyboardButton("💎 Получить расширенный PDF",callback_data=f"pdf:{rid}"));m.add(types.InlineKeyboardButton("📖 Подробнее",callback_data=f"detail:{rid}"));return m
@bot.message_handler(commands=["start"])
def start(x): save_user(x.from_user);bot.send_message(x.chat.id,"✨ Добро пожаловать! Пройдите тест из 7 вопросов и узнайте свою ведущую чакру.",reply_markup=menu())
@bot.message_handler(func=lambda x:x.text=="🔮 Пройти тест")
def test(x): sessions[x.from_user.id]={"i":0,"scores":Counter()};ask(x.chat.id,x.from_user.id)
def ask(chat,uid):
 s=sessions[uid]
 if s["i"]>=len(QUESTIONS):
  scores=s["scores"]; maxv=max(scores.values()); leaders=[k for k,v in scores.items() if v==maxv];ch=max(leaders);rid=save_result(uid,ch,dict(scores));del sessions[uid];c=CHAKRAS[ch]
  return bot.send_message(chat,f"✨ <b>Ваш результат: {c['name']}</b>\\n📍 {c['location']}\\n❓ «{c['question']}»\\n\\n{c['responsibility']}",parse_mode="HTML",reply_markup=result_buttons(rid))
 q=QUESTIONS[s["i"]];m=types.InlineKeyboardMarkup()
 for o in q["options"]:m.add(types.InlineKeyboardButton(o["text"],callback_data=f"a:{o['chakra']}"))
 bot.send_message(chat,f"🔮 Вопрос {s['i']+1}/7\\n\\n{q['question']}",reply_markup=m)
@bot.callback_query_handler(func=lambda c:c.data.startswith("a:"))
def ans(c):
 if c.from_user.id not in sessions:return bot.answer_callback_query(c.id,"Начните тест заново")
 s=sessions[c.from_user.id];s["scores"][int(c.data.split(":")[1])]+=1;s["i"]+=1;bot.answer_callback_query(c.id);ask(c.message.chat.id,c.from_user.id)
@bot.callback_query_handler(func=lambda c:c.data.startswith("detail:"))
def detail(c):
 r=get_result(c.from_user.id,int(c.data.split(":")[1]))
 if not r:return
 d=CHAKRAS[r[1]];text=f"<b>{d['name']}</b>\\n\\n<b>Сильные стороны:</b>\\n"+"\\n".join("• "+x for x in d["strengths"])+"\\n\\n<b>Деньги:</b>\\n"+d["money"]+"\\n\\n<b>Профессии:</b>\\n"+"\\n".join("• "+x for x in d["professions"])
 bot.send_message(c.message.chat.id,text,parse_mode="HTML")
@bot.message_handler(func=lambda x:x.text=="📊 Мой результат")
def last(x):
 r=get_last(x.from_user.id)
 if not r:return bot.send_message(x.chat.id,"Сначала пройдите тест.")
 c=CHAKRAS[r[1]];bot.send_message(x.chat.id,f"Ваш результат: {c['name']}\\n{c['question']}",reply_markup=result_buttons(r[0]))
@bot.message_handler(func=lambda x:x.text=="📜 История")
def hist(x):
 rows=history(x.from_user.id)
 if not rows:return bot.send_message(x.chat.id,"История пока пуста.")
 m=types.InlineKeyboardMarkup()
 for rid,ch,dt in rows:m.add(types.InlineKeyboardButton(f"{CHAKRAS[ch]['name']} — {dt[:10]}",callback_data=f"detail:{rid}"))
 bot.send_message(x.chat.id,"📜 История результатов:",reply_markup=m)
@bot.callback_query_handler(func=lambda c:c.data.startswith("pdf:"))
def pdf(c):
 rid=int(c.data.split(":")[1]);r=get_result(c.from_user.id,rid)
 if not r:return
 old=get_report(c.from_user.id,rid)
 try:
  path=old[0] if old and os.path.exists(old[0]) else create_report(c.from_user.id,c.from_user.first_name,r[1],CHAKRAS[r[1]],rid)
  save_report(c.from_user.id,rid,path)
  with open(path,"rb") as f:bot.send_document(c.message.chat.id,f,caption="💎 Ваш персональный расширенный отчёт")
 except Exception as e:bot.send_message(c.message.chat.id,f"Ошибка создания PDF: {e}")
@bot.message_handler(func=lambda x:x.text=="💎 Мои отчёты")
def reports(x):
 rows=history(x.from_user.id);m=types.InlineKeyboardMarkup();n=0
 for rid,ch,dt in rows:
  if get_report(x.from_user.id,rid):m.add(types.InlineKeyboardButton(f"📄 {CHAKRAS[ch]['name']} — {dt[:10]}",callback_data=f"pdf:{rid}"));n+=1
 bot.send_message(x.chat.id,"💎 Ваши отчёты:" if n else "Пока нет созданных расширенных отчётов.",reply_markup=m if n else None)
@bot.message_handler(func=lambda x:x.text=="ℹ️ О методике")
def about(x):bot.send_message(x.chat.id,"Методика использует 7 вопросов. Преобладающий вариант определяет ведущую чакру; при равенстве выбирается чакра с большим номером. Материалы предназначены для саморефлексии.")
@bot.message_handler(commands=["admin"])
def admin(x):
 if x.from_user.id not in ADMINS:return
 u,r,d=stats();text=f"⚙️ Админ-панель\\n👥 Пользователей: {u}\\n🔮 Результатов: {r}\\n\\n"+"\\n".join(f"{CHAKRAS[i]['name']}: {d.get(i,0)}" for i in range(1,8));bot.send_message(x.chat.id,text)
print("Bot started");bot.infinity_polling(skip_pending=True)
