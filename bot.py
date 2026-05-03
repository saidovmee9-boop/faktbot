import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiohttp import web

API_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- STRINGS ---
STRINGS = {
    "uz": {
        "hi": "🌟 Xush kelibsiz!",
        "next": "➡️ Keyingi",
        "prev": "⬅️ Oldingi",
        "save": "❤️ Saqlash",
        "saved": "❤️ Saqlanganlar",
        "rand": "🎲 Random",
        "lang": "🌐 Til",
        "empty": "Hech narsa yo'q"
    },
    "ru": {
        "hi": "🌟 Добро пожаловать!",
        "next": "➡️ Далее",
        "prev": "⬅️ Назад",
        "save": "❤️ Saqlash",
        "saved": "❤️ Saqlanganlar",
        "rand": "🎲 Рандом",
        "lang": "🌐 Язык",
        "empty": "Пусто"
    },
    "en": {
        "hi": "🌟 Welcome!",
        "next": "➡️ Next",
        "prev": "⬅️ Prev",
        "save": "❤️ Saqlash",
        "saved": "❤️ Saqlanganlar",
        "rand": "🎲 Random",
        "lang": "🌐 Language",
        "empty": "Empty"
    }
}

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
                # SCIENCE
                ("science","Inson miyasi tanadagi eng murakkab organ.","Мозг — самый сложный орган.","The brain is the most complex organ."),
                ("science","Suv 100°C da qaynaydi.","Вода кипит при 100°C.","Water boils at 100°C."),
                ("science","Yer Quyosh atrofida aylanadi.","Земля вращается вокруг Солнца.","Earth orbits the Sun."),
                ("science","DNA insonning genetik kodi.","ДНК — генетический код человека.","DNA carries genetic code."),
                ("science","Yorug'lik tezligi eng tezdir.","Скорость света самая высокая.","Light is the fastest."),

                # TECH
                ("tech","Internet 1960-yillarda yaratilgan.","Интернет создан в 1960-х.","Internet was created in 1960s."),
                ("tech","Birinchi kompyuter juda katta edi.","Первый компьютер был огромным.","First computer was huge."),
                ("tech","Python mashhur dasturlash tili.","Python популярный язык.","Python is a popular language."),
                ("tech","Smartfonlar mini kompyuter hisoblanadi.","Смартфоны — мини ПК.","Smartphones are mini computers."),
                ("tech","AI tez rivojlanmoqda.","ИИ быстро развивается.","AI is growing fast."),

                # HISTORY
                ("history","Misr piramidalari qadimiydir.","Пирамиды Египта древние.","Egypt pyramids are ancient."),
                ("history","Rim imperiyasi katta bo'lgan.","Римская империя была огромной.","Roman Empire was huge."),
                ("history","Ikkinchi jahon urushi 1945 da tugagan.","Вторая мировая закончилась в 1945.","WW2 ended in 1945."),
                ("history","Buyuk ipak yo‘li mavjud bo‘lgan.","Был Шёлковый путь.","Silk Road existed."),
                ("history","Amir Temur buyuk sarkarda.","Тамерлан великий полководец.","Tamerlane was a great commander."),
            ]

            c.executemany("INSERT INTO facts (cat, uz, ru, en) VALUES (?,?,?,?)", facts)

# --- HELPERS ---
def get_lang(uid):
    with db() as conn:
        r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
        return r[0] if r else "uz"

def set_lang(uid, l):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users (id, lang) VALUES (?,?)", (uid, l))

def get_text(row, lang):
    return row[2] if lang=="uz" else row[3] if lang=="ru" else row[4]

# --- MENU ---
def menu(l):
    s = STRINGS[l]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech","📜 History")
    kb.add(s["rand"], s["saved"])
    kb.add(s["lang"])
    return kb

def fact_kb(fid, cat, l):
    s = STRINGS[l]
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(s["prev"], callback_data=f"prev_{cat}"),
        InlineKeyboardButton(s["next"], callback_data=f"next_{cat}")
    )
    kb.add(InlineKeyboardButton(s["save"], callback_data=f"save_{fid}"))
    return kb

# --- FACT ---
def get_fact(uid, cat):
    with db() as conn:
        q = "SELECT * FROM facts WHERE id NOT IN (SELECT fid FROM history WHERE uid=?)"
        p = [uid]
        if cat!="random":
            q += " AND cat=?"
            p.append(cat)
        q += " ORDER BY RANDOM() LIMIT 1"
        return conn.execute(q,p).fetchone()

async def send_fact(m, uid, cat):
    lang = get_lang(uid)
    row = get_fact(uid, cat)

    if not row:
        with db() as conn:
            conn.execute("DELETE FROM history WHERE uid=?", (uid,))
        row = get_fact(uid, cat)

    with db() as conn:
        conn.execute("INSERT INTO history VALUES (?,?)",(uid,row[0]))

    await m.answer(get_text(row,lang), reply_markup=fact_kb(row[0],cat,lang))

# --- HANDLERS ---
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    set_lang(m.from_user.id,"uz")
    l = get_lang(m.from_user.id)
    await m.answer(STRINGS[l]["hi"], reply_markup=menu(l))

@dp.message_handler(lambda m: m.text in ["🌐 Til","🌐 Язык","🌐 Language"])
async def lang_menu(m):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("UZ",callback_data="lang_uz"),
        InlineKeyboardButton("RU",callback_data="lang_ru"),
        InlineKeyboardButton("EN",callback_data="lang_en"),
    )
    await m.answer("Til tanlang:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(c):
    l = c.data.split("_")[1]
    set_lang(c.from_user.id,l)
    await c.message.answer("✅", reply_markup=menu(l))

@dp.message_handler()
async def main(m: types.Message):
    t = m.text
    if "Science" in t:
        await send_fact(m,m.from_user.id,"science")
    elif "Tech" in t:
        await send_fact(m,m.from_user.id,"tech")
    elif "History" in t:
        await send_fact(m,m.from_user.id,"history")
    elif "Random" in t or "Рандом" in t:
        await send_fact(m,m.from_user.id,"random")
    elif "Saved" in t or "Избран" in t or "Saqlangan" in t:
        await show_saved(m)

@dp.callback_query_handler(lambda c: c.data.startswith("next_"))
async def next_f(c):
    await send_fact(c.message,c.from_user.id,c.data.split("_")[1])

@dp.callback_query_handler(lambda c: c.data.startswith("prev_"))
async def prev_f(c):
    await send_fact(c.message,c.from_user.id,c.data.split("_")[1])

@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = c.data.split("_")[1]
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)",(c.from_user.id,fid))
    await c.answer("Saved!")

async def show_saved(m):
    l = get_lang(m.from_user.id)
    with db() as conn:
        rows = conn.execute("SELECT f.* FROM facts f JOIN saved s ON f.id=s.fid WHERE s.uid=?",(m.from_user.id,)).fetchall()

    if not rows:
        return await m.answer(STRINGS[l]["empty"])

    for r in rows:
        await m.answer(get_text(r,l))

# --- SERVER ---
async def on_startup(_):
    init_db()
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner,"0.0.0.0",PORT).start()

if __name__=="__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)