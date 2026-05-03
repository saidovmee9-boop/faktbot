import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# ======================
# CONFIG
# ======================
TOKEN = os.getenv("BOT_TOKEN") or "PUT_TOKEN"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ======================
# DB
# ======================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        c = conn.cursor()

        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT, uz TEXT, ru TEXT, en TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS saved (uid INTEGER, fid INTEGER, UNIQUE(uid,fid))")

        if c.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0:
            data = [
                ("science","Miya uxlayotganda ham ishlaydi","Мозг работает во сне","Brain works during sleep"),
                ("tech","Internet global tarmoq","Интернет глобальная сеть","Internet is global network"),
                ("history","Piramidalar qadimiy","Пирамиды древние","Pyramids are ancient")
            ]
            c.executemany("INSERT INTO facts (cat,uz,ru,en) VALUES (?,?,?,?)", data)

# ======================
# LANG
# ======================
def get_lang(uid):
    with db() as conn:
        r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
        return r[0] if r else "uz"

def set_lang(uid,l):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (uid,l))

def t(row, lang):
    return row[2] if lang=="uz" else row[3] if lang=="ru" else row[4]

# ======================
# STATE
# ======================
state = {}

# ======================
# MENU
# ======================
def menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech")
    kb.add("📜 History","🎲 Random")
    kb.add("❤️ Saved","🌐 Language")
    return kb

# ======================
# LOAD FACTS
# ======================
def load(cat):
    with db() as conn:
        return conn.execute("SELECT * FROM facts WHERE cat=?", (cat,)).fetchall()

# ======================
# SHOW FACT (FIXED)
# ======================
async def show(c, uid):
    st = state.get(uid)
    if not st:
        return

    row = st["facts"][st["i"]]
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️", callback_data="prev"),
        InlineKeyboardButton("➡️", callback_data="next")
    ).add(
        InlineKeyboardButton("❤️ Save", callback_data=f"save_{row[0]}")
    )

    try:
        await c.message.edit_text(
            f"📚 {st['cat'].upper()}\n\n✨ {t(row,lang)}",
            reply_markup=kb
        )
    except:
        pass  # Render-safe silent fix

# ======================
# START
# ======================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    set_lang(m.from_user.id,"uz")
    await m.answer("🚀 Bot ishlayapti", reply_markup=menu())

# ======================
# MAIN
# ======================
@dp.message_handler()
async def main(m: types.Message):
    uid = m.from_user.id
    txt = m.text

    if "Science" in txt: cat="science"
    elif "Tech" in txt: cat="tech"
    elif "History" in txt: cat="history"
    elif "Random" in txt:
        import random
        cat = random.choice(["science","tech","history"])
    elif "Saved" in txt:
        return await show_saved(m)
    elif "Language" in txt:
        return await lang_menu(m)
    else:
        return

    facts = load(cat)
    if not facts:
        return await m.answer("No facts")

    state[uid] = {"facts":facts,"i":0,"cat":cat}

    row = facts[0]
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️", callback_data="prev"),
        InlineKeyboardButton("➡️", callback_data="next")
    )

    await m.answer(
        f"📚 {cat.upper()}\n\n✨ {t(row,lang)}",
        reply_markup=kb
    )

# ======================
# NAV
# ======================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)

    if not st:
        return await c.answer("Start bot", show_alert=True)

    if c.data == "next":
        st["i"] = (st["i"] + 1) % len(st["facts"])
    else:
        st["i"] = (st["i"] - 1) % len(st["facts"])

    await show(c, uid)

# ======================
# SAVE
# ======================
@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = c.data.split("_")[1]
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)", (c.from_user.id,fid))
    await c.answer("❤️ Saved")

# ======================
# SAVED
# ======================
async def show_saved(m):
    uid = m.from_user.id
    lang = get_lang(uid)

    with db() as conn:
        rows = conn.execute("SELECT f.* FROM facts f JOIN saved s ON f.id=s.fid WHERE s.uid=?", (uid,)).fetchall()

    if not rows:
        return await m.answer("Empty")

    for r in rows:
        await m.answer("❤️ " + t(r,lang))

# ======================
# LANGUAGE
# ======================
async def lang_menu(m):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("UZ", callback_data="lang_uz"),
        InlineKeyboardButton("RU", callback_data="lang_ru"),
        InlineKeyboardButton("EN", callback_data="lang_en")
    )
    await m.answer("Lang:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_lang_cb(c):
    set_lang(c.from_user.id, c.data.split("_")[1])
    await c.message.answer("OK", reply_markup=menu())

# ======================
# RUN (RENDER SAFE)
# ======================
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)