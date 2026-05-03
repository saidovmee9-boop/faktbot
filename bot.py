import os
import sqlite3
import asyncio
import random
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

# ================= AI GENERATOR =================
subjects = [
    ("Odam miyasi","Мозг человека","Human brain"),
    ("Koinot","Вселенная","Universe"),
    ("Sun’iy intellekt","Искусственный интеллект","Artificial intelligence"),
    ("Texnologiya","Технологии","Technology"),
    ("Yer sayyorasi","Планета Земля","Planet Earth")
]

actions = [
    ("doim o‘rganadi","постоянно учится","is constantly learning"),
    ("cheksiz rivojlanadi","развивается бесконечно","evolves endlessly"),
    ("sirli qolmoqda","остается загадкой","remains a mystery"),
    ("kutilmagan imkoniyatlarga ega","имеет неожиданные возможности","has unexpected capabilities"),
    ("insonni hayratda qoldiradi","удивляет человека","amazes humans")
]

extras = [
    ("va hali to‘liq o‘rganilmagan","и до конца не изучен","and is not fully understood"),
    ("va bu faqat boshlanishi","и это только начало","and this is just the beginning"),
    ("va kelajakni o‘zgartiradi","и изменит будущее","and will change the future"),
    ("va har kuni yangilanmoqda","и обновляется каждый день","and updates every day"),
    ("va insoniyat uchun muhim","и важно для человечества","and is important for humanity")
]

def generate_ai_fact():
    s = random.choice(subjects)
    a = random.choice(actions)
    e = random.choice(extras)
    return (
        f"{s[0]} {a[0]} {e[0]}",
        f"{s[1]} {a[1]} {e[1]}",
        f"{s[2]} {a[2]} {e[2]}"
    )

# ================= STATE =================
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

# ================= SHOW (FIXED) =================
async def show(uid, chat_id, edit=False):
    st = state[uid]
    cat = st["cat"]
    i = st["i"]

    # AI MIX
    if random.random() < 0.4:
        fact = generate_ai_fact()
    else:
        fact = FACTS[cat][i]

    text = f"🇺🇿 {fact[0]}\n🇷🇺 {fact[1]}\n🇬🇧 {fact[2]}"

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data="save"))

    # 🔥 FIXED EDIT LOGIC
    if edit and st.get("msg_id"):
        try:
            await bot.edit_message_text(
                text,
                chat_id,
                st["msg_id"],
                reply_markup=kb
            )
            return
        except:
            pass

    msg = await bot.send_message(chat_id, text, reply_markup=kb)
    st["msg_id"] = msg.message_id

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 Ultimate Fact Bot", reply_markup=menu())

# ================= CATEGORY (FIXED) =================
@dp.message_handler(lambda m: m.text in ["🔬 Science","💻 Tech","📜 History"])
async def cat_handler(m):
    uid = m.from_user.id

    if "Science" in m.text:
        cat = "science"
    elif "Tech" in m.text:
        cat = "tech"
    else:
        cat = "history"

    # 🔥 HAR BO‘LIM UCHUN YANGI STATE
    state[uid] = {
        "cat": cat,
        "i": 0,
        "msg_id": None
    }

    await show(uid, m.chat.id, edit=False)

# ================= NAV (FIXED) =================
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

# ================= SAVE =================
@dp.callback_query_handler(lambda c: c.data == "save")
async def save(c):
    try:
        with db() as conn:
            conn.execute("INSERT INTO saved VALUES (?,?)",
                         (c.from_user.id, c.message.text))
        await c.answer("❤️ Saved")
    except:
        await c.answer("❗ Already saved")

# ================= SAVED =================
@dp.message_handler(lambda m: "Saved" in m.text or "❤️" in m.text)
async def saved(m):
    with db() as c:
        rows = c.execute("SELECT text FROM saved WHERE uid=?",
                         (m.from_user.id,)).fetchall()

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