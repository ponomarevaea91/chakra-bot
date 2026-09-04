import os
import json
from collections import Counter, defaultdict
from dotenv import load_dotenv
import telebot
from telebot import types

from data import CHAKRAS, QUESTIONS, ENERGY_QUESTIONS, ENERGY_LEVELS
from database import *
from report_generator import create_report

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задана переменная окружения TELEGRAM_BOT_TOKEN. Добавьте её в Railway Variables.")

ADMINS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
bot = telebot.TeleBot(TOKEN)
create_tables()
sessions = {}
energy_sessions = {}


def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔮 Пройти тест", "🗺 Энергокарта")
    markup.row("📊 Мой результат", "🌿 Мои рекомендации")
    markup.row("📜 История", "💎 Мои отчёты")
    markup.row("ℹ️ О методике")
    return markup


def result_buttons(result_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🌿 Как вывести в плюс", callback_data=f"plus:{result_id}"))
    markup.add(types.InlineKeyboardButton("💎 Получить расширенный PDF", callback_data=f"pdf:{result_id}"))
    markup.add(types.InlineKeyboardButton("📖 Подробнее", callback_data=f"detail:{result_id}"))
    return markup


def chakra_recommendations(chakra):
    return (
        f"🌿 <b>Как перевести {chakra['name']} из минуса в плюс</b>\n\n"
        f"<b>Признаки минуса:</b>\n"
        + "\n".join(f"• {item}" for item in chakra["minus"])
        + "\n\n<b>Практика восстановления:</b>\n"
        + "\n".join(f"✓ {item}" for item in chakra["recovery"])
        + "\n\n<b>Смысл движения в плюс:</b>\n"
        + f"Развивать качества: {', '.join(chakra['strengths'][:3]).lower()}.\n\n"
        + "Начните с одного небольшого действия в день и наблюдайте за своим состоянием."
    )


@bot.message_handler(commands=["start"])
def start(message):
    save_user(message.from_user)
    bot.send_message(
        message.chat.id,
        "✨ Добро пожаловать! Здесь можно пройти тест на ведущую чакру, получить рекомендации и составить личную энергокарту.",
        reply_markup=menu(),
    )


@bot.message_handler(func=lambda message: message.text == "🔮 Пройти тест")
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
        text = (
            f"✨ <b>Ваш результат: {chakra['name']}</b>\n"
            f"📍 {chakra['location']}\n"
            f"❓ «{chakra['question']}»\n\n"
            f"{chakra['responsibility']}\n\n"
            "🌿 Нажмите «Как вывести в плюс», чтобы получить персональные рекомендации."
        )
        return bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=result_buttons(result_id))

    question = QUESTIONS[session["i"]]
    markup = types.InlineKeyboardMarkup()
    for option in question["options"]:
        markup.add(types.InlineKeyboardButton(option["text"], callback_data=f"a:{option['chakra']}"))
    bot.send_message(chat_id, f"🔮 Вопрос {session['i'] + 1}/{len(QUESTIONS)}\n\n{question['question']}", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("a:"))
def answer(call):
    if call.from_user.id not in sessions:
        return bot.answer_callback_query(call.id, "Начните тест заново")
    session = sessions[call.from_user.id]
    session["scores"][int(call.data.split(":")[1])] += 1
    session["i"] += 1
    bot.answer_callback_query(call.id)
    ask(call.message.chat.id, call.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("plus:"))
def plus_recommendations(call):
    result = get_result(call.from_user.id, int(call.data.split(":")[1]))
    if not result:
        return bot.answer_callback_query(call.id, "Результат не найден")
    bot.send_message(call.message.chat.id, chakra_recommendations(CHAKRAS[result[1]]), parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text == "🌿 Мои рекомендации")
def my_recommendations(message):
    result = get_last(message.from_user.id)
    if not result:
        return bot.send_message(message.chat.id, "Сначала пройдите тест, чтобы получить рекомендации для вашей ведущей чакры.")
    bot.send_message(message.chat.id, chakra_recommendations(CHAKRAS[result[1]]), parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith("detail:"))
