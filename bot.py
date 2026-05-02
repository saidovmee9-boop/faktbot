import os
import logging
import random
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv
from aiohttp import web

# ================= SETUP =================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= WEB (RENDER FIX) =================
app = web.Application()

async def home(request):
    return web.Response(text="Bot is running 🚀")

app.router.add_get("/", home)

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    active INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    game_id TEXT,
    user_id INTEGER,
    score INTEGER DEFAULT 0
)
""")

conn.commit()

# ================= FACTS (EN + UZ + RU) =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Suv 100°C da qaynaydi", "Вода кипит при 100°C"),
        ("Earth orbits the Sun", "Yer Quyosh atrofida aylanadi", "Земля вращается вокруг Солнца"),
    ],
    "history": [
        ("WW2 ended in 1945", "2-jahon urushi 1945 da tugagan", "Вторая мировая война закончилась в 1945"),
    ],
    "tech": [
        ("Python is a programming language", "Python dasturlash tili", "Python язык программирования"),
    ]
}

# ================= KEYBOARD =================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "📜 History", "💻 Tech")
    kb.add("🎲 Random", "📊 Stats")
    kb.add("🎯 Quiz Game")
    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("👋 Xush kelibsiz!", reply_markup=main_kb())

# ================= FACT =================
async def send_fact(message, cat):
    fact = random.choice(FACTS[cat])

    text = f"📌 FACT\n\n🇬🇧 {fact[0]}\n🇺🇿 {fact[1]}\n🇷🇺 {fact[2]}"
    await message.answer(text)

# ================= RANDOM =================
async def random_fact(message):
    cat = random.choice(list(FACTS.keys()))
    fact = random.choice(FACTS[cat])

    await message.answer(f"🎲 RANDOM\n\n🇬🇧 {fact[0]}\n🇺🇿 {fact[1]}\n🇷🇺 {fact[2]}")

# ================= STATS =================
async def stats(message):
    cursor.execute("SELECT views FROM users WHERE user_id=?", (message.from_user.id,))
    row = cursor.fetchone()

    views = row[0] if row else 0
    await message.answer(f"📊 Ko‘rgan: {views}")

# ================= QUIZ =================
def generate_quiz():
    cat = random.choice(list(FACTS.keys()))
    fact = random.choice(FACTS[cat])

    question = fact[0]
    correct = fact[1]

    wrong = [f[1] for c in FACTS for f in FACTS[c] if f[1] != correct]

    if len(wrong) < 2:
        wrong = ["A", "B", "C"]

    options = random.sample(wrong, 2)
    options.append(correct)
    random.shuffle(options)

    return question, correct, options

# ================= GAME =================
async def send_question(game_id):
    question, correct, options = generate_quiz()

    kb = types.InlineKeyboardMarkup()
    for opt in options:
        kb.add(types.InlineKeyboardButton(opt, callback_data=f"ans:{game_id}:{opt}:{correct}"))

    cursor.execute("SELECT user_id FROM players WHERE game_id=?", (game_id,))
    users = cursor.fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], f"🎯 QUIZ\n\n{question}\n⏱ 15s", reply_markup=kb)
        except:
            pass

    await asyncio.sleep(15)

# ================= RESULTS =================
async def show_results(game_id):
    cursor.execute("""
        SELECT user_id, score
        FROM players
        WHERE game_id=?
        ORDER BY score DESC
    """, (game_id,))

    players = cursor.fetchall()

    text = "🏆 RESULT\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, p in enumerate(players[:10]):
        text += f"{medals[i] if i < 3 else ''} {p[0]} — {p[1]} pts\n"

    for u in players:
        try:
            await bot.send_message(u[0], text)
        except:
            pass

# ================= GAME LOOP =================
async def game_loop(game_id):
    for _ in range(5):
        await send_question(game_id)

    await show_results(game_id)

# ================= ROUTER =================
@dp.message_handler()
async def router(message: types.Message):
    text = message.text

    if not text:
        return

    if text == "📚 Science":
        await send_fact(message, "science")
        return

    if text == "📜 History":
        await send_fact(message, "history")
        return

    if text == "💻 Tech":
        await send_fact(message, "tech")
        return

    if text == "🎲 Random":
        await random_fact(message)
        return

    if text == "📊 Stats":
        await stats(message)
        return

    if text == "🎯 Quiz Game":
        game_id = str(random.randint(1000, 9999))

        cursor.execute("INSERT INTO games VALUES (?, ?)", (game_id, 1))
        cursor.execute("INSERT INTO players VALUES (?, ?, 0)", (game_id, message.from_user.id))
        conn.commit()

        await message.answer(f"🎮 GAME STARTED\nID: {game_id}")
        asyncio.create_task(game_loop(game_id))
        return

    await message.answer("📌 Menyu ishlat", reply_markup=main_kb())

# ================= CALLBACK =================
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("ans"))
async def answer(call: types.CallbackQuery):
    try:
        parts = call.data.split(":")
        if len(parts) != 4:
            return await call.answer("error")

        _, game_id, ans, correct = parts

    except:
        return await call.answer("error")

    if ans == correct:
        cursor.execute("""
            UPDATE players
            SET score = score + 1
            WHERE user_id=? AND game_id=?
        """, (call.from_user.id, game_id))
        conn.commit()

        await call.answer("✅")
    else:
        await call.answer("❌")

# ================= STARTUP =================
async def on_startup(dp):
    asyncio.create_task(start_web())

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)