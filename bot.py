import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# =========================
# 🔑 HARD-CODE FALLBACK (ENV shart EMAS)
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "PASTE_YOUR_TOKEN_HERE"
PORT = int(os.getenv("PORT") or 10000)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# =========================
# DB
# =========================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT, uz TEXT, ru TEXT, en TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS saved (uid INTEGER, fid INTEGER, UNIQUE(uid,fid))")

        if c.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0:
            sample = []
            for i in range(1, 21):
                sample.append(("science", f"Suv fakt {i}", f"Факт вода {i}", f"Water fact {i}"))
                sample.append(("tech", f"Tech fakt {i}", f"Тех факт {i}", f"Tech fact {i}"))
                sample.append(("history", f"Tarix fakt {i}", f"История {i}", f"History fact {i}"))
            c.executemany("INSERT INTO facts (cat,uz,ru,en) VALUES (?,?,?,?)", sample)

# =========================
# LANG
# =========================
def get_lang(uid):
    with db() as conn:
        r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
        return r[0] if r else "uz"

def set_lang(uid, l):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (uid, l))

STR = {
    "uz": {"save":"❤️ Saqlash","saved":"❤️ Saqlanganlar","lang":"🌐 Til","empty":"Bo'sh"},
    "ru": {"save":"❤️ Сохранить","saved":"❤️ Избранное","lang":"🌐 Язык","empty":"Пусто"},
    "en": {"save":"❤️ Save","saved":"❤️ Saved","lang":"🌐 Language","empty":"Empty"}
}

# =========================
# STATE (prev/next)
# =========================
state = {}

def load(cat):
    with db() as conn:
        rows = conn.execute("SELECT * FROM facts WHERE cat=?", (cat,)).fetchall()
        return rows

def get_text(row, lang):
    return row[2] if lang=="uz" else row[3] if lang=="ru" else row[4]

# =========================
# MENU
# =========================
def menu(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech","📜 History")
    kb.add("🎲 Random","❤️ Saved")
    kb.add("🌐 Til")
    return kb

# =========================
# SHOW FACT
# =========================
async def show(call, uid):
    st = state[uid]
    row = st["facts"][st["i"]]
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️",callback_data="prev"),
        InlineKeyboardButton("➡️",callback_data="next")
    ).add(
        InlineKeyboardButton(STR[lang]["save"], callback_data=f"save_{row[0]}")
    )

    await call.message.edit_text(
        f"📚 {st['cat'].upper()}\n\n{get_text(row,lang)}",
        reply_markup=kb
    )

# =========================
# START
# =========================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    set_lang(m.from_user.id,"uz")
    await m.answer("🚀 Bot tayyor", reply_markup=menu(m.from_user.id))

# =========================
# CATEGORY
# =========================
@dp.message_handler()
async def main(m: types.Message):
    uid = m.from_user.id
    t = m.text

    if "Science" in t: cat="science"
    elif "Tech" in t: cat="tech"
    elif "History" in t: cat="history"
    elif "Random" in t: cat="science"
    elif "Saved" in t: return await show_saved(m)
    else: return

    facts = load(cat)

    if not facts:
        return await m.answer("No facts")

    state[uid] = {"facts":facts,"i":0,"cat":cat}

    row = facts[0]

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️",callback_data="prev"),
        InlineKeyboardButton("➡️",callback_data="next")
    )

    await m.answer(f"📚 {cat.upper()}\n\n{get_text(row,get_lang(uid))}", reply_markup=kb)

# =========================
# NAVIGATION
# =========================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)
    if not st:
        return

    if c.data == "next":
        st["i"] = (st["i"] + 1) % len(st["facts"])
    else:
        st["i"] = (st["i"] - 1) % len(st["facts"])

    await show(c, uid)

# =========================
# SAVE
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = c.data.split("_")[1]
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)",(c.from_user.id,fid))
    await c.answer("❤️ Saved!")

# =========================
# SAVED
# =========================
async def show_saved(m):
    uid = m.from_user.id
    lang = get_lang(uid)

    with db() as conn:
        rows = conn.execute(
            "SELECT f.* FROM facts f JOIN saved s ON f.id=s.fid WHERE s.uid=?",
            (uid,)
        ).fetchall()

    if not rows:
        return await m.answer(STR[lang]["empty"])

    for r in rows:
        await m.answer("❤️ " + get_text(r,lang))

# =========================
# RUN
# =========================
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)