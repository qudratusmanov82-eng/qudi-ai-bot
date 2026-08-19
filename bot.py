import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

import psycopg
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]
BASE_URL = os.environ["BASE_URL"].rstrip("/")

app = Flask(__name__)

user_states = {}


# ---------------- DATABASE ----------------

def db():
    return psycopg.connect(DATABASE_URL)


def init_db():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    category VARCHAR(100),
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS debts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    person VARCHAR(150) NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    note TEXT,
                    paid BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    name VARCHAR(150) NOT NULL,
                    target NUMERIC(14,2) NOT NULL,
                    saved NUMERIC(14,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()


# ---------------- TELEGRAM API ----------------

def telegram(method, data=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"

    encoded = urllib.parse.urlencode(data or {}).encode()

    req = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps({
            "inline_keyboard": keyboard
        })

    return telegram("sendMessage", data)


def answer_callback(callback_id):
    return telegram(
        "answerCallbackQuery",
        {"callback_query_id": callback_id}
    )


# ---------------- MENU ----------------
def main_menu():
    return [
        [
            {"text": "💰 Харажат қўшиш", "callback_data": "expense"},
            {"text": "💵 Даромад қўшиш", "callback_data": "income"}
        ],
        [
            {"text": "📊 Статистика", "callback_data": "stats"},
            {"text": "💳 Қарзлар", "callback_data": "debts"}
        ],
        [
            {"text": "🎯 Мақсадлар", "callback_data": "goals"},
            {"text": "🤖 AI ёрдамчи", "callback_data": "ai"}
        ],
        [
            {"text": "💎 Premium", "callback_data": "premium"}
        ],
        [
            {"text": "📱 Qudi AI App", "web_app": {"url": "https://qudi-ai-bot.onrender.com/static/index.html"}}
        ]
    ]


# ---------------- START ----------------
def start(chat_id):
    user_states.pop(chat_id, None)

    send_message(
        chat_id,
        "🤖 QUDI AI\n\n"
        "Ассалому алайкум! 👋\n"
        "Сизнинг шахсий AI молиявий ассистентингиз.\n\n"
        "💰 Пулларингизни назорат қилинг\n"
        "📊 Харажатларингизни таҳлил қилинг\n"
        "🎯 Мақсадларингизга тезроқ етинг\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 Керакли бўлимни танланг:",
        main_menu()
    )



# ---------------- AMOUNT ----------------

def parse_amount(text):
    text = (
        text.lower()
        .replace("сўм", "")
        .replace("сум", "")
        .replace("so'm", "")
        .replace("som", "")
        .replace(" ", "")
        .replace(",", "")
        .replace(".", "")
    )

    try:
        return float(text)
    except:
        return None


# ---------------- EXPENSE ----------------

def expense_start(chat_id):
    user_states[chat_id] = {
        "step": "expense_amount"
    }

    send_message(
        chat_id,
        "💰 Харажат миқдорини ёзинг.\n\n"
        "Масалан:\n"
        "50000"
    )


def expense_amount(chat_id, text):
    amount = parse_amount(text)

    if amount is None or amount <= 0:
        send_message(chat_id, "❌ Суммани тўғри ёзинг.\nМасалан: 50000")
        return

    user_states[chat_id] = {
        "step": "expense_category",
        "amount": amount
    }

    send_message(
        chat_id,
        "📂 Категорияни танланг:",
        [
            [
                {"text": "🍔 Овқат", "callback_data": "cat_food"},
                {"text": "🚕 Транспорт", "callback_data": "cat_transport"}
            ],
            [
                {"text": "🛒 Харид", "callback_data": "cat_shopping"},
                {"text": "🏠 Уй", "callback_data": "cat_home"}
            ],
            [
                {"text": "💊 Соғлиқ", "callback_data": "cat_health"},
                {"text": "📦 Бошқа", "callback_data": "cat_other"}
            ]
        ]
    )


def save_expense(chat_id, category):
    state = user_states.get(chat_id)

    if not state:
        return

    amount = state["amount"]

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions
                (user_id, type, amount, category)
                VALUES (%s, %s, %s, %s)
                """,
                (chat_id, "expense", amount, category)
            )
        conn.commit()

    user_states.pop(chat_id, None)

    send_message(
        chat_id,
        f"✅ Харажат сақланди!\n\n"
        f"💰 Сумма: {amount:,.0f} сўм\n"
        f"📂 Категория: {category}",
        main_menu()
    )


# ---------------- INCOME ----------------

def income_start(chat_id):
    user_states[chat_id] = {
        "step": "income_amount"
    }

    send_message(
        chat_id,
        "💵 Даромад миқдорини ёзинг.\n\n"
        "Масалан:\n"
        "7000000"
    )


def income_amount(chat_id, text):
    amount = parse_amount(text)

    if amount is None or amount <= 0:
        send_message(chat_id, "❌ Суммани тўғри ёзинг.\nМасалан: 7000000")
        return

    user_states[chat_id] = {
        "step": "income_source",
        "amount": amount
    }

    send_message(
        chat_id,
        "💼 Даромад манбасини ёзинг.\n\n"
        "Масалан: Ойлик"
    )


def save_income(chat_id, source):
    state = user_states.get(chat_id)

    if not state:
        return

    amount = state["amount"]

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions
                (user_id, type, amount, category, note)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (chat_id, "income", amount, "Даромад", source)
            )
        conn.commit()

    user_states.pop(chat_id, None)

    send_message(
        chat_id,
        f"✅ Даромад сақланди!\n\n"
        f"💵 Сумма: {amount:,.0f} сўм\n"
        f"💼 Манба: {source}",
        main_menu()
    )


# ---------------- STATISTICS ----------------

def statistics(chat_id):
    with db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE user_id=%s AND type='income'
                """,
                (chat_id,)
            )
            income = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE user_id=%s AND type='expense'
                """,
                (chat_id,)
            )
            expense = cur.fetchone()[0]

    balance = income - expense

    send_message(
        chat_id,
        "📊 Сизнинг статистикангиз\n\n"
        f"💵 Жами даромад: {income:,.0f} сўм\n"
        f"💰 Жами харажат: {expense:,.0f} сўм\n"
        f"💳 Баланс: {balance:,.0f} сўм",
        main_menu()
    )


# ---------------- DEBTS ----------------

def debts_menu(chat_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT person, amount, type, paid
                FROM debts
                WHERE user_id=%s
                ORDER BY id DESC
                """,
                (chat_id,)
            )

            rows = cur.fetchall()

    text = "💳 Қарзлар\n\n"

    if not rows:
        text += "Ҳозирча қарзлар йўқ."
    else:
        for person, amount, debt_type, paid in rows:
            status = "✅ Тўланган" if paid else "⏳ Кутилаётган"
            text += (
                f"👤 {person}\n"
                f"💰 {amount:,.0f} сўм\n"
                f"📌 {debt_type}\n"
                f"{status}\n\n"
            )

    send_message(
        chat_id,
        text,
        [
            [
                {"text": "➕ Қарз қўшиш", "callback_data": "add_debt"},
                {"text": "🔙 Меню", "callback_data": "menu"}
            ]
        ]
    )