def detail(call):
    result = get_result(call.from_user.id, int(call.data.split(":")[1]))
    if not result:
        return
    chakra = CHAKRAS[result[1]]
    text = (
        f"<b>{chakra['name']}</b>\n\n"
        "<b>Сильные стороны:</b>\n"
        + "\n".join("• " + item for item in chakra["strengths"])
        + "\n\n<b>Деньги:</b>\n" + chakra["money"]
        + "\n\n<b>Профессии:</b>\n" + "\n".join("• " + item for item in chakra["professions"])
    )
    bot.send_message(call.message.chat.id, text, parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text == "📊 Мой результат")
def last_result(message):
    result = get_last(message.from_user.id)
    if not result:
        return bot.send_message(message.chat.id, "Сначала пройдите тест.")
    chakra = CHAKRAS[result[1]]
    bot.send_message(message.chat.id, f"Ваш результат: {chakra['name']}\n{chakra['question']}", reply_markup=result_buttons(result[0]))


# ---------------- ЭНЕРГОКАРТА ----------------
@bot.message_handler(func=lambda message: message.text == "🗺 Энергокарта")
def start_energy_map(message):
    energy_sessions[message.from_user.id] = {"i": 0, "answers": []}
    bot.send_message(
        message.chat.id,
        "🗺 <b>Личная энергокарта</b>\n\nВам будет предложено 21 утверждение — по 3 для каждой чакры. Оценивайте каждое от 1 до 5:\n\n1 — совсем не про меня\n2 — скорее нет\n3 — частично\n4 — в основном да\n5 — полностью про меня\n\nЭто инструмент саморефлексии, а не медицинская диагностика.",
        parse_mode="HTML",
    )
    ask_energy_question(message.chat.id, message.from_user.id)


def ask_energy_question(chat_id, user_id):
    session = energy_sessions[user_id]
    if session["i"] >= len(ENERGY_QUESTIONS):
        return finish_energy_map(chat_id, user_id)
    chakra_number, question = ENERGY_QUESTIONS[session["i"]]
    markup = types.InlineKeyboardMarkup(row_width=5)
    for score in range(1, 6):
        markup.add(types.InlineKeyboardButton(str(score), callback_data=f"e:{score}"))
    bot.send_message(
        chat_id,
        f"🗺 <b>Энергокарта — {session['i'] + 1}/{len(ENERGY_QUESTIONS)}</b>\n"
        f"{CHAKRAS[chakra_number]['name']}\n\n{question}\n\nВыберите оценку от 1 до 5:",
        parse_mode="HTML",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("e:"))
def energy_answer(call):
    if call.from_user.id not in energy_sessions:
        return bot.answer_callback_query(call.id, "Начните энергокарту заново")
    session = energy_sessions[call.from_user.id]
    chakra_number, _ = ENERGY_QUESTIONS[session["i"]]
    score = int(call.data.split(":")[1])
    session["answers"].append((chakra_number, score))
    session["i"] += 1
    bot.answer_callback_query(call.id, f"Оценка: {score}")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    ask_energy_question(call.message.chat.id, call.from_user.id)


def energy_level(avg):
    if avg < 2.5:
        return "minus"
    if avg < 3.8:
        return "balance"
    return "plus"


