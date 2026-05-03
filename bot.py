import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiohttp import web

API_TOKEN = os.environ.get("BOT_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- DB ---
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, cat TEXT, uz TEXT, ru TEXT, en TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS history (uid INTEGER, fid INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS saved (uid INTEGER, fid INTEGER)")

        if c.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0:
            facts = [
                ("science","Suv 100°C da qaynaydi","Вода кипит при 100°C","Water boils at 100°C"),
                ("science","Yer Quyosh atrofida aylanadi","Земля вращается вокруг Солнца","Earth orbits the Sun"),
                ("tech","Internet 1960-yillarda yaratilgan","Интернет создан в 1960-х","Internet was created in 1960s"),
                ("tech","AI rivojlanmoqda","ИИ развивается","AI is growing"),
                ("history","Rim imperiyasi katta bo'lgan","Римская империя была большой","Roman Empire was huge"),
                ("history","Misr piramidalari qadimiy","Пирамиды древние","Pyramids are ancient")
            ]
            c.executemany("INSERT INTO facts (cat,uz,ru,en) VALUES (?,?,?,?)", facts)

# --- HELPERS ---
def get_lang(uid):
    with db() as conn:
        r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
        return r[0] if r else "uz"

def set_lang(uid,l):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)",(uid,l))

def get_text(row,lang):
    return row[2] if lang=="uz" else row[3] if lang=="ru" else row[4]

# --- AI FACT ---
def ai_fact(cat):
    return (
        cat,
        "AI yangi fakt (UZ)",
        "Новый факт от AI",
        "New AI fact"
    )

# --- MENU ---
def menu(l):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech","📜 History")
    kb.add("🎲 Random","❤️ Saved")
    kb.add("🌐 Language")
    return kb

# --- STATE (TEMP MEMORY) ---
user_state = {}

# --- FACT LOAD ---
def load_facts(cat):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM facts WHERE cat=? ORDER BY RANDOM()",
            (cat,)
        ).fetchall()

        if not rows:
            new = ai_fact(cat)
            conn.execute("INSERT INTO facts (cat,uz,ru,en) VALUES (?,?,?,?)", new)
            rows = conn.execute("SELECT * FROM facts WHERE cat=?", (cat,)).fetchall()

        return rows

# --- SHOW FACT ---
async def show_fact(call, uid):
    st = user_state[uid]
    row = st["facts"][st["index"]]
    lang = get_lang(uid)

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️", callback_data="prev"),
        InlineKeyboardButton("➡️", callback_data="next")
    ).add(
        InlineKeyboardButton("❤️ Save", callback_data=f"save_{row[0]}")
    )

    await call.message.edit_text(
        f"📚 {st['cat'].upper()}\n\n📌 {get_text(row,lang)}",
        reply_markup=kb
    )

# --- HANDLERS ---
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    set_lang(m.from_user.id,"uz")
    await m.answer("🌟 Xush kelibsiz", reply_markup=menu("uz"))

@dp.message_handler()
async def main(m: types.Message):
    uid = m.from_user.id
    text = m.text

    if "Science" in text:
        cat = "science"
    elif "Tech" in text:
        cat = "tech"
    elif "History" in text:
        cat = "history"
    elif "Random" in text:
        cat = "science"
    elif "Saved" in text:
        return await m.answer("Saved hali simple qoldirdim")
    elif "Language" in text:
        return await m.answer("Til almashtirish hali bor")

    facts = load_facts(cat)

    user_state[uid] = {
        "facts": facts,
        "index": 0,
        "cat": cat
    }

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⬅️", callback_data="prev"),
        InlineKeyboardButton("➡️", callback_data="next")
    )

    await m.answer(
        f"📚 {cat.upper()}\n\n📌 {get_text(facts[0],get_lang(uid))}",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c: types.CallbackQuery):
    uid = c.from_user.id
    st = user_state.get(uid)

    if not st:
        return

    if c.data == "next":
        st["index"] = (st["index"] + 1) % len(st["facts"])
    else:
        st["index"] = (st["index"] - 1) % len(st["facts"])

    await show_fact(c, uid)

@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    await c.answer("❤️ Saved!")

# --- START ---
if __name__ == "__main__":
    init_db()
    executor.start_polling(dp)