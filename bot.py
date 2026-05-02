import os
import random
import sqlite3
import logging
import asyncio
from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ================= SETUP =================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= WEB (RENDER HEALTH) =================
app = web.Application()

async def health(request):
    return web.Response(text="Bot is alive 🚀")

app.router.add_get("/", health)

async def start_web():
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS saved_facts (
    user_id INTEGER,
    en TEXT,
    uz TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    user_id INTEGER PRIMARY KEY,
    correct INTEGER DEFAULT 0,
    wrong INTEGER DEFAULT 0
)
""")

conn.commit()

# ================= FACTS =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Suv 100°C da qaynaydi"),
        ("Humans have 206 bones", "Insonda 206 ta suyak bor"),
    ],
    "history": [
        ("WW2 ended in 1945", "WW2 1945-yilda tugagan"),
        ("Uzbekistan independence 1991", "O‘zbekiston 1991-yilda mustaqil bo‘lgan"),
    ],
    "tech": [
        ("AI means Artificial Intelligence", "AI — sun’iy intellekt"),
        ("Internet started in 1983", "Internet 1983-yilda boshlangan"),
    ]
}

CATEGORY_WEIGHTS = {
    "science": 50,
    "history": 30,
    "tech": 20
}

GAME_STATE = {}

# ================= UTIL =================
def pick_category():
    pool = []
    for k, v in CATEGORY_WEIGHTS.items():
        pool += [k] * v
    return random.choice(pool)

def generate_question():
    cat = pick_category()
    fact = random.choice(FACTS[cat])

    correct = fact[1]

    wrong = []
    for c in FACTS:
        for f in FACTS[c]:
            if f[1] != correct:
                wrong.append(f[1])

    options = random.sample(wrong, min(2, len(wrong)))
    options.append(correct)
    random.shuffle(options)

    return cat, fact, correct, options

# ================= KEYBOARD =================
def kb_main():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎮 Quiz")
    kb.add("⭐ Saved Facts")
    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🔥 Quiz Bot Ready", reply_markup=kb_main())

# ================= QUIZ =================
@dp.message_handler(lambda m: m.text == "🎮 Quiz")
async def quiz(message: types.Message):
    GAME_STATE[message.from_user.id] = {"answered": False}

    cat, fact, correct, options = generate_question()

    kb = types.InlineKeyboardMarkup()
    for o in options:
        kb.add(types.InlineKeyboardButton(
            o,
            callback_data=f"ans:{correct}:{fact[0]}:{fact[1]}"
        ))

    await message.answer(
        f"🎯 {cat.upper()}\n\n🇬🇧 {fact[0]}",
        reply_markup=kb
    )

# ================= ANSWER =================
@dp.callback_query_handler(lambda c: c.data.startswith("ans"))
async def answer(call: types.CallbackQuery):
    _, correct, en, uz = call.data.split(":", 3)

    if call.from_user.id in GAME_STATE and GAME_STATE[call.from_user.id]["answered"]:
        return await call.answer("Already answered")

    GAME_STATE.setdefault(call.from_user.id, {})["answered"] = True

    if call.data.split(":")[1] == call.data.split(":")[1]:
        cursor.execute("""
            INSERT OR IGNORE INTO stats(user_id, correct, wrong)
            VALUES (?,0,0)
        """, (call.from_user.id,))

        cursor.execute("""
            UPDATE stats SET correct = correct + 1
            WHERE user_id=?
        """, (call.from_user.id,))
        conn.commit()

        cursor.execute("""
            INSERT INTO saved_facts(user_id, en, uz)
            VALUES (?,?,?)
        """, (call.from_user.id, en, uz))
        conn.commit()

        await call.answer("✅ Correct + Saved")
    else:
        cursor.execute("""
            INSERT OR IGNORE INTO stats(user_id, correct, wrong)
            VALUES (?,0,0)
        """, (call.from_user.id,))

        cursor.execute("""
            UPDATE stats SET wrong = wrong + 1
            WHERE user_id=?
        """, (call.from_user.id,))
        conn.commit()

        await call.answer("❌ Wrong")

# ================= SAVED FACTS =================
@dp.message_handler(lambda m: m.text == "⭐ Saved Facts")
async def saved(message: types.Message):
    cursor.execute("""
        SELECT en, uz FROM saved_facts
        WHERE user_id=?
    """, (message.from_user.id,))

    rows = cursor.fetchall()

    if not rows:
        return await message.answer("No saved facts")

    text = "⭐ SAVED FACTS:\n\n"
    for r in rows[-10:]:
        text += f"🇬🇧 {r[0]}\n🇺🇿 {r[1]}\n\n"

    await message.answer(text)

# ================= STARTUP =================
async def on_startup(_):
    asyncio.create_task(start_web())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)