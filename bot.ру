import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["BASE_URL"]

app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("💰 Харажат қўшиш", callback_data="expense"),
            InlineKeyboardButton("💵 Даромад қўшиш", callback_data="income")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("🤖 AI ёрдамчи", callback_data="ai")
        ],
        [
            InlineKeyboardButton("💳 Қарзлар", callback_data="debts"),
            InlineKeyboardButton("🎯 Мақсадлар", callback_data="goals")
        ],
        [
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ]
    ]

    await update.message.reply_text(
        "👋 Салом! Мен Qudi AI.\n\n"
        "Мен сизга пул, харажат ва кундалик ишларингизни "
        "назорат қилишда ёрдам бераман.\n\n"
        "Қуйидаги менюдан танланг 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    messages = {
        "expense": "💰 Харажат миқдорини ёзинг.\nМасалан: 50 000 сўм овқатга.",
        "income": "💵 Даромад миқдорини ёзинг.\nМасалан: 7 000 000 сўм ойлик.",
        "stats": "📊 Статистика функцияси тез орада ишлайди.",
        "ai": "🤖 AI ёрдамчи тез орада ишлайди.",
        "debts": "💳 Қарзлар функцияси тез орада ишлайди.",
        "goals": "🎯 Мақсадлар функцияси тез орада ишлайди.",
        "premium": "💎 Premium тарифлар тез орада очилади."
    }

    await query.message.reply_text(messages.get(query.data, "Тез орада ишлайди."))


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button))


@app.post("/webhook")
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK"


@app.get("/")
def home():
    return "Qudi AI ishlayapti!"


if __name__ == "__main__":
    import asyncio
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    async def main():
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.bot.set_webhook(f"{BASE_URL}/webhook")

        config = Config()
        config.bind = [f"0.0.0.0:{os.environ.get('PORT', '10000')}"]

        await serve(app, config)

    asyncio.run(main())
