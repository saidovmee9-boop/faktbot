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

# ================= FACTS =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Suv 100°C da qaynaydi"),
        ("Earth orbits the Sun", "Yer Quyosh atrofida aylanadi"),
        ("Humans have 206 bones", "Insonda 206 ta suyak bor"),
        ("Light is faster than sound", "Yorug‘lik tovushdan tez"),
    ],
    "history": [
        ("WW2 ended in 1945", "2-jahon urushi 1945 da tugagan"),
        ("Rome was founded in 753 BC", "Rim 753 BC asos solingan"),
        ("Columbus discovered America in 1492", "Kolumb 1492 yilda Amerika"),
    ],
    "tech": [
        ("Python is a programming language", "Python dasturlash tili"),
        ("AI means Artificial Intelligence", "AI sun’iy intellekt"),
        ("CPU is brain of computer", "CPU kompyuter miyasi"),
    ]
}

# ================= QUIZ =================
def generate_quiz():
    cat = random.choice(list(FACTS.keys()))
    fact = random.choice(FACTS[cat])

    question = f"Quyidagi faktning o‘zbekcha tarjimasi qaysi?\n\n🇬🇧 {fact[0]}"
    correct = fact[1]

    wrong = []
    for c in FACTS:
        for f in FACTS[c]:
            if f[1] != correct:
                wrong.append(f[1])

    options = random.sample(wrong, 2)
    options.append(correct)
    random.shuffle(options)

    return question, correct, options


# ================= KEYBOARD =================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "📜 History", "💻 Tech")
    kb.add("🎲 Random", "❤️ Saved", "📊 Stats")
    kb.add("🎯 Quiz Game")
    return kb


# ================= USER INIT =================
async def ensure_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()


# ================= QUIZ GAME =================
@dp.message_handler(lambda m: m.text == "🎯 Quiz Game")
async def start_game(message: types.Message):
    game_id = str(random.randint(1000, 9999))

    cursor.execute("INSERT INTO games VALUES (?, ?)", (game_id, 1))
    cursor.execute("INSERT INTO players VALUES (?, ?, 0)", (game_id, message.from_user.id))
    conn.commit()

    await message.answer(
        f"🎮 QUIZ BOSHLANDI!\n\n"
        f"🆔 Game ID: {game_id}\n"
        f"/join {game_id} bilan boshqalar qo‘shiladi\n"
        f"🏆 5 ta savol bo‘ladi"
    )

    asyncio.create_task(run_game(game_id))


@dp.message_handler(lambda m: m.text.startswith("/join"))
async def join_game(message: types.Message):
    try:
        game_id = message.text.split()[1]
    except:
        return await message.answer("❌ Xato ID")

    cursor.execute("INSERT INTO players VALUES (?, ?, 0)", (game_id, message.from_user.id))
    conn.commit()

    await message.answer("✅ Qo‘shildingiz!")


async def send_question(game_id):
    question, correct, options = generate_quiz()

    kb = types.InlineKeyboardMarkup()
    for opt in options:
        kb.add(types.InlineKeyboardButton(opt, callback_data=f"ans:{game_id}:{opt}:{correct}"))

    cursor.execute("SELECT user_id FROM players WHERE game_id=?", (game_id,))
    users = cursor.fetchall()

    for u in users:
        await bot.send_message(u[0], f"🎯 QUIZ\n\n{question}", reply_markup=kb)


async def run_game(game_id):
    for _ in range(5):
        await send_question(game_id)
        await asyncio.sleep(15)

    await show_results(game_id)


@dp.callback_query_handler(lambda c: c.data.startswith("ans"))
async def answer(call: types.CallbackQuery):
    _, game_id, answer, correct = call.data.split(":")

    if answer == correct:
        cursor.execute("""
            UPDATE players SET score = score + 1
            WHERE user_id=? AND game_id=?
        """, (call.from_user.id, game_id))
        conn.commit()

        await call.answer("✅ To‘g‘ri!")
    else:
        await call.answer(f"❌ Noto‘g‘ri!\nJavob: {correct}")


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
        await bot.send_message(u[0], text)


# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)