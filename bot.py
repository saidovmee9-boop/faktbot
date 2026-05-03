import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiohttp import web

# --- KONFIGURATSIYA ---
API_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- IDEAL LUG'AT (Hech qanday xatolarsiz) ---
STRINGS = {
    'uz': {
        'hi': "🌟 <b>Xush kelibsiz!</b>\nBo'limni tanlang:",
        'sci': "🔬 Science", 'tech': "💻 Tech", 'hist': "📜 History",
        'quiz': "🕹 Quiz Game", 'rand': "🎲 Random", 'save': "🌟 Saved",
        'lang': "🌐 Tilni o'zgartirish", 'next': "➡️ Keyingisi",
        'save_btn': "💾 Saqlash", 'quiz_ask': "🤔 Bu rostmi?",
        'true': "✅ Rost", 'false': "❌ Yolg'on", 'correct': "🎯 To'g'ri!", 'wrong': "❌ Xato!",
        'empty': "Saqlangan faktlar yo'q.", 'fin': "Bu bo'limda faktlar tugadi! ✅"
    },
    'ru': {
        'hi': "🌟 <b>Добро пожаловать!</b>\nВыберите раздел:",
        'sci': "🔬 Science", 'tech': "💻 Tech", 'hist': "📜 History",
        'quiz': "🕹 Quiz Game", 'rand': "🎲 Random", 'save': "🌟 Saved",
        'lang': "🌐 Изменить язык", 'next': "➡️ Следующий",
        'save_btn': "💾 Сохранить", 'quiz_ask': "🤔 Это правда?",
        'true': "✅ Правда", 'false': "❌ Ложь", 'correct': "🎯 Правильно!", 'wrong': "❌ Ошибка!",
        'empty': "Избранных фактов нет.", 'fin': "Факты в этом разделе закончились! ✅"
    },
    'en': {
        'hi': "🌟 <b>Welcome!</b>\nChoose a category:",
        'sci': "🔬 Science", 'tech': "💻 Tech", 'hist': "📜 History",
        'quiz': "🕹 Quiz Game", 'rand': "🎲 Random", 'save': "🌟 Saved",
        'lang': "🌐 Change Language", 'next': "➡️ Next",
        'save_btn': "💾 Save", 'quiz_ask': "🤔 Is it true?",
        'true': "✅ True", 'false': "❌ False", 'correct': "🎯 Correct!", 'wrong': "❌ Wrong!",
        'empty': "No saved facts yet.", 'fin': "No more facts in this category! ✅"
    }
}

# --- BAZA MANTIQI ---
def init_db():
    conn = sqlite3.connect('factbot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT DEFAULT "uz")')
    c.execute('CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, cat TEXT, uz TEXT, ru TEXT, en TEXT, is_true INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS seen (uid INTEGER, fid INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS saved (uid INTEGER, fid INTEGER)')
    
    c.execute("SELECT count(*) FROM facts")
    if c.fetchone()[0] == 0:
        data = [
            ('science', 'Inson ko\'zi 10 million xil rangni ajrata oladi.', 'Человеческий глаз может различать 10 миллионов цветов.', 'The human eye can distinguish 10 million colors.', 1),
            ('tech', 'Birinchi veb-kamera kofe qaynatgichni kuzatish uchun o\'rnatilgan.', 'Первая веб-камера была создана для наблюдения за кофеваркой.', 'The first webcam was created to monitor a coffee pot.', 1),
            ('history', 'Qadimgi Rimda tish pastasi o\'rnida siydik ishlatilgan.', 'В Древнем Риме мочу использовали вместо зубной пасты.', 'In Ancient Rome, urine was used instead of toothpaste.', 1)
        ]
        c.executemany("INSERT INTO facts (cat, uz, ru, en, is_true) VALUES (?,?,?,?,?)", data)
    conn.commit()
    conn.close()

def get_lang(uid):
    conn = sqlite3.connect('factbot.db')
    r = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return r[0] if r else 'uz'

def get_kb(l):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    s = STRINGS[l]
    kb.add(KeyboardButton(s['sci']), KeyboardButton(s['tech']), KeyboardButton(s['hist']))
    kb.add(KeyboardButton(s['quiz']), KeyboardButton(s['rand']), KeyboardButton(s['save']))
    kb.add(KeyboardButton(s['lang']))
    return kb

