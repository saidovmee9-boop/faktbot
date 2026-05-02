import os
import random
import asyncio
import logging
from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import aiosqlite

# ================= SETUP =================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= WEB =================
app = web.Application()

async def health(request):
    return web.Response(text="Ultra Pro Quiz Bot 🚀 Running")

app.router.add_get("/", health)

async def start_web():
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ================= FACT SYSTEM =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Suv 100°C da qaynaydi"),
        ("Humans have 206 bones", "Insonda 206 ta suyak bor"),
        ("Light is faster than sound", "Yorug‘lik tezligi tovushdan tez"),
    ],
    "history": [
        ("World War II ended in 1945", "Ikkinchi jahon urushi 1945-yilda tugagan"),
        ("Uzbekistan became independent in 1991", "O‘zbekiston 1991-yilda mustaqil bo‘lgan"),
    ],
    "tech": [
        ("AI means Artificial Intelligence", "AI — sun’iy intellekt"),
        ("Internet started development in 1983", "Internet 1983-yilda boshlangan"),
    ]
}

CATEGORY_WEIGHTS = {
    "science": 45,
    "history": 30,
    "tech": 25
}

GAME_STATE = {}

# ================= DB =================
async def init_db():
    async with aiosqlite.connect("bot.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS lobby (
            game_id TEXT,
            user_id INTEGER,
            nickname TEXT,
            ready INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            PRIMARY KEY (game_id, user_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS saved_facts (
            user_id INTEGER,
            en TEXT,
            uz TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER PRIMARY KEY,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0
        )
        """)

        await db.commit()

# ================= UTIL =================
def pick_category():
    pool = []
    for cat, w in CATEGORY_WEIGHTS.items():
        pool += [cat] * w
    return random.choice(pool)

def generate_question():
    category = pick_category()
    fact = random.choice(FACTS[category])

    correct = fact[1]

    wrong = []
    for c in FACTS:
        for f in FACTS[c]:
            if f[1] != correct:
                wrong.append(f[1])

    options = random.sample(wrong, min(2, len(wrong)))
    options.append(correct)
    random.shuffle(options)

    return category, fact, correct, options

# ================= KEYBOARD =================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎮 Start Quiz")
    kb.add("⭐ Saved Facts")
    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🔥 Ultra Quiz Bot Ready", reply_markup=main_kb())

# ================= CREATE ROOM =================
@dp.message_handler(lambda m: m.text == "🎮 Start Quiz")
async def create_room(message: types.Message):
    game_id = str(random.randint(1000, 9999))

    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO lobby VALUES (?, ?, ?, 0, 0)",
            (game_id, message.from_user.id, message.from_user.first_name)
        )
        await db.commit()

    GAME_STATE[game_id] = {"answered": set()}

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⚡ JOIN / READY", callback_data=f"ready:{game_id}"))

    await message.answer(f"🎮 ROOM CREATED\nID: {game_id}\n/join {game_id}", reply_markup=kb)

# ================= JOIN =================
@dp.message_handler(lambda m: m.text and m.text.startswith("/join"))
async def join(message: types.Message):
    game_id = message.text.split()[1]

    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO lobby VALUES (?, ?, ?, 0, 0)",
            (game_id, message.from_user.id, message.from_user.first_name)
        )
        await db.commit()

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⚡ READY", callback_data=f"ready:{game_id}"))

    await message.answer("👤 Joined", reply_markup=kb)

# ================= READY =================
@dp.callback_query_handler(lambda c: c.data.startswith("ready"))
async def ready(call: types.CallbackQuery):
    _, game_id = call.data.split(":")

    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
            UPDATE lobby SET ready=1
            WHERE user_id=? AND game_id=?
        """, (call.from_user.id, game_id))
        await db.commit()

        cur = await db.execute("""
            SELECT COUNT(*) FROM lobby
            WHERE game_id=? AND ready=0
        """, (game_id,))

        count = (await cur.fetchone())[0]

    await call.answer("Ready!")

    if count == 0:
        asyncio.create_task(game_loop(game_id))

# ================= STATS =================
async def update_stats(user_id, correct=True):
    async with aiosqlite.connect("bot.db") as db:
        if correct:
            await db.execute("""
                INSERT INTO stats(user_id, correct, wrong)
                VALUES (?,1,0)
                ON CONFLICT(user_id) DO UPDATE SET correct = correct + 1
            """, (user_id,))
        else:
            await db.execute("""
                INSERT INTO stats(user_id, correct, wrong)
                VALUES (?,0,1)
                ON CONFLICT(user_id) DO UPDATE SET wrong = wrong + 1
            """, (user_id,))
        await db.commit()

# ================= GAME LOOP =================
async def game_loop(game_id):

    for i in range(5):

        category, fact, correct, options = generate_question()

        kb = types.InlineKeyboardMarkup()

        for opt in options:
            kb.add(types.InlineKeyboardButton(
                opt,
                callback_data=f"ans:{game_id}:{opt}:{correct}:{fact[0]}:{fact[1]}"
            ))

        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute("SELECT user_id FROM lobby WHERE game_id=?", (game_id,))
            users = await cur.fetchall()

        for u in users:
            await bot.send_message(
                u[0],
                f"🎯 {category.upper()}\n\n🇬🇧 {fact[0]}",
                reply_markup=kb
            )

        await asyncio.sleep(10)

# ================= ANSWER =================
@dp.callback_query_handler(lambda c: c.data.startswith("ans"))
async def answer(call: types.CallbackQuery):
    _, game_id, ans, correct, en, uz = call.data.split(":", 5)

    if ans == correct:
        await update_stats(call.from_user.id, True)

        # SAVE FACT AUTOMATICALLY
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("""
                INSERT INTO saved_facts(user_id, en, uz)
                VALUES (?,?,?)
            """, (call.from_user.id, en, uz))
            await db.commit()

        await call.answer("✅ +1 Saved")
    else:
        await update_stats(call.from_user.id, False)
        await call.answer("❌ Wrong")

# ================= SAVED FACTS =================
@dp.message_handler(lambda m: m.text == "⭐ Saved Facts")
async def saved(message: types.Message):
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("""
            SELECT en, uz FROM saved_facts
            WHERE user_id=?
        """, (message.from_user.id,))
        rows = await cur.fetchall()

    if not rows:
        return await message.answer("No saved facts yet.")

    text = "⭐ SAVED FACTS:\n\n"
    for r in rows[-10:]:
        text += f"🇬🇧 {r[0]}\n🇺🇿 {r[1]}\n\n"

    await message.answer(text)

# ================= STARTUP =================
async def on_startup(_):
    await init_db()
    asyncio.create_task(start_web())

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)