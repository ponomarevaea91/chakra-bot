import os
import json
from collections import Counter, defaultdict
from dotenv import load_dotenv
import telebot
from telebot import types

from data import CHAKRAS, QUESTIONS, ENERGY_QUESTIONS, ENERGY_LEVELS
from database import *
from report_generator import create_report
from analysis_service import sphere_text, analyze_spheres
from funnel_service import FUNNEL_MESSAGES

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задана переменная TELEGRAM_BOT_TOKEN")

ADMINS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://instagram.com/ponomareva_elen")
PAYMENT_TOKEN = os.getenv("TELEGRAM_PAYMENT_PROVIDER_TOKEN", "")
PREMIUM_PRICE = int(os.getenv("PREMIUM_PRICE", "99000"))  # копейки
PREMIUM_CURRENCY = os.getenv("PREMIUM_CURRENCY", "RUB")

bot = telebot.TeleBot(TOKEN)
create_tables()
sessions = {}
energy_sessions = {}


def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔮 Пройти тест", "🗺 Энергокарта")
    markup.row("📊 Мой результат", "🌿 Рекомендации")
    markup.row("❤️ Сферы жизни", "📜 История")
    markup.row("💎 Мои отчёты", "📅 Консультация")
    markup.row("ℹ️ О методике")
    return markup


def consultation_button():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📅 Записаться на консультацию", url=INSTAGRAM_URL))
    return markup


def result_buttons(result_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🌿 Как вывести в плюс", callback_data=f"plus:{result_id}"))
    markup.add(types.InlineKeyboardButton("💎 Расширенный PDF", callback_data=f"pdf:{result_id}"))
    markup.add(types.InlineKeyboardButton("📖 Подробнее", callback_data=f"detail:{result_id}"))
    markup.add(types.InlineKeyboardButton("📅 Консультация", url=INSTAGRAM_URL))
    return markup


def short_label(text, limit=52):
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit - 1]) + "…"


def chakra_recommendations(chakra):
    return (
        f"🌿 <b>Как перевести {chakra['name']} из минуса в плюс</b>\n\n"
        "<b>Признаки минуса:</b>\n" + "\n".join(f"• {item}" for item in chakra["minus"])
        + "\n\n<b>Практика восстановления:</b>\n" + "\n".join(f"✓ {item}" for item in chakra["recovery"])
        + "\n\n<b>Смысл движения в плюс:</b>\n"
        + f"Развивать качества: {', '.join(chakra['strengths'][:3]).lower()}.\n\n"
        + "Начните с одного небольшого действия в день и наблюдайте за своим состоянием."
    )


@bot.message_handler(commands=["start"])
def start(message):
    save_user(message.from_user)
    bot.send_message(message.chat.id,
        "✨ Добро пожаловать! Здесь есть тест на ведущую чакру, энергокарта всех 7 чакр, рекомендации и расширенный отчёт.",
        reply_markup=menu())


# ---------------- ТЕСТ ----------------
@bot.message_handler(func=lambda m: m.text == "🔮 Пройти тест")
def test(message):
    sessions[message.from_user.id] = {"i": 0, "scores": Counter()}
    ask(message.chat.id, message.from_user.id)


def ask(chat_id, user_id):
    session = sessions[user_id]
    if session["i"] >= len(QUESTIONS):
        scores = session["scores"]
        max_score = max(scores.values())
        leaders = [chakra for chakra, score in scores.items() if score == max_score]
        chakra_number = max(leaders)
        result_id = save_result(user_id, chakra_number, dict(scores))
        del sessions[user_id]
        chakra = CHAKRAS[chakra_number]
        text = (f"✨ <b>Ваш результат: {chakra['name']}</b>\n"
                f"📍 {chakra['location']}\n"
                f"❓ «{chakra['question']}»\n\n"
                f"{chakra['responsibility']}\n\n"
                "🌿 Нажмите «Как вывести в плюс», чтобы получить рекомендации.")
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=result_buttons(result_id))
        set_funnel_step(user_id, 1)
        return

    question = QUESTIONS[session["i"]]
    markup = types.InlineKeyboardMarkup()
    for option in question["options"]:
        markup.add(types.InlineKeyboardButton(short_label(option["text"]), callback_data=f"a:{option['chakra']}"))
    bot.send_message(chat_id, f"🔮 <b>Вопрос {session['i'] + 1}/{len(QUESTIONS)}</b>\n\n{question['question']}", parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("a:"))
