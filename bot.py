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
TOKEN = os.getenv("BOT_TOKEN") or "PUT_TOKEN_HERE"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =====================
# DB
# =====================
def db():
    return sqlite3.connect("fact.db")

def init_db():
    with db() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_id INTEGER, UNIQUE(user_id,fact_id))")

init_db()

# =====================
# FACTS (qiziqarli + ko‘paytirilgan)
# =====================
facts = {
    "science": [
        (1, "🧬 Inson DNKsi 60% banan bilan o‘xshash."),
        (2, "🧠 Miya 24/7 ishlaydi, hatto uxlaganda ham."),
        (3, "🌍 Yer doimiy harakatda, lekin biz sezmaymiz."),
        (4, "⚡ Chaqmoq Quyosh yuzasidan ham issiq bo‘lishi mumkin."),
    ],
    "tech": [
        (10, "💻 Internet dastlab harbiy loyiha edi."),
        (11, "📱 Birinchi telefon 1 kg dan og‘ir edi."),
        (12, "🤖 AI hozir millionlab qarorlarni sekundda qiladi."),
    ],
    "history": [
        (20, "🏛 Rim imperiyasi 500+ yil yashagan."),
        (21, "📜 Kleopatra piramidalardan yaqinroq davrda yashagan."),
        (22, "⚔️ Vikinglar Yevropani asrlar davomida qo‘rqitgan."),
    ]
}

# =====================
# LANG SYSTEM
# =====================
def get_lang(uid):
    return user_lang.get(uid, "uz")

user_lang = {}

def translate(text, lang):
    if lang == "uz":
        return text
    if lang == "ru":
        return "🇷🇺 " + text
    if lang == "en":
        return "🇬🇧 " + text

# =====================
# STATE
# =====================
state = {}

# =====================
# MENU
# =====================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science", "💻 Tech")
    kb.add("📜 History", "🎲 Random")
    kb.add("❤️ Saved", "🌐 Language")
    return kb

# =====================
# FACT GET
# =====================
def get_fact(cat, idx):
    return facts[cat][idx]

# =====================
# SHOW FACT
# =====================
async def show(uid, chat_id):
    st = state[uid]
    cat = st["cat"]
    idx = st["i"]

    fact = get_fact(cat, idx)
    lang = get_lang(uid)

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
        f"📚 <b>{cat.upper()}</b>\n\n{translate(fact[1], lang)}",
        parse_mode="HTML",
        reply_markup=kb
    )

# =====================
# START
# =====================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    user_lang[m.from_user.id] = "uz"
    await m.answer("🚀 Fact Bot", reply_markup=menu())

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
        cat = random.choice(list(facts.keys()))
    elif "Saved" in t:
        return await saved(m)
    elif "Language" in t:
        return await lang_menu(m)
    else:
        return

    state[uid] = {"cat": cat, "i": 0}
    await show(uid, m.chat.id)

# =====================
# NAVIGATION (FIXED)
# =====================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)

    if not st:
        return await c.answer("Start bot")

    if c.data == "next":
        st["i"] = (st["i"] + 1) % len(facts[st["cat"]])
    else:
        st["i"] = (st["i"] - 1) % len(facts[st["cat"]])

    cat = st["cat"]
    idx = st["i"]
    fact = get_fact(cat, idx)
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(
        InlineKeyboardButton("❤️ Save", callback_data=f"save_{fact[0]}")
    )

    await c.message.edit_text(
        f"📚 <b>{cat.upper()}</b>\n\n{translate(fact[1], lang)}",
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

    await c.answer("❤️ Saved!")

# =====================
# SAVED LIST (FIXED FULL)
# =====================
async def saved(m):
    uid = m.from_user.id
    lang = get_lang(uid)

    saved_ids = []

    with db() as conn:
        rows = conn.execute("SELECT fact_id FROM saved WHERE user_id=?", (uid,)).fetchall()
        saved_ids = [r[0] for r in rows]

    if not saved_ids:
        return await m.answer("❤️ Empty")

    text = "❤️ SAVED FACTS:\n\n"

    for cat in facts:
        for f in facts[cat]:
            if f[0] in saved_ids:
                text += f"• {translate(f[1], lang)}\n"

    await m.answer(text)

# =====================
# LANGUAGE
# =====================
user_lang_map = {}

async def lang_menu(m):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("UZ", callback_data="lang_uz"),
        InlineKeyboardButton("RU", callback_data="lang_ru"),
        InlineKeyboardButton("EN", callback_data="lang_en")
    )
    await m.answer("🌐 Choose language", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_lang(c):
    user_lang[c.from_user.id] = c.data.split("_")[1]
    await c.message.answer("✅ Language updated", reply_markup=menu())

# =====================
# WEB SERVER (RENDER FIX)
# =====================
async def handle(request):
    return web.Response(text="Bot running")

async def web_start():
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
    asyncio.create_task(web_start())

# =====================
# RUN
# =====================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)