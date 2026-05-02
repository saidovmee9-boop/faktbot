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
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    en TEXT,
    ru TEXT,
    uz TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    user_id INTEGER,
    category TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, category)
)
""")

conn.commit()

# ================= FACTS =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Вода кипит при 100°C", "Suv 100°C da qaynaydi"),
        ("Earth has one moon", "У Земли один спутник", "Yerda bitta oy bor"),
        ("Light is fastest", "Свет самый быстрый", "Yorug‘lik eng tez"),
    ],
    "history": [
        ("WW2 ended 1945", "WW2 закончилась 1945", "WW2 1945 tugagan"),
        ("Rome founded 753 BC", "Рим основан 753 до н.э.", "Rim 753 BC"),
    ],
    "tech": [
        ("Internet 1983", "Интернет 1983", "Internet 1983"),
        ("Python 1991", "Python 1991", "Python 1991"),
    ]
}

USED = set()
USER_STATE = {}

# ================= UTILS =================
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
    INSERT INTO stats(user_id, category, count)
    VALUES (?, ?, 1)
    ON CONFLICT(user_id, category)
    DO UPDATE SET count = count + 1
    """, (user_id, cat))
    conn.commit()

# ================= UI =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "🏛 History")
    kb.add("💻 Tech", "⭐ Saved")
    return kb

def nav():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        types.InlineKeyboardButton("➡️ Next", callback_data="next")
    )
    kb.add(types.InlineKeyboardButton("⭐ Save", callback_data="save"))
    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🚀 Fact Bot Ready", reply_markup=menu())

# ================= CATEGORY =================
@dp.message_handler(lambda m: m.text in ["📚 Science", "🏛 History", "💻 Tech"])
async def category(message: types.Message):
    cat = message.text.split()[1].lower()

    fact = get_fact(cat)

    USER_STATE[message.from_user.id] = {
        "cat": cat,
        "fact": fact
    }

    update_stats(message.from_user.id, cat)

    await message.answer(
        f"📚 {cat.upper()}\n\n🇬🇧 {fact[0]}\n🇷🇺 {fact[1]}\n🇺🇿 {fact[2]}",
        reply_markup=nav()
    )

# ================= NAV =================
@dp.callback_query_handler(lambda c: c.data in ["next", "prev"])
async def nav_handler(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in USER_STATE:
        return await call.answer("No data")

    cat = USER_STATE[user_id]["cat"]
    fact = get_fact(cat)

    USER_STATE[user_id]["fact"] = fact

    update_stats(user_id, cat)

    await call.message.edit_text(
        f"📚 {cat.upper()}\n\n🇬🇧 {fact[0]}\n🇷🇺 {fact[1]}\n🇺🇿 {fact[2]}",
        reply_markup=nav()
    )

    await call.answer()

# ================= SAVE =================
@dp.callback_query_handler(lambda c: c.data == "save")
async def save(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in USER_STATE:
        return await call.answer("No fact")

    en, ru, uz = USER_STATE[user_id]["fact"]

    cursor.execute("""
    INSERT INTO saved(user_id, en, ru, uz)
    VALUES (?,?,?,?)
    """, (user_id, en, ru, uz))

    conn.commit()

    await call.answer("⭐ Saved")

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

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)