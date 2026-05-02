import os
import logging
import random
import sqlite3
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ================= SETUP =================
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN missing in Render environment")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
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
        ("WW2 ended 1945", "WW2 закончилась 1945", "WW2 1945 tugagan"),
    ],
    "tech": [
        ("Internet started 1983", "Интернет 1983", "Internet 1983"),
    ]
}

USED = set()
USER_STATE = {}

# ================= LOGIC =================
def get_fact(cat):
    pool = FACTS[cat]
    available = [f for f in pool if f[0] not in USED]

    if not available:
        USED.clear()
        available = pool

    fact = random.choice(available)
    USED.add(fact[0])
    return fact

# ================= UI =================
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

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 Fact Bot Ready", reply_markup=menu())

# ================= CATEGORY =================
@dp.message_handler(lambda m: m.text in ["📚 Science", "🏛 History", "💻 Tech"])
async def category(m: types.Message):
    cat = m.text.split()[1].lower()

    fact = get_fact(cat)

    USER_STATE[m.from_user.id] = {
        "cat": cat,
        "fact": fact
    }

    await m.answer(
        f"📚 {cat.upper()}\n\n🇬🇧 {fact[0]}\n🇷🇺 {fact[1]}\n🇺🇿 {fact[2]}",
        reply_markup=nav()
    )

# ================= NAV =================
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

# ================= SAVE =================
@dp.callback_query_handler(lambda c: c.data == "save")
async def save(c: types.CallbackQuery):
    uid = c.from_user.id

    if uid not in USER_STATE:
        return await c.answer("No fact")

    en, ru, uz = USER_STATE[uid]["fact"]

    cursor.execute(
        "INSERT INTO saved VALUES (?,?,?,?)",
        (uid, en, ru, uz)
    )
    conn.commit()

    await c.answer("Saved ⭐")

# ================= SAVED =================
@dp.message_handler(lambda m: m.text == "⭐ Saved")
async def saved(m: types.Message):
    cursor.execute(
        "SELECT en, ru, uz FROM saved WHERE user_id=?",
        (m.from_user.id,)
    )

    rows = cursor.fetchall()

    if not rows:
        return await m.answer("No saved facts")

    text = "⭐ SAVED FACTS:\n\n"

    for r in rows[-10:]:
        text += f"🇬🇧 {r[0]}\n🇷🇺 {r[1]}\n🇺🇿 {r[2]}\n\n"

    await m.answer(text)

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)