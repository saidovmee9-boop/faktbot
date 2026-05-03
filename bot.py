import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiohttp import web

# --- CONFIG ---
API_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- STRINGS ---
STRINGS = {
    'uz': {
        'hi': "🌟 <b>Xush kelibsiz!</b>\nBo'limni tanlang:",
        'sci': "🔬 Science", 'tech': "💻 Tech", 'hist': "📜 History",
        'quiz': "🕹 Quiz Game", 'rand': "🎲 Random", 'save': "🌟 Saved",
        'lang': "🌐 Tilni o'zgartirish", 'next': "➡️ Keyingisi",
        'save_btn': "💾 Saqlash", 'quiz_ask': "🤔 Bu rostmi?",
        'true': "✅ Rost", 'false': "❌ Yolg'on",
        'correct': "🎯 To'g'ri!", 'wrong': "❌ Xato!",
        'empty': "Saqlangan faktlar yo'q.", 'fin': "Faktlar tugadi! ✅"
    },
    'ru': {
        'hi': "🌟 <b>Добро пожаловать!</b>\nВыберите раздел:",
        'sci': "🔬 Science", 'tech': "💻 Tech", 'hist': "📜 History",
        'quiz': "🕹 Quiz Game", 'rand': "🎲 Random", 'save': "🌟 Saved",
        'lang': "🌐 Изменить язык", 'next': "➡️ Следующий",
        'save_btn': "💾 Сохранить", 'quiz_ask': "🤔 Это правда?",
        'true': "✅ Правда", 'false': "❌ Ложь",
        'correct': "🎯 Правильно!", 'wrong': "❌ Ошибка!",
        'empty': "Нет сохранённых фактов.", 'fin': "Факты закончились! ✅"
    },
    'en': {
        'hi': "🌟 <b>Welcome!</b>\nChoose a category:",
        'sci': "🔬 Science", 'tech': "💻 Tech", 'hist': "📜 History",
        'quiz': "🕹 Quiz Game", 'rand': "🎲 Random", 'save': "🌟 Saved",
        'lang': "🌐 Change Language", 'next': "➡️ Next",
        'save_btn': "💾 Save", 'quiz_ask': "🤔 Is it true?",
        'true': "✅ True", 'false': "❌ False",
        'correct': "🎯 Correct!", 'wrong': "❌ Wrong!",
        'empty': "No saved facts.", 'fin': "No more facts! ✅"
    }
}

# --- DB ---
def init_db():
    with sqlite3.connect('factbot.db') as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT DEFAULT "uz")')
        c.execute('CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, cat TEXT, uz TEXT, ru TEXT, en TEXT, is_true INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS seen (uid INTEGER, fid INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS saved (uid INTEGER, fid INTEGER)')

        if c.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0:
            data = [
                ('science', 'Inson ko\'zi 10 million rangni ajratadi.',
                 'Глаз различает 10 млн цветов.',
                 'The human eye distinguishes 10M colors.', 1),

                ('tech', 'Birinchi webcam kofe uchun yaratilgan.',
                 'Первая веб-камера следила за кофе.',
                 'First webcam watched coffee.', 1),

                ('history', 'Qadimda siydik tish pastasi bo‘lgan.',
                 'Мочу использовали как пасту.',
                 'Urine used as toothpaste.', 1)
            ]
            c.executemany("INSERT INTO facts (cat, uz, ru, en, is_true) VALUES (?,?,?,?,?)", data)

def get_lang(uid):
    with sqlite3.connect('factbot.db') as conn:
        r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
        return r[0] if r else 'uz'

def get_kb(l):
    s = STRINGS[l]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(s['sci'], s['tech'], s['hist'])
    kb.add(s['quiz'], s['rand'], s['save'])
    kb.add(s['lang'])
    return kb

# --- FACT ---
async def send_fact(m, uid, lang, cat):
    with sqlite3.connect('factbot.db') as conn:
        q = "SELECT * FROM facts WHERE id NOT IN (SELECT fid FROM seen WHERE uid=?)"
        p = [uid]

        if cat != 'random':
            q += " AND cat=?"
            p.append(cat)

        q += " ORDER BY RANDOM() LIMIT 1"
        f = conn.execute(q, p).fetchone()

        if not f:
            return await m.answer(STRINGS[lang]['fin'])

        conn.execute("INSERT INTO seen VALUES (?,?)", (uid, f[0]))
        conn.commit()

    txt = f[2] if lang == 'uz' else (f[3] if lang == 'ru' else f[4])

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton(STRINGS[lang]['save_btn'], callback_data=f"sv_{f[0]}"),
        InlineKeyboardButton(STRINGS[lang]['next'], callback_data=f"nx_{cat}")
    )

    await m.answer(f"<b>[{cat.upper()}]</b>\n\n{txt}", reply_markup=kb, parse_mode="HTML")

