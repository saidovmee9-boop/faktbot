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
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================= WEB SERVER (RENDER FIX) =================
app = web.Application()

async def handle(request):
    return web.Response(text="Bot is running 🚀")

app.router.add_get("/", handle)

async def start_web():
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():
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
    CREATE TABLE IF NOT EXISTS user_state (
        user_id INTEGER PRIMARY KEY,
        cat TEXT,
        idx INTEGER DEFAULT 0
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

init_db()

# ================= FACTS =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Suv 100°C da qaynaydi"),
        ("Earth orbits the Sun", "Yer Quyosh atrofida aylanadi"),
        ("Humans have 206 bones", "Insonda 206 ta suyak bor"),
    ],
    "history": [
        ("WW2 ended in 1945", "2-jahon urushi 1945 da tugagan"),
        ("Rome was founded in 753 BC", "Rim 753 BC asos solingan"),
    ],
    "tech": [
        ("Python is a programming language", "Python dasturlash tili"),
        ("AI means Artificial Intelligence", "AI sun’iy intellekt"),
    ]
}

# ================= QUIZ =================
def generate_quiz():
    cat = random.choice(list(FACTS.keys()))
    fact = random.choice(FACTS[cat])

    question = f"🇬🇧 {fact[0]}"
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
        kb.add(types.InlineKeyboardButton(
            opt,
            callback_data=f"ans:{game_id}:{opt}:{correct}"
        ))

    cursor.execute("SELECT user_id FROM players WHERE game_id=?", (game_id,))
    users = cursor.fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], f"🎯 QUIZ\n\n{question}", reply_markup=kb)
        except:
            pass

async def run_game(game_id):
    for _ in range(5):
        await send_question(game_id)
        await asyncio.sleep(12)

    await show_results(game_id)

# ================= RESULTS =================
async def show_results(game_id):
    cursor.execute("""
        SELECT user_id, score
        FROM players
        WHERE game_id=?
        ORDER BY score DESC
    """, (game_id,))

    players = cursor.fetchall()

    text = "🏆 NATIJA\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    for i, p in enumerate(players[:5]):
        text += f"{medals[i]} {p[0]} — {p[1]} ball\n"

    cursor.execute("SELECT user_id FROM players WHERE game_id=?", (game_id,))
    users = cursor.fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], text)
        except:
            pass

# ================= QUIZ START =================
@dp.message_handler(lambda m: m.text == "🎯 Quiz Game")
async def start_game(message: types.Message):
    game_id = str(random.randint(1000, 9999))

    cursor.execute("INSERT INTO games VALUES (?, ?)", (game_id, 1))
    cursor.execute("INSERT INTO players VALUES (?, ?, 0)", (game_id, message.from_user.id))
    conn.commit()

    await message.answer(f"🎮 GAME STARTED\nID: {game_id}")

    asyncio.create_task(run_game(game_id))

# ================= ANSWER =================
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("ans"))
async def answer(call: types.CallbackQuery):
    try:
        _, game_id, ans, correct = call.data.split(":")
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

# ================= RUN =================
async def on_startup(dp):
    asyncio.create_task(start_web())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)