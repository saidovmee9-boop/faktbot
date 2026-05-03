import os
import sqlite3
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiohttp import web

# =====================
# CONFIG
# =====================
TOKEN = os.getenv("BOT_TOKEN") or "PUT_TOKEN"
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# =====================
# DB
# =====================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        c = conn.cursor()

        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT, uz TEXT, ru TEXT, en TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS saved (uid INTEGER, fid INTEGER, UNIQUE(uid,fid))")

        # small but interesting facts (not boring spam)
        if c.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0:
            data = [
                ("science",
                 "Inson miyasi tunda ham ishlaydi",
                 "Мозг человека работает даже ночью",
                 "Human brain works even at night"),

                ("tech",
                 "Internet har sekundda millionlab ma’lumot uzatadi",
                 "Интернет передаёт миллионы данных каждую секунду",
                 "Internet transfers millions of data per second"),

                ("history",
                 "Misr piramidalari 4500 yil oldin qurilgan",
                 "Египетские пирамиды построены 4500 лет назад",
                 "Egypt pyramids built 4500 years ago")
            ]
            c.executemany("INSERT INTO facts (cat,uz,ru,en) VALUES (?,?,?,?)", data)

# =====================
# LANG SYSTEM
# =====================
def get_lang(uid):
    with db() as conn:
        r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
        return r[0] if r else "uz"

def set_lang(uid, lang):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (uid, lang))

# =====================
# TEXT GETTER
# =====================
def text(row, lang):
    return row[2] if lang=="uz" else row[3] if lang=="ru" else row[4]

# =====================
# FACT LOADER
# =====================
def load(cat):
    with db() as conn:
        rows = conn.execute("SELECT * FROM facts WHERE cat=?", (cat,)).fetchall()
        if not rows:
            return []
        return rows

# =====================
# STATE
# =====================
state = {}

# =====================
# MENU
# =====================
def menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science", "💻 Tech")
    kb.add("📜 History", "🎲 Random")
    kb.add("❤️ Saved", "🌐 Language")
    return kb

# =====================
# SHOW FACT
# =====================
async def show(call, uid):
    st = state.get(uid)
    if not st:
        return

    row = st["facts"][st["i"]]
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    ).add(
        InlineKeyboardButton("❤️ Save", callback_data=f"save_{row[0]}")
    )

    await call.message.edit_text(
        f"📚 <b>{st['cat'].upper()}</b>\n\n✨ {text(row,lang)}",
        parse_mode="HTML",
        reply_markup=kb
    )

# =====================
# START
# =====================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    set_lang(m.from_user.id, "uz")
    await m.answer("🚀 Welcome to Fact World!", reply_markup=menu())

# =====================
# CATEGORY HANDLER
# =====================
@dp.message_handler()
async def main(m: types.Message):
    uid = m.from_user.id
    t = m.text

    if "Science" in t: cat="science"
    elif "Tech" in t: cat="tech"
    elif "History" in t: cat="history"
    elif "Random" in t:
        cat = random.choice(["science","tech","history"])
    elif "Saved" in t:
        return await show_saved(m)
    elif "Language" in t:
        return await lang_menu(m)
    else:
        return

    facts = load(cat)
    if not facts:
        return await m.answer("No facts available")

    state[uid] = {"facts": facts, "i": 0, "cat": cat}

    row = facts[0]
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )

    await m.answer(
        f"📚 <b>{cat.upper()}</b>\n\n✨ {text(row,lang)}",
        parse_mode="HTML",
        reply_markup=kb
    )

# =====================
# NAVIGATION
# =====================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)

    if not st:
        return await c.answer("Start bot first", show_alert=True)

    if c.data == "next":
        st["i"] = (st["i"] + 1) % len(st["facts"])
    else:
        st["i"] = (st["i"] - 1) % len(st["facts"])

    await show(c, uid)

# =====================
# SAVE
# =====================
@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = c.data.split("_")[1]
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)", (c.from_user.id, fid))
    await c.answer("❤️ Saved!")

# =====================
# SAVED LIST
# =====================
async def show_saved(m):
    uid = m.from_user.id
    lang = get_lang(uid)

    with db() as conn:
        rows = conn.execute(
            "SELECT f.* FROM facts f JOIN saved s ON f.id=s.fid WHERE s.uid=?",
            (uid,)
        ).fetchall()

    if not rows:
        return await m.answer("No saved facts")

    for r in rows:
        await m.answer("❤️ " + text(r, lang))

# =====================
# LANGUAGE MENU
# =====================
async def lang_menu(m):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🇺🇿", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺", callback_data="lang_ru"),
        InlineKeyboardButton("🇺🇸", callback_data="lang_en"),
    )
    await m.answer("Choose language:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_lang_cb(c):
    lang = c.data.split("_")[1]
    set_lang(c.from_user.id, lang)
    await c.message.answer("✅ Language changed", reply_markup=menu())

# =====================
# RUN (RENDER SAFE)
# =====================
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)