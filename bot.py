import os
import sqlite3
import asyncio
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

ADMIN_ID = 123456789  # o'zingni id

# ================= DB =================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS saved (uid INTEGER, text TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, premium INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, text TEXT)")
init_db()

# ================= FACTS =================
FACTS = {
    "science": [
        "Inson DNKsi bananga o‘xshaydi",
        "Miya uxlaganda ham ishlaydi",
        "Suv kosmosda muzlaydi",
        "Yurak 24/7 ishlaydi",
        "Odam 70% suv",
        "Bakteriyalar tanada bor",
        "Yer aylanadi",
        "Miya juda kuchli",
        "Koinot kengayadi",
        "Tana energiya ishlab chiqaradi"
    ],
    "tech": [
        "Internet harbiy loyiha edi",
        "AI tez rivojlanadi",
        "Telefon mini kompyuter",
        "Kod dunyoni boshqaradi",
        "Cloud tizim mavjud",
        "Serverlar 24/7",
        "Robotlar rivojlanadi",
        "Apps juda ko‘p",
        "Cyber security muhim",
        "Data juda qimmat"
    ],
    "history": [
        "Rim imperiyasi kuchli edi",
        "Kleopatra mashhur",
        "Vikinglar jangchi",
        "Piramidalar sirli",
        "Tarix boy",
        "Urushlar bo‘lgan",
        "Qirollar davri",
        "Imperiyalar qulagan",
        "Qadimiy shaharlar",
        "O‘tmish qiziq"
    ]
}

# ================= AI FAKE GENERATOR =================
def ai_fact():
    templates = [
        "🤖 {a} sababli {b} bo‘ladi",
        "🤖 Agar {a} bo‘lsa, {b} yuz beradi",
        "🤖 Ilmiy jihatdan {a} {b} bilan bog‘liq",
        "🤖 Tadqiqotlarga ko‘ra {a} juda muhim"
    ]

    a = random.choice([
        "inson miyasi", "koinot", "AI", "atomlar", "energiya", "tabiat"
    ])
    b = random.choice([
        "rivojlanish", "harakat", "o‘zgarish", "texnologiya", "hayot"
    ])

    return random.choice(templates).format(a=a, b=b)

# ================= STATE =================
state = {}

# ================= MENU =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech")
    kb.add("📜 History","🤖 AI Fact")
    kb.add("❤️ Saved","📊 Stats")
    kb.add("💎 Premium","🛠 Admin")
    return kb

# ================= SHOW =================
async def show(uid, chat_id):
    st = state[uid]
    cat = st["cat"]
    i = st["i"]

    fact = FACTS[cat][i]

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data="save"))

    await bot.send_message(chat_id, fact, reply_markup=kb)

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,0)", (m.from_user.id,))
    await m.answer("🚀 Fact Bot Ready", reply_markup=menu())

# ================= CATEGORY =================
@dp.message_handler()
async def h(m):
    uid = m.from_user.id
    t = m.text

    if "Science" in t: cat="science"
    elif "Tech" in t: cat="tech"
    elif "History" in t: cat="history"
    elif "AI Fact" in t:
        return await m.answer(ai_fact())
    elif "Saved" in t:
        return await saved(m)
    elif "Stats" in t:
        return await stats(m)
    elif "Premium" in t:
        return await premium(m)
    elif "Admin" in t:
        return await admin(m)
    else:
        return

    state[uid] = {"cat":cat,"i":0}
    await show(uid,m.chat.id)

# ================= NAV =================
@dp.callback_query_handler(lambda c:c.data in ["next","prev"])
async def nav(c):
    uid=c.from_user.id
    st=state.get(uid)
    if not st: return

    if c.data=="next":
        st["i"]=(st["i"]+1)%10
    else:
        st["i"]=(st["i"]-1)%10

    await show(uid,c.message.chat.id)

# ================= SAVE =================
@dp.callback_query_handler(lambda c:c.data=="save")
async def save(c):
    with db() as conn:
        conn.execute("INSERT INTO saved VALUES (?,?)",(c.from_user.id,c.message.text))
    await c.answer("❤️ Saved")

# ================= SAVED =================
@dp.message_handler(lambda m:"Saved" in m.text)
async def saved(m):
    with db() as c:
        rows=c.execute("SELECT text FROM saved WHERE uid=?",(m.from_user.id,)).fetchall()

    if not rows:
        return await m.answer("Empty")

    txt="❤️ SAVED:\n\n"
    for r in rows:
        txt+=f"• {r[0]}\n"

    await m.answer(txt)

# ================= STATS =================
@dp.message_handler(lambda m:"Stats" in m.text)
async def stats(m):
    with db() as c:
        count=c.execute("SELECT COUNT(*) FROM saved WHERE uid=?",(m.from_user.id,)).fetchone()[0]
    await m.answer(f"📊 Saved: {count}")

# ================= PREMIUM =================
@dp.message_handler(lambda m:"Premium" in m.text)
async def premium(m):
    with db() as c:
        c.execute("UPDATE users SET premium=1 WHERE id=?",(m.from_user.id,))
    await m.answer("💎 Premium activated")

# ================= ADMIN =================
@dp.message_handler(lambda m:"Admin" in m.text)
async def admin(m):
    if m.from_user.id!=ADMIN_ID:
        return await m.answer("No access")

    kb=types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Fact","📢 Post Channel")
    await m.answer("Admin panel",reply_markup=kb)

# ================= ADD FACT =================
@dp.message_handler(lambda m:"Add Fact" in m.text)
async def add(m):
    if m.from_user.id!=ADMIN_ID: return

    fact=ai_fact()

    with db() as c:
        c.execute("INSERT INTO facts (text) VALUES (?)",(fact,))

    await m.answer("Added ✔️")

# ================= CHANNEL POST =================
@dp.message_handler(commands=["post"])
async def post(m):
    if m.from_user.id!=ADMIN_ID: return

    fact=ai_fact()
    await bot.send_message(CHANNEL_ID,"📢 FACT\n\n"+fact)
    await m.answer("Posted")

# ================= WEB FIX =================
async def handle(r):
    return web.Response(text="OK")

async def web():
    app=web.Application()
    app.router.add_get("/",handle)

    runner=web.AppRunner(app)
    await runner.setup()

    site=web.TCPSite(runner,"0.0.0.0",int(os.getenv("PORT",10000)))
    await site.start()

async def on_startup(dp):
    asyncio.create_task(web())

# ================= RUN =================
if __name__=="__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)