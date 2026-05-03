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
# DB
# =====================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_id INTEGER)")

init_db()

# =====================
# FACTS
# =====================
FACTS = {
    "science": [(1,"Inson DNKsi bananga o‘xshash"),(2,"Miya uxlaganda ham ishlaydi"),(3,"Suv muzlaydi")],
    "tech": [(10,"Internet harbiy loyiha"),(11,"AI rivojlanadi"),(12,"Phone mini PC")],
    "history": [(20,"Rim imperiyasi"),(21,"Kleopatra"),(22,"Vikinglar")]
}

# =====================
# STATE
# =====================
state = {}

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

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data=f"save_{fact[0]}"))

    await bot.send_message(chat_id, f"📚 {fact[1]}", reply_markup=kb)

# =====================
# START
# =====================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 Bot ready", reply_markup=menu())

# =====================
# CATEGORY
# =====================
@dp.message_handler()
async def h(m):
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
# NAV FIX
# =====================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)
    if not st:
        return await c.answer("Start bot")

    if c.data=="next":
        st["i"]=(st["i"]+1)%len(FACTS[st["cat"]])
    else:
        st["i"]=(st["i"]-1)%len(FACTS[st["cat"]])

    await show(uid,c.message.chat.id)

# =====================
# SAVE FIX
# =====================
@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = int(c.data.split("_")[1])

    with db() as conn:
        conn.execute("INSERT INTO saved VALUES (?,?)",(c.from_user.id,fid))

    await c.answer("❤️ Saved")

# =====================
# SAVED FIX (FULL)
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
# WEB SERVER (CRITICAL FIX)
# =====================
async def handle(request):
    return web.Response(text="OK")

def start_web():
    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)

    async def _run():
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT",10000)))
        await site.start()

    loop = asyncio.get_event_loop()
    loop.create_task(_run())

# =====================
# STARTUP FIX (NO CRASH)
# =====================
async def on_startup(dp):
    start_web()

# =====================
# RUN
# =====================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)