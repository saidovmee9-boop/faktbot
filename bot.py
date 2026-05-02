import os
import logging
import random
import sqlite3
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv
from aiohttp import web

# ================= SETUP =================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# ================= WEB (RENDER) =================
app = web.Application()

async def health(request):
    return web.Response(text="Ultra Pro Bot Running 🚀")

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
CREATE TABLE IF NOT EXISTS lobby (
    game_id TEXT,
    user_id INTEGER,
    nickname TEXT,
    ready INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    answered INTEGER DEFAULT 0
)
""")
conn.commit()

# ================= GAME STATE =================
GAME_STATE = {
    "active": {},
    "answered": set()
}

# ================= FACTS =================
FACTS = [
    ("Water boils at 100°C", "Suv 100°C da qaynaydi"),
    ("Earth orbits the Sun", "Yer Quyosh atrofida aylanadi"),
    ("Humans have 206 bones", "Insonda 206 ta suyak bor"),
    ("Light is faster than sound", "Yorug‘lik tezligi tovushdan tez"),
]

used_questions = set()

def get_unique_question():
    for _ in range(30):
        f = random.choice(FACTS)
        if f[0] not in used_questions:
            used_questions.add(f[0])
            return f
    return random.choice(FACTS)

# ================= KEYBOARD =================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎮 Ultra Quiz")
    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🔥 Ultra Pro Kahoot Bot", reply_markup=main_kb())

# ================= ROOM =================
@dp.message_handler(lambda m: m.text == "🎮 Ultra Quiz")
async def create_room(message: types.Message):
    game_id = str(random.randint(1000, 9999))

    cursor.execute(
        "INSERT INTO lobby VALUES (?, ?, ?, 0, 0, 0)",
        (game_id, message.from_user.id, message.from_user.first_name)
    )
    conn.commit()

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⚡ JOIN / READY", callback_data=f"ready:{game_id}"))

    await message.answer(
        f"🎮 ROOM CREATED\n\nID: {game_id}\n/join {game_id}",
        reply_markup=kb
    )

# ================= JOIN =================
@dp.message_handler(lambda m: m.text and m.text.startswith("/join"))
async def join(message: types.Message):
    try:
        game_id = message.text.split()[1]
    except:
        return await message.answer("❌ Xato ID")

    cursor.execute(
        "INSERT INTO lobby VALUES (?, ?, ?, 0, 0, 0)",
        (game_id, message.from_user.id, message.from_user.first_name)
    )
    conn.commit()

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⚡ READY", callback_data=f"ready:{game_id}"))

    await message.answer("👤 Joined!", reply_markup=kb)

# ================= READY =================
@dp.callback_query_handler(lambda c: c.data.startswith("ready"))
async def ready(call: types.CallbackQuery):
    _, game_id = call.data.split(":")

    cursor.execute("""
        UPDATE lobby
        SET ready=1
        WHERE user_id=? AND game_id=?
    """, (call.from_user.id, game_id))
    conn.commit()

    await call.answer("Ready!")

    cursor.execute("""
        SELECT COUNT(*) FROM lobby
        WHERE game_id=? AND ready=0
    """, (game_id,))

    if cursor.fetchone()[0] == 0:
        asyncio.create_task(game_loop(game_id))

# ================= QUIZ ENGINE =================
def generate():
    q = get_unique_question()
    correct = q[1]

    wrong = [f[1] for f in FACTS if f[1] != correct]

    if len(wrong) < 2:
        wrong = ["A", "B", "C"]

    options = random.sample(wrong, 2)
    options.append(correct)
    random.shuffle(options)

    return q, correct, options

# ================= LIVE TIMER =================
async def countdown(msg, text, seconds=5):
    for i in range(seconds, 0, -1):
        await msg.edit_text(f"{text}\n⏳ {i}s")
        await asyncio.sleep(1)

# ================= GAME LOOP =================
async def game_loop(game_id):
    GAME_STATE["answered"] = set()

    for i in range(5):
        q, correct, options = generate()

        kb = types.InlineKeyboardMarkup()

        for opt in options:
            kb.add(types.InlineKeyboardButton(
                opt,
                callback_data=f"ans:{game_id}:{opt}:{correct}"
            ))

        cursor.execute("SELECT user_id FROM lobby WHERE game_id=?", (game_id,))
        users = cursor.fetchall()

        for u in users:
            msg = await bot.send_message(u[0], f"🎯 QUESTION {i+1}\n\n🇬🇧 {q[0]}", reply_markup=kb)
            await countdown(msg, "🔥 ANSWER NOW", 5)

        await asyncio.sleep(10)

        await show_leaderboard(game_id)

    await final_result(game_id)

# ================= ANSWER SYSTEM =================
@dp.callback_query_handler(lambda c: c.data.startswith("ans"))
async def answer(call: types.CallbackQuery):
    try:
        _, game_id, ans, correct = call.data.split(":")
    except:
        return

    key = f"{call.from_user.id}:{game_id}"

    if key in GAME_STATE["answered"]:
        return await call.answer("❌ Already answered")

    GAME_STATE["answered"].add(key)

    if ans == correct:
        cursor.execute("""
            UPDATE lobby
            SET score = score + 1
            WHERE user_id=? AND game_id=?
        """, (call.from_user.id, game_id))
        conn.commit()
        await call.answer("⚡ +1")
    else:
        await call.answer("❌")

# ================= LIVE LEADERBOARD =================
async def show_leaderboard(game_id):
    cursor.execute("""
        SELECT nickname, score
        FROM lobby
        WHERE game_id=?
        ORDER BY score DESC
    """, (game_id,))

    players = cursor.fetchall()

    text = "📊 LIVE LEADERBOARD\n\n"

    for i, p in enumerate(players):
        text += f"{i+1}. {p[0]} — {p[1]} pts\n"

    cursor.execute("SELECT user_id FROM lobby WHERE game_id=?", (game_id,))
    users = cursor.fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], text)
        except:
            pass

# ================= FINAL =================
async def final_result(game_id):
    await show_leaderboard(game_id)

# ================= RUN =================
async def on_startup(dp):
    asyncio.create_task(start_web())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)