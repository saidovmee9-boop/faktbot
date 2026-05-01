import os
import logging
import random
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# DATABASE
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    views INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    fact TEXT,
    PRIMARY KEY(user_id, fact)
)
""")

conn.commit()

FACTS = {
    "science": [
        ("Water boils at 100°C", "Suv 100°C da qaynaydi"),
        ("Earth orbits the Sun", "Yer Quyosh atrofida aylanadi"),
    ],
    "history": [
        ("WW2 ended in 1945", "2-jahon urushi 1945 da tugagan"),
    ],
    "tech": [
        ("Python is a popular language", "Python mashhur dasturlash tili"),
    ]
}

user_data = {}

# START
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "📜 History", "💻 Tech")
    kb.add("🎲 Random", "❤️ Saved", "📊 Stats")

    await message.answer("📌 Kategoriya tanlang:", reply_markup=kb)


# CATEGORY
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


async def send_fact(message, cat, index):
    fact_en, fact_uz = FACTS[cat][index]

    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []

    if index > 0:
        buttons.append(types.InlineKeyboardButton("⬅️", callback_data="prev"))
    if index < len(FACTS[cat]) - 1:
        buttons.append(types.InlineKeyboardButton("➡️", callback_data="next"))

    buttons.append(types.InlineKeyboardButton("❤️ Save", callback_data=f"save|{cat}|{index}"))
    kb.add(*buttons)

    cursor.execute("UPDATE users SET views = views + 1 WHERE user_id=?", (message.from_user.id,))
    conn.commit()

    await message.answer(
        f"📌 FACT\n\n🌍 {fact_en}\n\n🇺🇿 {fact_uz}",
        reply_markup=kb
    )


# NAVIGATION (FIX QILINMADI — SEND_FACT ishlayapti)
@dp.callback_query_handler(lambda c: c.data in ["next", "prev"])
async def nav(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in user_data:
        return await call.answer("Start bosing")

    data = user_data[user_id]
    cat = data["cat"]
    index = data["index"]

    index += 1 if call.data == "next" else -1
    index = max(0, min(index, len(FACTS[cat]) - 1))

    user_data[user_id]["index"] = index

    await send_fact(call.message, cat, index)
    await call.answer()


# SAVE
@dp.callback_query_handler(lambda c: c.data.startswith("save"))
async def save(call: types.CallbackQuery):
    _, cat, idx = call.data.split("|")
    idx = int(idx)

    fact_en, _ = FACTS[cat][idx]

    cursor.execute(
        "INSERT OR IGNORE INTO saved VALUES (?, ?)",
        (call.from_user.id, fact_en)
    )
    conn.commit()

    await call.answer("❤️ Saqlandi!")


# RANDOM
@dp.message_handler(lambda m: m.text == "🎲 Random")
async def random_fact(message: types.Message):
    cat = random.choice(list(FACTS.keys()))
    fact = random.choice(FACTS[cat])

    await message.answer(f"🎲 RANDOM\n\n🌍 {fact[0]}\n\n🇺🇿 {fact[1]}")


# SAVED
@dp.message_handler(lambda m: m.text == "❤️ Saved")
async def saved(message: types.Message):
    cursor.execute("SELECT fact FROM saved WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchall()

    if not data:
        return await message.answer("Hech narsa yo‘q 😢")

    for f in data:
        await message.answer(f"❤️ {f[0]}")


# STATS
@dp.message_handler(lambda m: m.text == "📊 Stats")
async def stats(message: types.Message):
    cursor.execute("SELECT views FROM users WHERE user_id=?", (message.from_user.id,))
    row = cursor.fetchone()

    views = row[0] if row else 0

    await message.answer(f"📊 Siz {views} ta fakt ko‘rgansiz")


# =========================
# 🌐 RENDER WEB SERVER FIX
# =========================

runner = None

async def handle(request):
    return web.Response(text="Bot is running!")

async def on_startup(dp):
    global runner

    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("Web server started on port", port)


async def on_shutdown(dp):
    global runner
    if runner:
        await runner.cleanup()


# START BOT
if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )