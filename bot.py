import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from openai import OpenAI

# ======================
# TOKENS (NO ENV REQUIRED)
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "PUT_TOKEN_HERE"
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or "PUT_OPENAI_KEY_HERE"

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

        # demo facts
        if c.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0:
            demo = [
                ("science","Suv 100°C da qaynaydi","Вода кипит при 100°C","Water boils at 100°C"),
                ("tech","Internet global tarmoq","Интернет глобальная сеть","Internet is global network"),
                ("history","Rim imperiyasi katta edi","Римская империя была большой","Roman empire was large")
            ]
            c.executemany("INSERT INTO facts (cat,uz,ru,en) VALUES (?,?,?,?)", demo)

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
# AI FACT (SAFE)
# ======================
def ai_fact(cat):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role":"user",
                "content":f"1 short {cat} fact in format uz|ru|en"
            }]
        )

        parts = res.choices[0].message.content.split("|")

        if len(parts) < 3:
            raise Exception("bad AI output")

        return (cat, parts[0].strip(), parts[1].strip(), parts[2].strip())

    except:
        return (cat, "AI fakt", "AI факт", "AI fact")

# ======================
# FACT LOAD
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
    await m.answer("🚀 Bot ishga tushdi", reply_markup=menu())

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
        InlineKeyboardButton("⬅️", callback_data="prev"),
        InlineKeyboardButton("➡️", callback_data="next")
    )

    await m.answer(
        f"📚 {cat.upper()}\n\n{get_text(row,lang)}",
        reply_markup=kb
    )

# ======================
# NAVIGATION
# ======================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)

    if not st:
        return await c.answer("Start qiling /start", show_alert=True)

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

    await c.answer("❤️ Saved!")

# ======================
# RUN
# ======================
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)