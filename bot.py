import os
import sqlite3
import random
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =====================
# TOKEN
# =====================
API_TOKEN = os.getenv("BOT_TOKEN") or "PUT_TOKEN_HERE"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# =====================
# DB
# =====================
def db():
    return sqlite3.connect("pro_fact.db")

def init_db():
    with db() as conn:
        c = conn.cursor()

        c.execute("CREATE TABLE IF NOT EXISTS stats (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_id INTEGER, UNIQUE(user_id,fact_id))")
        c.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, fact_id INTEGER, UNIQUE(user_id,fact_id))")

init_db()

# =====================
# FACTS (small but high quality)
# =====================
facts_data = {
    "science": [
        (1, "🧬 Inson DNKsi banan bilan 50% emas, 60% ga yaqin o‘xshash."),
        (2, "🧠 Miya energiya sarfi telefon zaryadidan ham kam."),
        (3, "🌌 Koinot har soniyada kengayib bormoqda.")
    ],
    "history": [
        (4, "📜 Kleopatra piramidalardan yaqinroq davrda yashagan."),
        (5, "🏛 Rim imperiyasi 500 yildan ortiq yashagan.")
    ],
    "tech": [
        (6, "💻 Birinchi kompyuter xona kattaligida bo‘lgan."),
        (7, "📡 Internet dastlab harbiy loyiha edi.")
    ]
}

# =====================
# LANG SYSTEM
# =====================
def get_lang(uid):
    return "uz"

# =====================
# STATE (IMPORTANT FIX)
# =====================
state = {}

# =====================
# MENU
# =====================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science", "💻 Tech")
    kb.add("📜 History", "🎲 Random")
    kb.add("❤️ Saved")
    return kb

# =====================
# TEXT FORMAT (3 LANG)
# =====================
def format_fact(text):
    return f"""
🇺🇿 {text}
🇷🇺 {text}
🇬🇧 {text}
"""

# =====================
# FACT GET
# =====================
def get_fact(cat, idx):
    return facts_data[cat][idx]

# =====================
# SHOW FACT (EDITABLE)
# =====================
async def show(uid, chat_id):
    st = state[uid]
    cat = st["cat"]
    idx = st["i"]

    fact = get_fact(cat, idx)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(
        InlineKeyboardButton("❤️ Save", callback_data=f"save_{fact[0]}")
    )

    await bot.send_message(
        chat_id,
        f"📚 <b>{cat.upper()}</b>\n\n{fact[1]}",
        parse_mode="HTML",
        reply_markup=kb
    )

# =====================
# START
# =====================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 Pro Fact Bot ishga tushdi", reply_markup=menu())

# =====================
# CATEGORY
# =====================
@dp.message_handler()
async def handler(m: types.Message):
    uid = m.from_user.id
    t = m.text

    if "Science" in t:
        cat = "science"
    elif "Tech" in t:
        cat = "tech"
    elif "History" in t:
        cat = "history"
    elif "Random" in t:
        cat = random.choice(["science","tech","history"])
    else:
        return

    state[uid] = {"cat": cat, "i": 0}

    await show(uid, m.chat.id)

# =====================
# NAVIGATION (FIXED EDIT TEXT)
# =====================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)

    if not st:
        return await c.answer("Start bot")

    if c.data == "next":
        st["i"] = (st["i"] + 1) % len(facts_data[st["cat"]])
    else:
        st["i"] = (st["i"] - 1) % len(facts_data[st["cat"]])

    cat = st["cat"]
    idx = st["i"]
    fact = get_fact(cat, idx)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data=f"save_{fact[0]}"))

    await c.message.edit_text(
        f"📚 <b>{cat.upper()}</b>\n\n{fact[1]}",
        parse_mode="HTML",
        reply_markup=kb
    )

# =====================
# SAVE (FIXED)
# =====================
@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = int(c.data.split("_")[1])

    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)", (c.from_user.id, fid))

    await c.answer("❤️ Saved")

# =====================
# SAVED LIST
# =====================
@dp.message_handler(lambda m: "Saved" in m.text or "❤️" in m.text)
async def saved(m):
    with db() as conn:
        rows = conn.execute("SELECT fact_id FROM saved WHERE user_id=?", (m.from_user.id,)).fetchall()

    if not rows:
        return await m.answer("Empty ❤️")

    txt = "❤️ SAVED FACTS:\n\n"
    for r in rows:
        fid = r[0]
        for cat in facts_data:
            for f in facts_data[cat]:
                if f[0] == fid:
                    txt += f"• {f[1]}\n"

    await m.answer(txt)

# =====================
# WEB SERVER (RENDER FIX)
# =====================
async def handle(request):
    return web.Response(text="Bot is running")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# =====================
# STARTUP
# =====================
async def on_startup(dp):
    asyncio.create_task(start_web())

# =====================
# RUN
# =====================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)