def answer(call):
    if call.from_user.id not in sessions:
        return bot.answer_callback_query(call.id, "Начните тест заново")
    session = sessions[call.from_user.id]
    session["scores"][int(call.data.split(":")[1])] += 1
    session["i"] += 1
    bot.answer_callback_query(call.id)
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception: pass
    ask(call.message.chat.id, call.from_user.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("plus:"))
def plus_recommendations(call):
    result = get_result(call.from_user.id, int(call.data.split(":")[1]))
    if not result: return bot.answer_callback_query(call.id, "Результат не найден")
    bot.send_message(call.message.chat.id, chakra_recommendations(CHAKRAS[result[1]]), parse_mode="HTML", reply_markup=consultation_button())


@bot.message_handler(func=lambda m: m.text in ("🌿 Рекомендации", "🌿 Мои рекомендации"))
def my_recommendations(message):
    result = get_last(message.from_user.id)
    if not result: return bot.send_message(message.chat.id, "Сначала пройдите тест, чтобы получить рекомендации.")
    bot.send_message(message.chat.id, chakra_recommendations(CHAKRAS[result[1]]), parse_mode="HTML", reply_markup=consultation_button())


@bot.callback_query_handler(func=lambda c: c.data.startswith("detail:"))
def detail(call):
    result = get_result(call.from_user.id, int(call.data.split(":")[1]))
    if not result: return
    chakra = CHAKRAS[result[1]]
    text = (f"<b>{chakra['name']}</b>\n\n<b>Сильные стороны:</b>\n" + "\n".join("• " + x for x in chakra["strengths"])
            + "\n\n<b>Деньги:</b>\n" + chakra["money"]
            + "\n\n<b>Профессии:</b>\n" + "\n".join("• " + x for x in chakra["professions"]))
    bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=consultation_button())


@bot.message_handler(func=lambda m: m.text == "📊 Мой результат")
def last_result(message):
    result = get_last(message.from_user.id)
    if not result: return bot.send_message(message.chat.id, "Сначала пройдите тест.")
    chakra = CHAKRAS[result[1]]
    bot.send_message(message.chat.id, f"✨ Ваш результат: {chakra['name']}\n❓ «{chakra['question']}»", reply_markup=result_buttons(result[0]))


# ---------------- ЭНЕРГОКАРТА ----------------
@bot.message_handler(func=lambda m: m.text == "🗺 Энергокарта")
def start_energy_map(message):
    energy_sessions[message.from_user.id] = {"i": 0, "answers": []}
    bot.send_message(message.chat.id,
        "🗺 <b>Личная энергокарта</b>\n\n21 утверждение: по 3 для каждой чакры. Оценивайте от 1 до 5.\n\n1 — совсем не про меня\n5 — полностью про меня\n\nЭто инструмент саморефлексии.", parse_mode="HTML")
    ask_energy_question(message.chat.id, message.from_user.id)


def ask_energy_question(chat_id, user_id):
    session = energy_sessions[user_id]
    if session["i"] >= len(ENERGY_QUESTIONS): return finish_energy_map(chat_id, user_id)
    chakra_number, question = ENERGY_QUESTIONS[session["i"]]
    markup = types.InlineKeyboardMarkup(row_width=5)
    markup.row(*[types.InlineKeyboardButton(str(score), callback_data=f"e:{score}") for score in range(1, 6)])
    bot.send_message(chat_id,
        f"🗺 <b>Энергокарта — {session['i'] + 1}/{len(ENERGY_QUESTIONS)}</b>\n{CHAKRAS[chakra_number]['name']}\n\n{question}",
        parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("e:"))