def finish_energy_map(chat_id, user_id):
    session = energy_sessions[user_id]
    grouped = defaultdict(list)
    for chakra_number, score in session["answers"]:
        grouped[chakra_number].append(score)
    scores = {chakra: round(sum(values) / len(values), 2) for chakra, values in grouped.items()}
    save_energy_map(user_id, scores)
    del energy_sessions[user_id]

    lines = ["🗺 <b>Ваша личная энергокарта</b>\n"]
    for chakra_number in range(1, 8):
        score = scores.get(chakra_number, 0)
        level_key = energy_level(score)
        level_name, _ = ENERGY_LEVELS[level_key]
        filled = round(score)
        bar = "🟣" * filled + "⚪" * (5 - filled)
        lines.append(f"<b>{CHAKRAS[chakra_number]['name']}</b>: {score}/5 {bar}\n{level_name}")

    low = [number for number, score in scores.items() if energy_level(score) == "minus"]
    balance = [number for number, score in scores.items() if energy_level(score) == "balance"]
    lines.append("\n<b>Что делать дальше:</b>")
    if low:
        lines.append("В первую очередь уделите внимание: " + ", ".join(CHAKRAS[n]["name"] for n in low) + ".")
        for number in low[:3]:
            lines.append(f"\n🌿 <b>{CHAKRAS[number]['name']}</b> — первый шаг:")
            lines.append("• " + CHAKRAS[number]["recovery"][0])
            lines.append("• " + CHAKRAS[number]["recovery"][1])
    elif balance:
        lines.append("У вас нет ярко выраженных зон минуса. Поддерживайте чакры в балансе небольшими регулярными практиками.")
    else:
        lines.append("По этой саморефлексивной анкете все зоны находятся в выраженном ресурсе. Поддерживайте баланс и наблюдайте за изменениями состояния.")

    bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text == "📜 История")
def show_history(message):
    rows = history(message.from_user.id)
    if not rows:
        return bot.send_message(message.chat.id, "История пока пуста.")
    markup = types.InlineKeyboardMarkup()
    for result_id, chakra_number, created_at in rows:
        markup.add(types.InlineKeyboardButton(f"{CHAKRAS[chakra_number]['name']} — {created_at[:10]}", callback_data=f"detail:{result_id}"))
    bot.send_message(message.chat.id, "📜 История результатов:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("pdf:"))
def pdf(call):
    result_id = int(call.data.split(":")[1])
    result = get_result(call.from_user.id, result_id)
    if not result:
        return
    try:
        # Каждый раз создаём свежий PDF: так не отправляется старый файл со сломанными шрифтами.
        path = create_report(call.from_user.id, call.from_user.first_name, result[1], CHAKRAS[result[1]], result_id)
        save_report(call.from_user.id, result_id, path)
        with open(path, "rb") as report_file:
            bot.send_document(call.message.chat.id, report_file, caption="💎 Ваш персональный расширенный отчёт")
    except Exception as error:
        bot.send_message(call.message.chat.id, f"Ошибка создания PDF: {error}")


@bot.message_handler(func=lambda message: message.text == "💎 Мои отчёты")
def reports(message):
    rows = history(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    count = 0
    for result_id, chakra_number, created_at in rows:
        if get_report(message.from_user.id, result_id):
            markup.add(types.InlineKeyboardButton(f"📄 {CHAKRAS[chakra_number]['name']} — {created_at[:10]}", callback_data=f"pdf:{result_id}"))
            count += 1
    bot.send_message(message.chat.id, "💎 Ваши отчёты:" if count else "Пока нет созданных расширенных отчётов.", reply_markup=markup if count else None)


@bot.message_handler(func=lambda message: message.text == "ℹ️ О методике")
def about(message):
    bot.send_message(
        message.chat.id,
        "Методика использует два инструмента саморефлексии:\n\n"
        "🔮 Тест на ведущую чакру — показывает, какая тема сейчас проявлена сильнее.\n"
        "🗺 Энергокарта — помогает оценить текущее субъективное состояние всех 7 чакр по шкале от 1 до 5.\n\n"
        "Материалы предназначены для саморефлексии и не являются медицинской или психологической диагностикой.",
    )


@bot.message_handler(commands=["admin"])
def admin(message):
    if message.from_user.id not in ADMINS:
        return
    users, results, distribution = stats()
    text = f"⚙️ Админ-панель\n👥 Пользователей: {users}\n🔮 Результатов: {results}\n\n" + "\n".join(f"{CHAKRAS[i]['name']}: {distribution.get(i, 0)}" for i in range(1, 8))
    bot.send_message(message.chat.id, text)


print("Bot started")
bot.infinity_polling(skip_pending=True)
