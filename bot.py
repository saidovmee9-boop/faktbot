import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from openai import OpenAI

# ======================
# 🔑 TOKENS (ENV OR HARD)
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "PASTE_BOT_TOKEN"
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or "PASTE_OPENAI_KEY"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

client = OpenAI(api_key=OPENAI_KEY)

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

# ======================
# LANG
# ======================
def get_lang(uid):
    with db() as conn:
        r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
        return r[0] if r else "uz"

def set_lang(uid, l):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (uid, l))

# ======================
# AI FACT (OPENAI 1.3.5 FIXED)
# ======================
def ai_fact(cat):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"Give 1 short {cat} fact in Uzbek|Russian|English format separated by |"
                }
            ]
        )

        text = res.choices[0].message.content.split("|")

        return (
            cat,
            text[0].strip(),
            text[1].strip(),
            text[2].strip()
        )

    except:
        # fallback (bot NEVER crashes)
        return (cat, "AI fakt", "AI факт", "AI fact")

# ======================
# FACTS
# ======================
def load(cat):
    with db() as conn:
        rows = conn.execute("SELECT * FROM facts WHERE cat=?", (cat,)).fetchall()

        if not rows:
            new = ai_fact(cat)
            conn.execute("INSERT INTO facts (cat,uz,ru,en) VALUES (?,?,?,?)", new)
            rows = conn.execute("SELECT * FROM facts WHERE cat=?", (cat,)).fetchall()

        return rows

def get_text(row, lang):
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
    kb.add("🔬 Science","💻 Tech","📜 History")
    kb.add("🎲 Random","❤️ Saved")
    return kb

# ======================
# SHOW FACT
# ======================
async def show(call, uid):
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

    await call.message.edit_text(
        f"📚 {st['cat'].upper()}\n\n{get_text(row,lang)}",
        reply_markup=kb
    )

# ======================
# START
# ======================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    set_lang(m.from_user.id,"uz")
    await m.answer("🚀 Bot tayyor", reply_markup=menu())

# ======================
# MAIN
# ======================
@dp.message_handler()
async def main(m: types.Message):
    uid = m.from_user.id
    t = m.text

    if "Science" in t: cat="science"
    elif "Tech" in t: cat="tech"
    elif "History" in t: cat="history"
    elif "Random" in t: cat="science"
    else: return

    facts = load(cat)

    state[uid] = {
        "facts": facts,
        "i": 0,
        "cat": cat
    }

    row = facts[0]
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️",callback_data="prev"),
        InlineKeyboardButton("➡️",callback_data="next")
    )

    await m.answer(
        f"📚 {cat.upper()}\n\n{get_text(row,lang)}",
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
        return

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
        conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)",(c.from_user.id,fid))
    await c.answer("❤️ Saved!")

# ======================
# RUN (RENDER SAFE)
# ======================
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)