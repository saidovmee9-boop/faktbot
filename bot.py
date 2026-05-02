import os
import logging
import random
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

if not TOKEN or not BASE_URL:
    raise Exception("ENV missing")

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
conn = sqlite3.connect("/tmp/bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    user_id INTEGER,
    date TEXT,
    count INTEGER DEFAULT 0
)
""")

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
FACTS = [
    ("Water boils at 100°C", "Вода кипит при 100°C", "Suv 100°C da qaynaydi"),
    ("Humans have 206 bones", "У человека 206 костей", "Insonda 206 suyak bor"),
    ("Internet started in 1983", "Интернет 1983", "Internet 1983"),
    ("Earth has 1 moon", "У Земли 1 луна", "Yerda 1 oy bor"),
]

USER_STATE = {}

# ================= DATE =================
def today():
    return datetime.now().strftime("%Y-%m-%d")

# ================= STATS =================
def add_stat(user_id):
    d = today()

    cursor.execute("SELECT count FROM stats WHERE user_id=? AND date=?", (user_id, d))
    row = cursor.fetchone()

    if row:
        cursor.execute("UPDATE stats SET count=count+1 WHERE user_id=? AND date=?", (user_id, d))
    else:
        cursor.execute("INSERT INTO stats (user_id, date, count) VALUES (?,?,1)", (user_id, d))

    conn.commit()

def get_stat(user_id):
    cursor.execute("SELECT count FROM stats WHERE user_id=? AND date=?", (user_id, today()))
    row = cursor.fetchone()
    return row[0] if row else 0

# ================= FACT =================
def get_fact():
    return random.choice(FACTS)

# ================= UI =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Get Fact", "📊 My Stats")
    kb.add("⭐ Saved")
    return kb

def nav():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("➡️ Next", callback_data="next"),
        types.InlineKeyboardButton("⭐ Save", callback_data="save")
    )
    return kb

# ================= HANDLERS =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer(
        "🚀 <b>PRO FACT BOT</b>\nDaily stats + smart facts",
        parse_mode="HTML",
        reply_markup=menu()
    )

@dp.message_handler(lambda m: m.text == "📚 Get Fact")
async def fact(m: types.Message):
    fact = get_fact()
    USER_STATE[m.from_user.id] = fact

    add_stat(m.from_user.id)

    count = get_stat(m.from_user.id)

    await m.answer(
        f"📚 <b>FACT OF THE DAY</b>\n\n"
        f"🇬🇧 {fact[0]}\n"
        f"🇷🇺 {fact[1]}\n"
        f"🇺🇿 {fact[2]}\n\n"
        f"📊 Today viewed: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=nav()
    )

@dp.callback_query_handler(lambda c: c.data == "next")
async def next_fact(c: types.CallbackQuery):
    fact = get_fact()
    USER_STATE[c.from_user.id] = fact

    add_stat(c.from_user.id)
    count = get_stat(c.from_user.id)

    await c.message.edit_text(
        f"📚 <b>NEW FACT</b>\n\n"
        f"🇬🇧 {fact[0]}\n"
        f"🇷🇺 {fact[1]}\n"
        f"🇺🇿 {fact[2]}\n\n"
        f"📊 Today viewed: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=nav()
    )

    await c.answer()

@dp.callback_query_handler(lambda c: c.data == "save")
async def save(c: types.CallbackQuery):
    uid = c.from_user.id

    if uid not in USER_STATE:
        return await c.answer("No fact")

    en, ru, uz = USER_STATE[uid]

    cursor.execute("INSERT INTO saved VALUES (?,?,?,?)", (uid, en, ru, uz))
    conn.commit()

    await c.answer("⭐ Saved!")

@dp.message_handler(lambda m: m.text == "📊 My Stats")
async def stats(m: types.Message):
    count = get_stat(m.from_user.id)

    await m.answer(
        f"📊 <b>TODAY STATS</b>\n\n"
        f"👀 Viewed facts: <b>{count}</b>\n"
        f"🔄 Resets daily at 00:00",
        parse_mode="HTML"
    )

@dp.message_handler(lambda m: m.text == "⭐ Saved")
async def saved(m: types.Message):
    cursor.execute("SELECT en, ru, uz FROM saved WHERE user_id=?", (m.from_user.id,))
    rows = cursor.fetchall()

    if not rows:
        return await m.answer("No saved facts")

    text = "⭐ SAVED FACTS:\n\n"
    for r in rows[-10:]:
        text += f"🇬🇧 {r[0]}\n🇷🇺 {r[1]}\n🇺🇿 {r[2]}\n\n"

    await m.answer(text)

# ================= WEBHOOK =================
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )