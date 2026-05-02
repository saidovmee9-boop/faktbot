import os
import logging
import random
import sqlite3

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.webhook import get_new_configured_app
from aiogram.utils.executor import start_webhook

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN missing")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # Render URL
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# ================= DB =================
conn = sqlite3.connect("/tmp/bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    en TEXT,
    ru TEXT,
    uz TEXT
)
""")
conn.commit()

# ================= FACTS =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Вода кипит при 100°C", "Suv 100°C da qaynaydi"),
        ("Humans have 206 bones", "У человека 206 костей", "Insonda 206 suyak bor"),
    ],
    "history": [
        ("WW2 ended in 1945", "WW2 закончилась 1945", "WW2 1945 tugagan"),
    ],
    "tech": [
        ("Internet started in 1983", "Интернет 1983", "Internet 1983"),
    ]
}

USED = set()
USER_STATE = {}

# ================= LOGIC =================
def get_fact(cat):
    pool = FACTS.get(cat, [])
    available = [f for f in pool if f[0] not in USED]

    if not available:
        USED.clear()
        available = pool

    fact = random.choice(available)
    USED.add(fact[0])
    return fact

# ================= KEYBOARDS =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "🏛 History")
    kb.add("💻 Tech", "⭐ Saved")
    return kb

def nav():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("⬅️", callback_data="prev"),
        types.InlineKeyboardButton("➡️", callback_data="next")
    )
    kb.add(types.InlineKeyboardButton("⭐ Save", callback_data="save"))
    return kb

# ================= HANDLERS =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 Webhook bot ishlayapti!", reply_markup=menu())

@dp.message_handler(lambda m: m.text in ["📚 Science", "🏛 History", "💻 Tech"])
async def category(m: types.Message):
    cat = m.text.split()[1].lower()
    fact = get_fact(cat)

    USER_STATE[m.from_user.id] = {"cat": cat, "fact": fact}

    await m.answer(
        f"📚 {cat.upper()}\n\n🇬🇧 {fact[0]}\n🇷🇺 {fact[1]}\n🇺🇿 {fact[2]}",
        reply_markup=nav()
    )

@dp.callback_query_handler(lambda c: c.data in ["next", "prev"])
async def nav_handler(c: types.CallbackQuery):
    uid = c.from_user.id

    if uid not in USER_STATE:
        return await c.answer("Start first")

    cat = USER_STATE[uid]["cat"]
    fact = get_fact(cat)

    USER_STATE[uid]["fact"] = fact

    await c.message.edit_text(
        f"📚 {cat.upper()}\n\n🇬🇧 {fact[0]}\n🇷🇺 {fact[1]}\n🇺🇿 {fact[2]}",
        reply_markup=nav()
    )

    await c.answer()

@dp.callback_query_handler(lambda c: c.data == "save")
async def save(c: types.CallbackQuery):
    uid = c.from_user.id

    if uid not in USER_STATE:
        return await c.answer("No fact")

    en, ru, uz = USER_STATE[uid]["fact"]

    cursor.execute("INSERT INTO saved VALUES (?,?,?,?)", (uid, en, ru, uz))
    conn.commit()

    await c.answer("Saved ⭐")

@dp.message_handler(lambda m: m.text == "⭐ Saved")
async def saved(m: types.Message):
    cursor.execute("SELECT en, ru, uz FROM saved WHERE user_id=?", (m.from_user.id,))
    rows = cursor.fetchall()

    if not rows:
        return await m.answer("No saved facts")

    text = "⭐ SAVED:\n\n"
    for r in rows[-10:]:
        text += f"🇬🇧 {r[0]}\n🇷🇺 {r[1]}\n🇺🇿 {r[2]}\n\n"

    await m.answer(text)

# ================= WEBHOOK =================
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

app = get_new_configured_app(
    dispatcher=dp,
    path=WEBHOOK_PATH
)

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# ================= RUN =================
if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))