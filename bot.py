import logging
import os
import random
import sqlite3
import asyncio
from dotenv import load_dotenv
load_dotenv()


from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()




from aiogram import Bot, Dispatcher, executor, types

# 🔐 TOKEN (env dan olinadi)
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 🗄 DATABASE
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    lang TEXT DEFAULT 'uz',
    views INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    fact TEXT
)
""")

conn.commit()

# 📚 FACTS
FACTS = {
    "science": [
        ("Water boils at 100°C", "Suv 100°C da qaynaydi"),
        ("Earth orbits the Sun", "Yer Quyosh atrofida aylanadi"),
    ],
    "history": [
        ("WW2 ended in 1945", "2-jahon urushi 1945 da tugagan"),
    ],
    "tech": [
        ("Python is popular language", "Python mashhur dasturlash tili"),
    ]
}

user_data = {}

# 🟢 START
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "📜 History", "💻 Tech")
    kb.add("🎲 Random", "❤️ Saved", "📊 Stats")

    await message.answer("Kategoriya tanlang:", reply_markup=kb)

# 📂 CATEGORY
@dp.message_handler(lambda m: m.text in ["📚 Science", "📜 History", "💻 Tech"])
async def category(message: types.Message):

    cat_map = {
        "📚 Science": "science",
        "📜 History": "history",
        "💻 Tech": "tech"
    }

    cat = cat_map[message.text]

    user_data[message.from_user.id] = {"cat": cat, "index": 0}

    await send_fact(message, cat, 0)

# 📤 SEND FACT
async def send_fact(message, cat, index):

    fact_en, fact_uz = FACTS[cat][index]

    kb = types.InlineKeyboardMarkup()
    buttons = []

    if index > 0:
        buttons.append(types.InlineKeyboardButton("⬅️", callback_data="prev"))

    if index < len(FACTS[cat]) - 1:
        buttons.append(types.InlineKeyboardButton("➡️", callback_data="next"))

    buttons.append(types.InlineKeyboardButton("❤️", callback_data="save"))

    kb.add(*buttons)

    cursor.execute("UPDATE users SET views = views + 1 WHERE user_id=?", (message.from_user.id,))
    conn.commit()

    await message.answer(
        f"📌 FACT\n\n🌍 {fact_en}\n\n🇺🇿 {fact_uz}",
        reply_markup=kb
    )

# 🔘 NAV
@dp.callback_query_handler(lambda c: c.data in ["next", "prev"])
async def nav(call: types.CallbackQuery):

    user_id = call.from_user.id

    data = user_data[user_id]
    cat = data["cat"]
    index = data["index"]

    index += 1 if call.data == "next" else -1
    index = max(0, min(index, len(FACTS[cat]) - 1))

    user_data[user_id]["index"] = index

    fact_en, fact_uz = FACTS[cat][index]

    kb = types.InlineKeyboardMarkup()
    buttons = []

    if index > 0:
        buttons.append(types.InlineKeyboardButton("⬅️", callback_data="prev"))

    if index < len(FACTS[cat]) - 1:
        buttons.append(types.InlineKeyboardButton("➡️", callback_data="next"))

    buttons.append(types.InlineKeyboardButton("❤️", callback_data="save"))

    kb.add(*buttons)

    await call.message.edit_text(
        f"📌 FACT\n\n🌍 {fact_en}\n\n🇺🇿 {fact_uz}",
        reply_markup=kb
    )

    await call.answer()

# ❤️ SAVE
@dp.callback_query_handler(lambda c: c.data == "save")
async def save(call: types.CallbackQuery):
    user_id = call.from_user.id
    text = call.message.text

    cursor.execute("INSERT INTO saved VALUES (?, ?)", (user_id, text))
    conn.commit()

    await call.answer("Saqlandi ❤️")

# 🎲 RANDOM
@dp.message_handler(lambda m: m.text == "🎲 Random")
async def random_fact(message: types.Message):
    cat = random.choice(list(FACTS.keys()))
    fact = random.choice(FACTS[cat])

    await message.answer(f"🎲 RANDOM\n\n🌍 {fact[0]}\n\n🇺🇿 {fact[1]}")

# ❤️ SAVED LIST
@dp.message_handler(lambda m: m.text == "❤️ Saved")
async def saved(message: types.Message):
    cursor.execute("SELECT fact FROM saved WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchall()

    if not data:
        await message.answer("Hech narsa saqlanmagan 😢")
        return

    for f in data:
        await message.answer(f[0])

# 📊 STATS
@dp.message_handler(lambda m: m.text == "📊 Stats")
async def stats(message: types.Message):
    cursor.execute("SELECT views FROM users WHERE user_id=?", (message.from_user.id,))
    views = cursor.fetchone()[0]

    await message.answer(f"📊 Siz {views} ta fakt ko‘rdingiz")

# 🔍 SEARCH
@dp.message_handler()
async def search(message: types.Message):
    text = message.text.lower()

    results = []

    for cat in FACTS:
        for fact_en, fact_uz in FACTS[cat]:
            if text in fact_en.lower() or text in fact_uz.lower():
                results.append((fact_en, fact_uz))

    if not results:
        await message.answer("Topilmadi 😢")
        return

    for fact in results:
        await message.answer(f"🔍\n\n🌍 {fact[0]}\n\n🇺🇿 {fact[1]}")

# ⏱ DAILY FACT
async def scheduler():
    while True:
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for user in users:
            cat = random.choice(list(FACTS.keys()))
            fact = random.choice(FACTS[cat])

            try:
                await bot.send_message(
                    user[0],
                    f"📅 DAILY FACT\n\n🌍 {fact[0]}\n\n🇺🇿 {fact[1]}"
                )
            except:
                pass

        await asyncio.sleep(86400)

async def on_startup(dp):
    asyncio.create_task(scheduler())

# 🚀 RUN
if __name__ == "__main__":
    keep_alive()  # Avval serverni yoqamiz
    # Botni ishga tushirish (faqat bitta bo'lishi kerak):
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)