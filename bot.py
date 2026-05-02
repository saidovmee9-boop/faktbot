import os
import random
import sqlite3
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ================= SETUP =================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    user_id INTEGER,
    category TEXT,
    views INTEGER DEFAULT 0
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
FACTS = {
    "science": [
        ("Water boils at 100°C", "Вода кипит при 100°C", "Suv 100°C da qaynaydi"),
        ("Earth has one moon", "У Земли один спутник", "Yerda bitta oy bor"),
        ("Light is fastest", "Свет самый быстрый", "Yorug‘lik eng tez"),
        ("Humans have 206 bones", "У человека 206 костей", "Insonda 206 suyak bor"),
        ("Gravity pulls objects", "Гравитация притягивает", "Gravitatsiya tortadi"),
    ],
    "history": [
        ("WW2 ended in 1945", "Вторая мировая закончилась в 1945", "WW2 1945 tugagan"),
        ("Rome was founded 753 BC", "Рим основан в 753 до н.э.", "Rim 753 BC tashkil topgan"),
        ("Cold War ended 1991", "Холодная война закончилась 1991", "Sovuq urush 1991 tugagan"),
        ("Napoleon born 1769", "Наполеон родился в 1769", "Napoleon 1769 tug‘ilgan"),
        ("USA independence 1776", "США независимость 1776", "AQSH 1776 mustaqil"),
    ],
    "tech": [
        ("Internet started 1983", "Интернет начался в 1983", "Internet 1983 boshlangan"),
        ("AI means Artificial Intelligence", "ИИ означает ИИ", "AI sun’iy intellekt"),
        ("First iPhone 2007", "Первый iPhone 2007", "Birinchi iPhone 2007"),
        ("Python created 1991", "Python создан 1991", "Python 1991 yaratilgan"),
        ("Google founded 1998", "Google основан 1998", "Google 1998 tashkil topgan"),
    ]
}

CATEGORIES = ["science", "history", "tech", "saved"]

# global used facts memory
USED = set()

USER_STATE = {}

# ================= UTIL =================
def get_fact(cat):
    pool = FACTS.get(cat, [])
    available = [f for f in pool if f[0] not in USED]

    if not available:
        USED.clear()
        available = pool

    fact = random.choice(available)
    USED.add(fact[0])
    return fact

def update_stats(user_id, cat):
    cursor.execute("""
    INSERT INTO stats(user_id, category, views)
    VALUES (?,?,1)
    ON CONFLICT(user_id, category)
    DO UPDATE SET views = views + 1
    """, (user_id, cat))
    conn.commit()

def get_stats(user_id):
    cursor.execute("""
    SELECT category, views FROM stats WHERE user_id=?
    """, (user_id,))
    return cursor.fetchall()

# ================= UI =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "🏛 History")
    kb.add("💻 Tech", "⭐ Saved")
    kb.add("📊 Stats")
    return kb

def nav_kb(cat):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("⬅️ Prev", callback_data=f"prev:{cat}"),
        types.InlineKeyboardButton("➡️ Next", callback_data=f"next:{cat}")
    )
    kb.add(
        types.InlineKeyboardButton("⭐ Save", callback_data="save")
    )
    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🚀 Ultra Fact Bot Ready", reply_markup=menu())

# ================= CATEGORY =================
@dp.message_handler(lambda m: m.text in ["📚 Science", "🏛 History", "💻 Tech"])
async def open_category(message: types.Message):
    cat = message.text.split()[1].lower()

    fact = get_fact(cat)

    USER_STATE[message.from_user.id] = {
        "cat": cat,
        "fact": fact
    }

    update_stats(message.from_user.id, cat)

    await message.answer(
        f"📚 {cat.upper()}\n\n🇬🇧 {fact[0]}\n🇷🇺 {fact[1]}\n🇺🇿 {fact[2]}",
        reply_markup=nav_kb(cat)
    )

# ================= NAVIGATION =================
@dp.callback_query_handler(lambda c: c.data.startswith(("next", "prev")))
async def nav(call: types.CallbackQuery):
    action, cat = call.data.split(":")

    fact = get_fact(cat)

    USER_STATE[call.from_user.id] = {
        "cat": cat,
        "fact": fact
    }

    update_stats(call.from_user.id, cat)

    await call.message.edit_text(
        f"📚 {cat.upper()}\n\n🇬🇧 {fact[0]}\n🇷🇺 {fact[1]}\n🇺🇿 {fact[2]}",
        reply_markup=nav_kb(cat)
    )

    await call.answer()

# ================= SAVE =================
@dp.callback_query_handler(lambda c: c.data == "save")
async def save(call: types.CallbackQuery):
    state = USER_STATE.get(call.from_user.id)

    if not state:
        return await call.answer("No fact")

    en, ru, uz = state["fact"]

    cursor.execute("""
    INSERT INTO saved(user_id, en, ru, uz)
    VALUES (?,?,?,?)
    """, (call.from_user.id, en, ru, uz))
    conn.commit()

    await call.answer("⭐ Saved!")

# ================= SAVED =================
@dp.message_handler(lambda m: m.text == "⭐ Saved")
async def saved(message: types.Message):
    cursor.execute("""
    SELECT en, ru, uz FROM saved WHERE user_id=?
    """, (message.from_user.id,))

    rows = cursor.fetchall()

    if not rows:
        return await message.answer("No saved facts")

    text = "⭐ SAVED FACTS:\n\n"

    for r in rows[-10:]:
        text += f"🇬🇧 {r[0]}\n🇷🇺 {r[1]}\n🇺🇿 {r[2]}\n\n"

    await message.answer(text)

# ================= STATS =================
@dp.message_handler(lambda m: m.text == "📊 Stats")
async def stats(message: types.Message):
    rows = get_stats(message.from_user.id)

    text = "📊 YOUR STATS:\n\n"

    for r in rows:
        text += f"{r[0]}: {r[1]} views\n"

    await message.answer(text or "No stats yet")

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)