def add_debt_start(chat_id):
    user_states[chat_id] = {
        "step": "debt_person"
    }

    send_message(
        chat_id,
        "👤 Қарз ким билан?\n\n"
        "Масалан: Али"
    )


# ---------------- GOALS ----------------

def goals_menu(chat_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, target, saved
                FROM goals
                WHERE user_id=%s
                ORDER BY id DESC
                """,
                (chat_id,)
            )

            rows = cur.fetchall()

    text = "🎯 Мақсадлар\n\n"

    if not rows:
        text += "Ҳозирча мақсадлар йўқ."
    else:
        for name, target, saved in rows:
            percent = min((float(saved) / float(target)) * 100, 100)

            text += (
                f"🎯 {name}\n"
                f"💰 {saved:,.0f} / {target:,.0f} сўм\n"
                f"📈 {percent:.0f}%\n\n"
            )

    send_message(
        chat_id,
        text,
        [
            [
                {"text": "➕ Мақсад қўшиш", "callback_data": "add_goal"},
                {"text": "🔙 Меню", "callback_data": "menu"}
            ]
        ]
    )


def add_goal_start(chat_id):
    user_states[chat_id] = {
        "step": "goal_name"
    }

    send_message(
        chat_id,
        "🎯 Мақсад номини ёзинг.\n\n"
        "Масалан: Машина"
    )


# ---------------- AI / PREMIUM ----------------

def ai_menu(chat_id):
    send_message(
        chat_id,
        "🤖 AI ёрдамчи\n\n"
        "AI функцияси кейинги босқичда уланади.\n"
        "У харажатларингизни таҳлил қилиб, "
        "пулни тежаш бўйича шахсий тавсиялар беради.",
        main_menu()
    )


def premium(chat_id):
    send_message(
        chat_id,
        "💎 Qudi AI Premium\n\n"
        "Premium версияда:\n"
        "🤖 AI молиявий таҳлил\n"
        "📊 Кенгайтирилган статистика\n"
        "🔔 Эслатмалар\n"
        "🎯 Мақсадлар таҳлили\n"
        "📈 Ойлик ҳисоботлар\n\n"
        "Тўлов тизими кейинги босқичда уланади.",
        main_menu()
    )


# ---------------- CALLBACK ----------------

def handle_callback(callback):
    callback_id = callback["id"]
    answer_callback(callback_id)

    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    data = callback.get("data")

    if not chat_id:
        return

    if data == "menu":
        start(chat_id)

    elif data == "expense":
        expense_start(chat_id)

    elif data == "income":
        income_start(chat_id)

    elif data == "stats":
        statistics(chat_id)

    elif data == "debts":
        debts_menu(chat_id)

    elif data == "goals":
        goals_menu(chat_id)

    elif data == "ai":
        ai_menu(chat_id)

    elif data == "premium":
        premium(chat_id)

    elif data.startswith("cat_"):
        categories = {
            "cat_food": "Овқат",
            "cat_transport": "Транспорт",
            "cat_shopping": "Харид",
            "cat_home": "Уй",
            "cat_health": "Соғлиқ",
            "cat_other": "Бошқа"
        }

        save_expense(chat_id, categories[data])

    elif data == "add_debt":
        add_debt_start(chat_id)

    elif data == "add_goal":
        add_goal_start(chat_id)


# ---------------- TEXT ----------------

def handle_text(chat_id, text):
    state = user_states.get(chat_id)

    if not state:
        send_message(
            chat_id,
            "Менюдан керакли функцияни танланг 👇",
            main_menu()
        )
        return

    step = state["step"]

    if step == "expense_amount":
        expense_amount(chat_id, text)

    elif step == "income_amount":
        income_amount(chat_id, text)

    elif step == "income_source":
        save_income(chat_id, text)

    elif step == "debt_person":
        state["person"] = text
        state["step"] = "debt_amount"

        send_message(
            chat_id,
            "💰 Қарз суммасини ёзинг."
        )

    elif step == "debt_amount":
        amount = parse_amount(text)

        if not amount:
            send_message(chat_id, "❌ Суммани тўғри ёзинг.")
            return

        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO debts
                    (user_id, person, amount, type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        chat_id,
                        state["person"],
                        amount,
                        "Мен бераман"
                    )
                )
            conn.commit()

        user_states.pop(chat_id, None)

        send_message(
            chat_id,
            f"✅ Қарз сақланди!\n\n"
            f"👤 {state['person']}\n"
            f"💰 {amount:,.0f} сўм",
            main_menu()
        )

    elif step == "goal_name":
        state["name"] = text
        state["step"] = "goal_target"

        send_message(
            chat_id,
            "💰 Мақсад суммасини ёзинг."
        )

    elif step == "goal_target":
        amount = parse_amount(text)

        if not amount:
            send_message(chat_id, "❌ Суммани тўғри ёзинг.")
            return

        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO goals
                    (user_id, name, target)
                    VALUES (%s, %s, %s)
                    """,
                    (chat_id, state["name"], amount)
                )
            conn.commit()

        user_states.pop(chat_id, None)

        send_message(
            chat_id,
            f"✅ Мақсад сақланди!\n\n"
            f"🎯 {state['name']}\n"
            f"💰 {amount:,.0f} сўм",
            main_menu()
        )


# ---------------- UPDATE ----------------

def process_update(update):
    if "callback_query" in update:
        handle_callback(update["callback_query"])
        return

    message = update.get("message")

    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text.startswith("/start"):
        start(chat_id)
    else:
        handle_text(chat_id, text)


# ---------------- WEBHOOK ----------------

@app.post("/webhook")
def webhook():
    update = request.get_json(silent=True)

    if update:
        try:
            process_update(update)
        except Exception as e:
            print("BOT ERROR:", repr(e))

    return "OK"


@app.get("/")
def home():
    return "Qudi AI ishlayapti!"


# ---------------- STARTUP ----------------

init_db()

try:
    telegram(
        "setWebhook",
        {
            "url": f"{BASE_URL}/webhook"
        }
    )
    print("Webhook successfully configured")
except Exception as e:
    print("Webhook error:", repr(e))


if __name__ == "__main__":
    import hypercorn.asyncio
    from hypercorn.config import Config
    import asyncio

    config = Config()
    config.bind = [
        f"0.0.0.0:{os.environ.get('PORT', '10000')}"
    ]

    asyncio.run(
        hypercorn.asyncio.serve(app, config)
    )