def energy_answer(call):
    if call.from_user.id not in energy_sessions: return bot.answer_callback_query(call.id, "Начните энергокарту заново")
    session = energy_sessions[call.from_user.id]
    chakra_number, _ = ENERGY_QUESTIONS[session["i"]]
    score = int(call.data.split(":")[1])
    session["answers"].append((chakra_number, score)); session["i"] += 1
    bot.answer_callback_query(call.id, f"Оценка: {score}")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception: pass
    ask_energy_question(call.message.chat.id, call.from_user.id)


def energy_level(avg):
    return "minus" if avg < 2.5 else "balance" if avg < 3.8 else "plus"


def finish_energy_map(chat_id, user_id):
    session = energy_sessions[user_id]
    grouped = defaultdict(list)
    for chakra_number, score in session["answers"]: grouped[chakra_number].append(score)
    scores = {chakra: round(sum(values) / len(values), 2) for chakra, values in grouped.items()}
    save_energy_map(user_id, scores); del energy_sessions[user_id]

    lines = ["🗺 <b>Ваша личная энергокарта</b>"]
    low = []
    for chakra_number in range(1, 8):
        score = scores.get(chakra_number, 0); key = energy_level(score); level_name, _ = ENERGY_LEVELS[key]
        bar = "🟣" * round(score) + "⚪" * (5 - round(score))
        lines.append(f"\n<b>{CHAKRAS[chakra_number]['name']}</b>: {score}/5 {bar}\n{level_name}")
        if key == "minus": low.append(chakra_number)

    lines.append("\n<b>Первые шаги:</b>")
    if low:
        for n in low[:3]:
            lines.append(f"🌿 {CHAKRAS[n]['name']}: {CHAKRAS[n]['recovery'][0]}")
    else:
        lines.append("Поддерживайте текущий баланс небольшими регулярными практиками.")
    bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")
    bot.send_message(chat_id, sphere_text(scores), parse_mode="HTML", reply_markup=consultation_button())
    set_funnel_step(user_id, 2)


@bot.message_handler(func=lambda m: m.text == "❤️ Сферы жизни")
def life_spheres(message):
    row = get_last_energy_map(message.from_user.id)
    if not row: return bot.send_message(message.chat.id, "Сначала пройдите 🗺 Энергокарту — тогда я смогу сформировать анализ трёх сфер.")
    scores = {int(k): float(v) for k, v in json.loads(row[1]).items()}
    bot.send_message(message.chat.id, sphere_text(scores), parse_mode="HTML", reply_markup=consultation_button())


# ---------------- PDF И ОПЛАТА ----------------
def send_report(chat_id, user_id, result_id, name):
    result = get_result(user_id, result_id)
    if not result: return bot.send_message(chat_id, "Результат не найден.")
    energy_row = get_last_energy_map(user_id)
    energy_scores = None
    if energy_row:
        energy_scores = {int(k): float(v) for k, v in json.loads(energy_row[1]).items()}
    path = create_report(user_id, name or "Пользователь", result[1], CHAKRAS[result[1]], result_id, energy_scores, analyze_spheres(energy_scores) if energy_scores else None)
    save_report(user_id, result_id, path)
    with open(path, "rb") as f: bot.send_document(chat_id, f, caption="💎 Ваш персональный расширенный отчёт")


