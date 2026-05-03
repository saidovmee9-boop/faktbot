import os
import sqlite3
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS saved (
            uid INTEGER,
            text TEXT,
            UNIQUE(uid, text)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            uid INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
        """)
init_db()

# ================= FACTS =================
FACTS = {
    "science": [
        ("DNK bananga o‘xshaydi","ДНК как банан","DNA like banana"),
        ("Miya uxlaydi ham ishlaydi","Мозг работает во сне","Brain works in sleep"),
        ("Suv kosmosda muzlaydi","Вода в космосе замерзает","Water freezes in space"),
        ("Yurak doim ishlaydi","Сердце всегда работает","Heart always works"),
        ("Odam 70% suv","Человек 70% вода","Human is 70% water"),
    ],
    "tech": [
        ("Internet harbiy loyiha edi","Интернет был военным проектом","Internet was a military project"),
        ("AI rivojlanmoqda","ИИ развивается","AI is evolving"),
        ("Telefon mini kompyuter","Телефон мини ПК","Phone is mini PC"),
        ("Kod dunyoni boshqaradi","Код управляет миром","Code runs the world"),
        ("Cloud tizim bor","Облачные системы","Cloud systems exist"),
    ],
    "history": [
        ("Rim imperiyasi kuchli edi","Римская империя была сильной","Roman Empire was strong"),
        ("Kleopatra mashhur edi","Клеопатра была известной","Cleopatra was famous"),
        ("Vikinglar jangchi edi","Викинги были воинами","Vikings were warriors"),
        ("Piramidalar sirli","Пирамиды загадка","Pyramids are mysterious"),
        ("Tarix juda boy","История богата","History is rich"),
    ]
}

state = {}

# ================= MENU =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech")
    kb.add("📜 History")
    kb.add("❤️ Saved","📊 Stats")
    return kb

# ================= STATS =================
def add_stat(uid):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO stats VALUES (?,0)", (uid,))
        c.execute("UPDATE stats SET count = count + 1 WHERE uid=?", (uid,))

def get_stat(uid):
    with db() as c:
        r = c.execute("SELECT count FROM stats WHERE uid=?", (uid,)).fetchone()
        return r[0] if r else 0

# ================= SHOW =================
async def show(uid, chat_id, edit=False):
    st = state[uid]
    cat = st["cat"]
    i = st["i"]

    fact = FACTS[cat][i]
    text = f"🇺🇿 {fact[0]}\n🇷🇺 {fact[1]}\n🇬🇧 {fact[2]}"

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data="save"))

    if edit:
        try:
            await bot.edit_message_text(
                text,
                chat_id,
                state[uid]["msg_id"],
                reply_markup=kb
            )
            return
        except:
            pass

    msg = await bot.send_message(chat_id, text, reply_markup=kb)
    state[uid]["msg_id"] = msg.message_id

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 Fact Bot Ready", reply_markup=menu())

# ================= CATEGORY =================
@dp.message_handler(lambda m: m.text in ["🔬 Science","💻 Tech","📜 History"])
async def cat_handler(m):
    uid = m.from_user.id

    if "Science" in m.text:
        cat = "science"
    elif "Tech" in m.text:
        cat = "tech"
    else:
        cat = "history"

    state[uid] = {"cat":cat,"i":0}
    await show(uid, m.chat.id)

# ================= NAV =================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)
    if not st:
        return await c.answer()

    if c.data == "next":
        st["i"] = (st["i"] + 1) % len(FACTS[st["cat"]])
    else:
        st["i"] = (st["i"] - 1) % len(FACTS[st["cat"]])

    add_stat(uid)
    await show(uid, c.message.chat.id, edit=True)
    await c.answer()

# ================= SAVE (FIXED) =================
@dp.callback_query_handler(lambda c: c.data == "save")
async def save(c):
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO saved VALUES (?,?)",
                (c.from_user.id, c.message.text)
            )
        await c.answer("❤️ Saved")
    except:
        await c.answer("❗ Already saved")

# ================= SAVED =================
@dp.message_handler(lambda m: "Saved" in m.text or "❤️" in m.text)
async def saved(m):
    with db() as c:
        rows = c.execute("SELECT text FROM saved WHERE uid=?", (m.from_user.id,)).fetchall()

    if not rows:
        return await m.answer("Empty")

    txt = "❤️ SAVED:\n\n" + "\n\n".join(r[0] for r in rows)
    await m.answer(txt)

# ================= STATS =================
@dp.message_handler(lambda m: "Stats" in m.text)
async def stats(m):
    count = get_stat(m.from_user.id)
    await m.answer(f"📊 Ko‘rilgan faktlar: {count}")

# ================= WEB =================
async def handle(r):
    return web.Response(text="OK")

async def web_app():
    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()

async def on_startup(dp):
    asyncio.create_task(web_app())

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)