# --- HANDLERS ---
@dp.message_handler(commands=['start'])
async def start(m: types.Message):
    with sqlite3.connect('factbot.db') as conn:
        conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (m.from_user.id,))
        conn.commit()

    l = get_lang(m.from_user.id)
    await m.answer(STRINGS[l]['hi'], reply_markup=get_kb(l), parse_mode="HTML")

@dp.message_handler(lambda m: m.text in [s['lang'] for s in STRINGS.values()])
async def lang_cmd(m: types.Message):
    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("🇺🇿 UZ", callback_data="set_uz"),
        InlineKeyboardButton("🇷🇺 RU", callback_data="set_ru"),
        InlineKeyboardButton("🇺🇸 EN", callback_data="set_en")
    )
    await m.answer("Tilni tanlang:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('set_'))
async def set_lang(c: types.CallbackQuery):
    l = c.data.split('_')[1]
    with sqlite3.connect('factbot.db') as conn:
        conn.execute("UPDATE users SET lang=? WHERE id=?", (l, c.from_user.id))
        conn.commit()

    await c.message.delete()
    await c.message.answer("✅", reply_markup=get_kb(l))

@dp.message_handler()
async def main_menu(m: types.Message):
    l = get_lang(m.from_user.id)
    s = STRINGS[l]

    if m.text == s['sci']:
        await send_fact(m, m.from_user.id, l, 'science')
    elif m.text == s['tech']:
        await send_fact(m, m.from_user.id, l, 'tech')
    elif m.text == s['hist']:
        await send_fact(m, m.from_user.id, l, 'history')
    elif m.text == s['rand']:
        await send_fact(m, m.from_user.id, l, 'random')
    elif m.text == s['quiz']:
        await quiz(m)
    elif m.text == s['save']:
        await show_saved(m)

@dp.callback_query_handler(lambda c: c.data.startswith('nx_'))
async def next_fact(c: types.CallbackQuery):
    l = get_lang(c.from_user.id)
    cat = c.data.split('_')[1]
    await c.message.delete()
    await send_fact(c.message, c.from_user.id, l, cat)

@dp.callback_query_handler(lambda c: c.data.startswith('sv_'))
async def save_fact(c: types.CallbackQuery):
    fid = c.data.split('_')[1]
    with sqlite3.connect('factbot.db') as conn:
        conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)", (c.from_user.id, fid))
        conn.commit()

    await c.answer("⭐ Saved!")

# --- QUIZ ---
async def quiz(m):
    l = get_lang(m.from_user.id)
    with sqlite3.connect('factbot.db') as conn:
        f = conn.execute("SELECT * FROM facts ORDER BY RANDOM() LIMIT 1").fetchone()

    if not f:
        return

    txt = f[2] if l == 'uz' else (f[3] if l == 'ru' else f[4])

    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton(STRINGS[l]['true'], callback_data=f"qz_{f[5]}_1"),
        InlineKeyboardButton(STRINGS[l]['false'], callback_data=f"qz_{f[5]}_0")
    )

    await m.answer(f"❓ QUIZ\n\n{txt}\n\n{STRINGS[l]['quiz_ask']}", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('qz_'))
async def check_quiz(c: types.CallbackQuery):
    l = get_lang(c.from_user.id)
    _, real, user = c.data.split('_')

    res = STRINGS[l]['correct'] if real == user else STRINGS[l]['wrong']
    await c.answer(res, show_alert=True)

    await c.message.delete()
    await quiz(c.message)

# --- SAVED ---
async def show_saved(m):
    l = get_lang(m.from_user.id)
    with sqlite3.connect('factbot.db') as conn:
        rows = conn.execute(
            "SELECT f.* FROM facts f JOIN saved s ON f.id=s.fid WHERE s.uid=?",
            (m.from_user.id,)
        ).fetchall()

    if not rows:
        return await m.answer(STRINGS[l]['empty'])

    for r in rows:
        txt = r[2] if l == 'uz' else (r[3] if l == 'ru' else r[4])
        await m.answer(f"⭐ {txt}")

# --- SERVER ---
async def on_startup(_):
    init_db()
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)