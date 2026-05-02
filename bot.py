import os
import logging
import random
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from aiohttp import web
import asyncio

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

if not TOKEN or not BASE_URL:
    raise Exception("ENV missing")

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DATABASE =================
conn = sqlite3.connect("/tmp/bot.db", check_same_thread=False)
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
CREATE TABLE IF NOT EXISTS seen (
    user_id INTEGER,
    fact TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    user_id INTEGER,
    date TEXT,
    count INTEGER
)
""")

conn.commit()

# ================= FACTS =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Вода кипит при 100°C", "Suv 100°C da qaynaydi"),
        ("Earth orbits the Sun", "Земля вращается вокруг Солнца", "Yer Quyosh atrofida aylanadi"),
        ("Humans have 206 bones", "У человека 206 костей", "Insonda 206 suyak bor"),
        ("Light travels faster than sound", "Свет быстрее звука", "Yorug‘lik tovushdan tez"),
    ],
    "history": [
        ("WW2 ended in 1945", "WW2 закончилась 1945", "WW2 1945 tugagan"),
        ("Roman Empire fell in 476", "Рим пал в 476", "Rim 476 da qulagan"),
        ("Ancient Egypt built pyramids", "Древний Египет строил пирамиды", "Misr piramidalar qurgan"),
    ],
    "tech": [
        ("Internet started in 1983", "Интернет 1983", "Internet 1983"),
        ("AI means Artificial Intelligence", "ИИ — ИИ", "AI sun’iy intellekt"),
        ("First computers were huge", "Первые компьютеры были огромные", "Birinchi kompyuterlar katta bo‘lgan"),
    ]
}

USER_STATE = {}

# ================= DATE =================
def today():
    return datetime.now().strftime("%Y-%m-%d")

# ================= STATS =================
def add_stat(user_id):
    d = today()
    cursor.execute("SELECT count FROM stats WHERE user_id=? AND date=?", (user_id, d))
    row = cursor.fetchone()

    if row:
        cursor.execute("UPDATE stats SET count=count+1 WHERE user_id=? AND date=?", (user_id, d))
    else:
        cursor.execute("INSERT INTO stats VALUES (?,?,1)", (user_id, d))

    conn.commit()

def get_stat(user_id):
    cursor.execute("SELECT count FROM stats WHERE user_id=? AND date=?", (user_id, today()))
    row = cursor.fetchone()
    return row[0] if row else 0

# ================= FACT ENGINE (NO REPEAT PER USER) =================
def get_fact(cat, user_id):
    pool = FACTS.get(cat, [])

    cursor.execute("SELECT fact FROM seen WHERE user_id=?", (user_id,))
    seen = [r[0] for r in cursor.fetchall()]

    available = [f for f in pool if f[0] not in seen]

    if not available:
        cursor.execute("DELETE FROM seen WHERE user_id=?", (user_id,))
        conn.commit()
        available = pool

    fact = random.choice(available)

    cursor.execute("INSERT INTO seen VALUES (?,?)", (user_id, fact[0]))
    conn.commit()

    return fact

def random_fact(user_id):
    all_facts = sum(FACTS.values(), [])
    return get_fact(random.choice(list(FACTS.keys())), user_id)

# ================= UI =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "🏛 History")
    kb.add("💻 Tech", "🎲 Random")
    kb.add("⭐ Saved", "📊 Stats")
    return kb

def nav():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        types.InlineKeyboardButton("➡️ Next", callback_data="next")
    )
    kb.add(types.InlineKeyboardButton("⭐ Save", callback_data="save"))
    return kb

# ================= FORMAT =================
def format_fact(title, fact):
    return (
        f"📚 <b>{title}</b>\n\n"
        f"🇬🇧 {fact[0]}\n"
        f"🇷🇺 {fact[1]}\n"
        f"🇺🇿 {fact[2]}"
    )

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 <b>PRO FACT BOT</b>", parse_mode="HTML", reply_markup=menu())

# ================= CATEGORY =================
@dp.message_handler(lambda m: m.text in ["📚 Science", "🏛 History", "💻 Tech"])
async def category(m: types.Message):
    cat = m.text.split()[1].lower()

    fact = get_fact(cat, m.from_user.id)
    USER_STATE[m.from_user.id] = {"cat": cat, "fact": fact}

    add_stat(m.from_user.id)

    await m.answer(
        format_fact(cat.upper(), fact) + f"\n\n📊 Today: {get_stat(m.from_user.id)}",
        reply_markup=nav(),
        parse_mode="HTML"
    )

# ================= RANDOM =================
@dp.message_handler(lambda m: m.text == "🎲 Random")
async def random_handler(m: types.Message):
    fact = random_fact(m.from_user.id)

    USER_STATE[m.from_user.id] = {"cat": "random", "fact": fact}

    add_stat(m.from_user.id)

    await m.answer(
        format_fact("🎲 RANDOM", fact),
        reply_markup=nav(),
        parse_mode="HTML"
    )

# ================= NAV =================
@dp.callback_query_handler(lambda c: c.data in ["next", "prev"])
async def nav_handler(c: types.CallbackQuery):
    uid = c.from_user.id

    if uid not in USER_STATE:
        return await c.answer("Start first")

    cat = USER_STATE[uid]["cat"]

    fact = random_fact(uid) if cat == "random" else get_fact(cat, uid)

    USER_STATE[uid]["fact"] = fact

    add_stat(uid)

    await c.message.edit_text(
        format_fact(cat.upper(), fact),
        reply_markup=nav(),
        parse_mode="HTML"
    )

    await c.answer()

# ================= SAVE =================
@dp.callback_query_handler(lambda c: c.data == "save")
async def save(c: types.CallbackQuery):
    uid = c.from_user.id

    if uid not in USER_STATE:
        return await c.answer("No fact")

    en, ru, uz = USER_STATE[uid]["fact"]

    cursor.execute("INSERT INTO saved VALUES (?,?,?,?)", (uid, en, ru, uz))
    conn.commit()

    await c.answer("⭐ Saved")

# ================= SAVED =================
@dp.message_handler(lambda m: m.text == "⭐ Saved")
async def saved(m: types.Message):
    cursor.execute("SELECT en, ru, uz FROM saved WHERE user_id=?", (m.from_user.id,))
    rows = cursor.fetchall()

    if not rows:
        return await m.answer("No saved facts")

    text = "⭐ SAVED FACTS:\n\n"
    for r in rows[-10:]:
        text += format_fact("SAVED", r) + "\n\n"

    await m.answer(text, parse_mode="HTML")

# ================= STATS =================
@dp.message_handler(lambda m: m.text == "📊 Stats")
async def stats(m: types.Message):
    count = get_stat(m.from_user.id)

    await m.answer(
        f"📊 <b>TODAY STATS</b>\n\n"
        f"👀 Viewed: <b>{count}</b>",
        parse_mode="HTML"
    )

# ================= WEBHOOK =================
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()



async def handle(request):
    return web.Response(text="Bot is running!")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render avtomatik tarzda 10000-portni yoki PORT o'zgaruvchisini beradi
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()


async def main():
    # 1. Web serverni orqa fonda ishga tushiramiz
    asyncio.create_task(run_web_server())
    
    # 2. Botni ishga tushiramiz (eskicha holatda qolaveradi)
    # Masalan sizda shunday bo'lishi mumkin:
    bot = Bot(token="TOKEN")
    dp = Dispatcher()
    
    print("Bot ishga tushdi...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())




if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )