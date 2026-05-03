import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# 🔑 TOKENS
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🔌 INIT
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- DB ---
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT, uz TEXT, ru TEXT, en TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS saved (uid INTEGER, fid INTEGER, UNIQUE(uid,fid))")

# --- LANG ---
STR = {
    "uz": {"saved":"❤️ Saqlanganlar","save":"❤️ Saqlash","lang":"🌐 Til","empty":"Bo'sh"},
    "ru": {"saved":"❤️ Избранное","save":"❤️ Сохранить","lang":"🌐 Язык","empty":"Пусто"},
    "en": {"saved":"❤️ Saved","save":"❤️ Save","lang":"🌐 Language","empty":"Empty"}
}

def get_lang(uid):
    with db() as conn:
        r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
        return r[0] if r else "uz"

def set_lang(uid,l):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)",(uid,l))

# --- SAFE AI (optional) ---
def generate_fact(cat):
    try:
        if not OPENAI_API_KEY:
            raise Exception("no key")

        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role":"user",
                "content":f"Give 1 short {cat} fact in Uzbek|Russian|English separated by |"
            }]
        )

        txt = res.choices[0].message.content.split("|")
        return (cat, txt[0].strip(), txt[1].strip(), txt[2].strip())

    except:
        # fallback (HECH QACHON CRASH BO‘LMAYDI)
        return (cat,
                "AI fakt ishlamadi",
                "AI факт не работает",
                "AI failed")

# --- MENU ---
def menu(uid):
    l = get_lang(uid)
    s = STR[l]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech","📜 History")
    kb.add("🎲 Random", s["saved"])
    kb.add(s["lang"])
    return kb

# --- STATE ---
state = {}

# --- LOAD FACTS ---
def load(cat):
    with db() as conn:
        rows = conn.execute("SELECT * FROM facts WHERE cat=?", (cat,)).fetchall()

        if not rows:
            new = generate_fact(cat)
            conn.execute("INSERT INTO facts (cat,uz,ru,en) VALUES (?,?,?,?)", new)
            rows = conn.execute("SELECT * FROM facts WHERE cat=?", (cat,)).fetchall()

        return rows

def get_text(row,lang):
    return row[2] if lang=="uz" else row[3] if lang=="ru" else row[4]

# --- SHOW ---
async def show(call, uid):
    if uid not in state:
        return

    st = state[uid]
    row = st["facts"][st["i"]]
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️",callback_data="prev"),
        InlineKeyboardButton("➡️",callback_data="next")
    ).add(
        InlineKeyboardButton(STR[lang]["save"],callback_data=f"save_{row[0]}")
    )

    await call.message.edit_text(
        f"📚 {st['cat'].upper()}\n\n{get_text(row,lang)}",
        reply_markup=kb
    )

# --- HANDLERS ---
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    set_lang(m.from_user.id,"uz")
    await m.answer("🚀 Bot ishga tushdi", reply_markup=menu(m.from_user.id))

@dp.message_handler(lambda m: m.text in ["🌐 Til","🌐 Язык","🌐 Language"])
async def lang(m):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("UZ",callback_data="l_uz"),
        InlineKeyboardButton("RU",callback_data="l_ru"),
        InlineKeyboardButton("EN",callback_data="l_en")
    )
    await m.answer("Choose language:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("l_"))
async def set_l(c):
    l = c.data.split("_")[1]
    set_lang(c.from_user.id,l)
    await c.message.answer("✅", reply_markup=menu(c.from_user.id))

@dp.message_handler()
async def main(m: types.Message):
    uid = m.from_user.id
    t = m.text

    if "Science" in t: cat="science"
    elif "Tech" in t: cat="tech"
    elif "History" in t: cat="history"
    elif "Random" in t: cat="science"
    elif "Saved" in t or "Избран" in t or "Saqlangan" in t:
        return await show_saved(m)
    else:
        return

    facts = load(cat)
    state[uid] = {"facts":facts,"i":0,"cat":cat}

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️",callback_data="prev"),
        InlineKeyboardButton("➡️",callback_data="next")
    )

    await m.answer(
        f"📚 {cat.upper()}\n\n{get_text(facts[0],get_lang(uid))}",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id

    if uid not in state:
        return await c.answer("Boshlang /start", show_alert=True)

    st = state[uid]

    if c.data=="next":
        st["i"] = (st["i"]+1) % len(st["facts"])
    else:
        st["i"] = (st["i"]-1) % len(st["facts"])

    await show(c, uid)

@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = c.data.split("_")[1]
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)",(c.from_user.id,fid))
    await c.answer("❤️ Saved!")

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
        await m.answer("❤️ "+get_text(r,lang))

# --- RUN ---
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)