@bot.callback_query_handler(func=lambda c: c.data.startswith("pdf:"))
def pdf(call):
    result_id = int(call.data.split(":")[1])
    if get_report(call.from_user.id, result_id) or has_paid(call.from_user.id, result_id):
        try: send_report(call.message.chat.id, call.from_user.id, result_id, call.from_user.first_name)
        except Exception as error: bot.send_message(call.message.chat.id, f"Ошибка создания PDF: {error}")
        return
    if not PAYMENT_TOKEN:
        return bot.send_message(call.message.chat.id, "Оплата ещё не подключена. Добавьте TELEGRAM_PAYMENT_PROVIDER_TOKEN в Railway Variables, после чего PDF будет выдаваться автоматически после оплаты.")
    prices = [types.LabeledPrice(label="Расширенный энергетический отчёт", amount=PREMIUM_PRICE)]
    bot.send_invoice(call.message.chat.id, "Расширенный энергетический отчёт", "Персональный PDF с результатом, энергокартой и рекомендациями", f"report:{result_id}", PAYMENT_TOKEN, PREMIUM_CURRENCY, prices)


@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def successful_payment(message):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("report:"): return
    result_id = int(payload.split(":", 1)[1])
    save_payment(message.from_user.id, result_id, message.successful_payment.total_amount, message.successful_payment.currency)
    try: send_report(message.chat.id, message.from_user.id, result_id, message.from_user.first_name)
    except Exception as error: bot.send_message(message.chat.id, f"Оплата получена, но PDF временно не создан: {error}")


@bot.message_handler(func=lambda m: m.text == "💎 Мои отчёты")
def reports(message):
    rows = history(message.from_user.id); markup = types.InlineKeyboardMarkup(); count = 0
    for result_id, chakra_number, created_at in rows:
        if get_report(message.from_user.id, result_id) or has_paid(message.from_user.id, result_id):
            markup.add(types.InlineKeyboardButton(f"📄 {CHAKRAS[chakra_number]['name']} — {created_at[:10]}", callback_data=f"pdf:{result_id}")); count += 1
    bot.send_message(message.chat.id, "💎 Ваши отчёты:" if count else "Пока нет доступных расширенных отчётов.", reply_markup=markup if count else None)


# ---------------- ИСТОРИЯ, ВОРОНКА, КОНСУЛЬТАЦИЯ ----------------
@bot.message_handler(func=lambda m: m.text == "📜 История")
def show_history(message):
    rows = history(message.from_user.id)
    if not rows: return bot.send_message(message.chat.id, "История пока пуста.")
    markup = types.InlineKeyboardMarkup()
    for result_id, chakra_number, created_at in rows:
        markup.add(types.InlineKeyboardButton(f"{CHAKRAS[chakra_number]['name']} — {created_at[:10]}", callback_data=f"detail:{result_id}"))
    bot.send_message(message.chat.id, "📜 История результатов:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "📅 Консультация")
def consultation(message):
    bot.send_message(message.chat.id, "📅 Запись на консультацию к энерготерапевту:", reply_markup=consultation_button())


@bot.message_handler(commands=["продолжить", "funnel"])
def funnel(message):
    for text in FUNNEL_MESSAGES: bot.send_message(message.chat.id, text)
    bot.send_message(message.chat.id, "Если хотите разобрать результат глубже — можно записаться на консультацию.", reply_markup=consultation_button())


@bot.message_handler(func=lambda m: m.text == "ℹ️ О методике")
def about(message):
    bot.send_message(message.chat.id,
        "Методика использует два инструмента саморефлексии:\n\n🔮 Тест на ведущую чакру — показывает наиболее выраженную тему.\n🗺 Энергокарта — помогает оценить субъективное состояние всех 7 чакр по шкале 1–5.\n\nМатериалы не являются медицинской, психологической или финансовой диагностикой.")


@bot.message_handler(commands=["admin"])
def admin(message):
    if message.from_user.id not in ADMINS: return
    users, results, distribution = stats()
    text = f"⚙️ Админ-панель\n👥 Пользователей: {users}\n🔮 Результатов: {results}\n\n" + "\n".join(f"{CHAKRAS[i]['name']}: {distribution.get(i, 0)}" for i in range(1, 8))
    bot.send_message(message.chat.id, text)


print("Bot started")
bot.infinity_polling(skip_pending=True)
