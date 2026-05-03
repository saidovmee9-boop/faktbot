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
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =====================
# DB (ONLY SAVED)
# =====================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_id INTEGER)")

init_db()

# =====================
# FACTS (CLEAN + 10 EACH)
# =====================
FACTS = {
    "science": [
        (1,"Inson DNKsi banan bilan o‘xshash"),
        (2,"Miya uxlaganda ham ishlaydi"),
        (3,"Suv kosmosda muzlaydi"),
        (4,"Yurak 24/7 uradi"),
        (5,"Odam 70% suv"),
        (6,"Quyosh juda issiq"),
        (7,"Bakteriyalar tanada bor"),
        (8,"Yer aylanishda"),
        (9,"Miya super kuchli"),
        (10,"Koinot kengaymoqda")
    ],
    "tech": [
        (11,"Internet harbiy loyiha edi"),
        (12,"AI tez rivojlanadi"),
        (13,"Telefon mini kompyuter"),
        (14,"Kod dunyoni boshqaradi"),
        (15,"Cloud saqlash tizimi"),
        (16,"Serverlar 24/7 ishlaydi"),
        (17,"Robotlar rivojlanmoqda"),
        (18,"Apps millionlab"),
        (19,"Cyber security muhim"),
        (20,"Data juda qimmat")
    ],
    "history": [
        (21,"Rim imperiyasi kuchli edi"),
        (22,"Kleopatra mashhur malikasi"),
        (23,"Vikinglar jangchi edi"),
        (24,"Piramidalar sirli"),
        (25,"Tarix juda boy"),
        (26,"Urushlar bo‘lgan"),
        (27,"Qirollar davri"),
        (28,"Imperiyalar qulagan"),
        (29,"Qadimiy shaharlar"),
        (30,"O‘tmish qiziq")
    ]
}

# =====================
# STATE + LANG
# =====================
state = {}
lang = {}

def get_lang(uid):
    return lang.get(uid,"uz")

def tr(text, l):
    if l=="uz": return text
    if l=="ru": return "🇷🇺 "+text
    return "🇬🇧 "+text

# =====================
# MENU
# =====================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech")
    kb.add("📜 History","❤️ Saved")
    return kb

# =====================
# SHOW FACT
# =====================
async def show(uid, chat_id):
    st = state[uid]
    cat = st["cat"]
    i = st["i"]

    fact = FACTS[cat][i]
    l = get_lang(uid)

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(
        InlineKeyboardButton("❤️ Save", callback_data=f"save_{fact[0]}")
    )

    await bot.send_message(
        chat_id,
        f"📚 {cat.upper()}\n\n{tr(fact[1],l)}",
        reply_markup=kb
    )

# =====================
# START
# =====================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    lang[m.from_user.id] = "uz"
    await m.answer("🚀 Fact Bot", reply_markup=menu())

# =====================
# CATEGORY
# =====================
@dp.message_handler()
async def handler(m):
    uid = m.from_user.id
    t = m.text

    if "Science" in t:
        cat="science"
    elif "Tech" in t:
        cat="tech"
    elif "History" in t:
        cat="history"
    elif "Saved" in t:
        return await saved(m)
    else:
        return

    state[uid] = {"cat":cat,"i":0}
    await show(uid,m.chat.id)

# =====================
# NAV FIX (NO CRASH)
# =====================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)

    if not st:
        return await c.answer("Start bot")

    if c.data=="next":
        st["i"] = (st["i"]+1) % len(FACTS[st["cat"]])
    else:
        st["i"] = (st["i"]-1) % len(FACTS[st["cat"]])

    await show(uid, c.message.chat.id)

# =====================
# SAVE FIX (NO DUPLICATE LOSS)
# =====================
@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = int(c.data.split("_")[1])

    with db() as conn:
        conn.execute("INSERT INTO saved VALUES (?,?)",(c.from_user.id,fid))

    await c.answer("❤️ Saved")

# =====================
# SAVED FIX (FULL LIST)
# =====================
@dp.message_handler(lambda m:"Saved" in m.text or "❤️" in m.text)
async def saved(m):
    uid=m.from_user.id

    with db() as conn:
        rows=conn.execute("SELECT fact_id FROM saved WHERE user_id=?",(uid,)).fetchall()

    if not rows:
        return await m.answer("Empty ❤️")

    txt="❤️ SAVED:\n\n"

    for r in rows:
        fid=r[0]
        for cat in FACTS:
            for f in FACTS[cat]:
                if f[0]==fid:
                    txt+=f"• {f[1]}\n"

    await m.answer(txt)

# =====================
# WEB SERVER (RENDER SAFE)
# =====================
async def handle(r):
    return web.Response(text="OK")

async def web():
    app=web.Application()
    app.router.add_get("/",handle)
    runner=web.AppRunner(app)
    await runner.setup()
    site=web.TCPSite(runner,"0.0.0.0",10000)
    await site.start()

async def on_startup(dp):
    asyncio.create_task(web())

# =====================
# RUN
# =====================
if __name__=="__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)