# --- ASOSIY FAKT LOGIKASI ---
async def send_fact_engine(m, uid, lang, category):
    conn = sqlite3.connect('factbot.db')
    q = "SELECT * FROM facts WHERE id NOT IN (SELECT fid FROM seen WHERE uid=?)"
    p = [uid]
    if category != 'random':
        q += " AND cat=?"
        p.append(category)
    q += " ORDER BY RANDOM() LIMIT 1"
    
    f = conn.execute(q, p).fetchone()
    if not f:
        conn.close()
        return await m.answer(STRINGS[lang]['fin'])
    
    conn.execute("INSERT INTO seen VALUES (?,?)", (uid, f[0]))
    conn.commit()
    conn.close()
    
    txt = f[2] if lang=='uz' else (f[3] if lang=='ru' else f[4])
    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton(STRINGS[lang]['save_btn'], callback_data=f"sv_{f[0]}"),
        InlineKeyboardButton(STRINGS[lang]['next'], callback_data=f"nx_{category}")
    )
    await m.answer(f"<b>[{category.upper()}]</b>\n\n{txt}", reply_markup=kb, parse_mode="HTML")

# --- HANDLERLAR ---
@dp.message_handler(commands=['start'])
async def start(m: types.Message):
    conn = sqlite3.connect('factbot.db')
    conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (m.from_user.id,))
    conn.commit()
    l = get_lang(m.from_user.id)
    await m.answer(STRINGS[l]['hi'], reply_markup=get_kb(l), parse_mode="HTML")

@dp.message_handler(lambda m: any(m.text == s['lang'] for s in STRINGS.values()))
async def lang_cmd(m: types.Message):
    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton("🇺🇿 UZ", callback_data="set_uz"),
        InlineKeyboardButton("🇷🇺 RU", callback_data="set_ru"),
        InlineKeyboardButton("🇺🇸 EN", callback_data="set_en")
    )
    await m.answer("Select / Выберите / Tanlang:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('set_'))
async def set_l(c: types.CallbackQuery):
    l = c.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    conn.execute("UPDATE users SET lang=? WHERE id=?", (l, c.from_user.id))
    conn.commit()
    await c.message.delete()
    await c.message.answer("✅", reply_markup=get_kb(l))

@dp.message_handler(lambda m: any(m.text in [s[k] for s in STRINGS.values() for k in ['sci', 'tech', 'hist', 'rand']]))
async def cats(m: types.Message):
    l = get_lang(m.from_user.id)
    cat = 'science' if any(m.text == s['sci'] for s in STRINGS.values()) else \
          'tech' if any(m.text == s['tech'] for s in STRINGS.values()) else \
          'history' if any(m.text == s['hist'] for s in STRINGS.values()) else 'random'
    await send_fact_engine(m, m.from_user.id, l, cat)

@dp.callback_query_handler(lambda c: c.data.startswith('nx_'))
async def nx_f(c: types.CallbackQuery):
    l = get_lang(c.from_user.id)
    await c.message.delete()
    await send_fact_engine(c.message, c.from_user.id, l, c.data.split('_')[1])

@dp.message_handler(lambda m: any(m.text == s['quiz'] for s in STRINGS.values()))
async def quiz_cmd(m: types.Message):
    l = get_lang(m.from_user.id)
    conn = sqlite3.connect('factbot.db')
    f = conn.execute("SELECT * FROM facts ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    if not f: return
    txt = f[2] if l=='uz' else (f[3] if l=='ru' else f[4])
    kb = InlineKeyboardMarkup().row(
        InlineKeyboardButton(STRINGS[l]['true'], callback_data=f"qz_{f[5]}_1"),
        InlineKeyboardButton(STRINGS[l]['false'], callback_data=f"qz_{f[5]}_0")
    )
    await m.answer(f"❓ <b>QUIZ</b>\n\n{txt}\n\n{STRINGS[l]['quiz_ask']}", reply_markup=kb, parse_mode="HTML")

@dp.callback_query_handler(lambda c: c.data.startswith('qz_'))
async def check_qz(c: types.CallbackQuery):
    l = get_lang(c.from_user.id)
    _, real, user = c.data.split('_')
    res = STRINGS[l]['correct'] if real == user else STRINGS[l]['wrong']
    await c.answer(res, show_alert=True)
    await c.message.delete()
    await quiz_cmd(c.message)

@dp.message_handler(lambda m: any(m.text == s['save'] for s in STRINGS.values()))
async def saved_cmd(m: types.Message):
    l = get_lang(m.from_user.id)
    conn = sqlite3.connect('factbot.db')
    rows = conn.execute("SELECT f.* FROM facts f JOIN saved s ON f.id=s.fid WHERE s.uid=?", (m.from_user.id,)).fetchall()
    conn.close()
    if not rows: return await m.answer(STRINGS[l]['empty'])
    for r in rows:
        txt = r[2] if l=='uz' else (r[3] if l=='ru' else r[4])
        await m.answer(f"⭐ <b>{r[1].upper()}</b>\n{txt}", parse_mode="HTML")

@dp.callback_query_handler(lambda c: c.data.startswith('sv_'))
async def sv_f(c: types.CallbackQuery):
    fid = c.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)", (c.from_user.id, fid))
    conn.commit()
    await c.answer("⭐ Saved!")

# --- RENDER SERVER (Port binding) ---
async def on_startup(_):
    init_db()
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is Active"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)