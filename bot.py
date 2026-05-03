import os
import sqlite3
import asyncio
import random
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

# --- MATNLAR LUG'ATI (100% Tilni ta'minlaydi) ---
LANG_DATA = {
    'uz': {
        'welcome': "🌟 <b>Xush kelibsiz!</b>\nO'zingizga yoqqan bo'limni tanlang:",
        'science': "🔬 Fan", 'tech': "💻 Texno", 'history': "📜 Tarix",
        'random': "🔀 Tasodifiy", 'saved': "⭐ Saqlanganlar", 'lang': "🌐 Tilni o'zgartirish",
        'quiz': "🕹 Quiz Game", 'true': "✅ To'g'ri", 'false': "❌ Noto'g'ri",
        'next': "➡️ Keyingisi", 'save_btn': "💾 Saqlash", 'no_more': "Bu bo'limda faktlar tugadi! ✅",
        'quiz_ask': "🤔 Ushbu ma'lumot rostmi?", 'correct': "🎯 To'g'ri topdingiz!", 'wrong': "❌ Xato qildingiz!",
        'empty_saved': "Sizda hali saqlangan faktlar yo'q. 🤷‍♂️"
    },
    'ru': {
        'welcome': "🌟 <b>Добро пожаловать!</b>\nВыберите интересующий вас раздел:",
        'science': "🔬 Наука", 'tech': "💻 Техно", 'history': "📜 История",
        'random': "🔀 Случайно", 'saved': "⭐ Сохраненные", 'lang': "🌐 Изменить язык",
        'quiz': "🕹 Квиз игра", 'true': "✅ Правда", 'false': "❌ Ложь",
        'next': "➡️ Следующий", 'save_btn': "💾 Сохранить", 'no_more': "Факты в этом разделе закончились! ✅",
        'quiz_ask': "🤔 Это правда?", 'correct': "🎯 Правильно!", 'wrong': "❌ Вы ошиблись!",
        'empty_saved': "У вас пока нет сохраненных фактов. 🤷‍♂️"
    },
    'en': {
        'welcome': "🌟 <b>Welcome!</b>\nPlease choose a category:",
        'science': "🔬 Science", 'tech': "💻 Tech", 'history': "📜 History",
        'random': "🔀 Random", 'saved': "⭐ Saved", 'lang': "🌐 Change Language",
        'quiz': "🕹 Quiz Game", 'true': "✅ True", 'false': "❌ False",
        'next': "➡️ Next", 'save_btn': "💾 Save", 'no_more': "No more facts in this category! ✅",
        'quiz_ask': "🤔 Is this true?", 'correct': "🎯 Correct!", 'wrong': "❌ Wrong answer!",
        'empty_saved': "You don't have any saved facts yet. 🤷‍♂️"
    }
}

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('factbot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT DEFAULT "uz")')
    c.execute('''CREATE TABLE IF NOT EXISTS facts 
                 (id INTEGER PRIMARY KEY, cat TEXT, uz TEXT, ru TEXT, en TEXT, is_true INTEGER)''')
    c.execute('CREATE TABLE IF NOT EXISTS seen (uid INTEGER, fid INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS saved (uid INTEGER, fid INTEGER)')
    
    c.execute("SELECT count(*) FROM facts")
    if c.fetchone()[0] == 0:
        sample = [
            ('science', 'Inson miyasi tunda kunduzgidan faolroq.', 'Мозг человека активнее ночью, чем днем.', 'The human brain is more active at night than during the day.', 1),
            ('tech', 'Birinchi Apple logotipida Nyuton tasvirlangan.', 'На первом логотипе Apple был изображен Ньютон.', 'The first Apple logo featured Isaac Newton.', 1),
            ('history', 'Kleopatra piramidalardan ko\'ra iPhone-ga yaqinroq davrda yashagan.', 'Клеопатра жила ближе к iPhone, чем к пирамидам.', 'Cleopatra lived closer to the iPhone than the pyramids.', 1),
            ('science', 'Suv molekulasi 2 ta vodorod atomidan iborat.', 'Молекула воды состоит из 2 атомов водорода.', 'A water molecule consists of 2 hydrogen atoms.', 1)
        ]
        c.executemany("INSERT INTO facts (cat, uz, ru, en, is_true) VALUES (?,?,?,?,?)", sample)
    conn.commit()
    conn.close()

def get_user_lang(uid):
    conn = sqlite3.connect('factbot.db')
    res = conn.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return res[0] if res else 'uz'

def get_menu(lang):
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    d = LANG_DATA[lang]
    m.add(KeyboardButton(d['science']), KeyboardButton(d['tech']), KeyboardButton(d['history']))
    m.add(KeyboardButton(d['random']), KeyboardButton(d['quiz']), KeyboardButton(d['saved']))
    m.add(KeyboardButton(d['lang']))
    return m

# --- HANDLERLAR ---

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    conn = sqlite3.connect('factbot.db')
    conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()
    lang = get_user_lang(uid)
    await message.answer(LANG_DATA[lang]['welcome'], parse_mode="HTML", reply_markup=get_menu(lang))

@dp.message_handler(lambda m: any(x in m.text for x in ["🌐", "Language", "Til", "Язык"]))
async def cmd_lang(message: types.Message):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="set_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="set_ru"),
        InlineKeyboardButton("🇺🇸 English", callback_data="set_en")
    )
    await message.answer("Choose / Tanlang / Выберите:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('set_'))
async def set_lang(c: types.CallbackQuery):
    l = c.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    conn.execute("UPDATE users SET lang=? WHERE id=?", (l, c.from_user.id))
    conn.commit()
    conn.close()
    await c.message.delete()
    await c.message.answer("✅", reply_markup=get_menu(l))

async def send_fact_logic(message, uid, lang, category=None):
    conn = sqlite3.connect('factbot.db')
    c = conn.cursor()
    query = "SELECT * FROM facts WHERE id NOT IN (SELECT fid FROM seen WHERE uid=?)"
    params = [uid]
    if category and category != 'random':
        query += " AND cat=?"
        params.append(category)
    query += " ORDER BY RANDOM() LIMIT 1"
    
    f = c.execute(query, params).fetchone()
    if not f:
        conn.close()
        return await message.answer(LANG_DATA[lang]['no_more'])
    
    c.execute("INSERT INTO seen VALUES (?,?)", (uid, f[0]))
    conn.commit()
    conn.close()

    txt = f[2] if lang=='uz' else (f[3] if lang=='ru' else f[4])
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton(LANG_DATA[lang]['save_btn'], callback_data=f"sv_{f[0]}"),
        InlineKeyboardButton(LANG_DATA[lang]['next'], callback_data=f"nx_{category or 'random'}")
    )
    await message.answer(f"<b>[{f[1].upper()}]</b>\n\n{txt}", parse_mode="HTML", reply_markup=kb)

@dp.message_handler(lambda m: any(i in m.text for i in ["🔬", "💻", "📜", "🔀"]))
async def handle_cats(message: types.Message):
    uid = message.from_user.id
    lang = get_user_lang(uid)
    cat = 'science' if "🔬" in message.text else ('tech' if "💻" in message.text else ('history' if "📜" in message.text else 'random'))
    await send_fact_logic(message, uid, lang, cat)

@dp.callback_query_handler(lambda c: c.data.startswith('nx_'))
async def next_cb(c: types.CallbackQuery):
    lang = get_user_lang(c.from_user.id)
    cat = c.data.split('_')[1]
    await c.message.delete()
    await send_fact_logic(c.message, c.from_user.id, lang, cat)

@dp.callback_query_handler(lambda c: c.data.startswith('sv_'))
async def save_cb(c: types.CallbackQuery):
    fid = c.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)", (c.from_user.id, fid))
    conn.commit()
    conn.close()
    await c.answer("⭐ Saved!")

@dp.message_handler(lambda m: "🕹" in m.text or "Quiz" in m.text)
async def cmd_quiz(message: types.Message):
    uid = message.from_user.id
    lang = get_user_lang(uid)
    conn = sqlite3.connect('factbot.db')
    f = conn.execute("SELECT * FROM facts ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    
    txt = f[2] if lang=='uz' else (f[3] if lang=='ru' else f[4])
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton(LANG_DATA[lang]['true'], callback_data=f"qz_1_{f[5]}"),
        InlineKeyboardButton(LANG_DATA[lang]['false'], callback_data=f"qz_0_{f[5]}")
    )
    await message.answer(f"<b>{LANG_DATA[lang]['quiz_ask']}</b>\n\n{txt}", parse_mode="HTML", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('qz_'))
async def qz_cb(c: types.CallbackQuery):
    lang = get_user_lang(c.from_user.id)
    _, u_ans, r_ans = c.data.split('_')
    res = LANG_DATA[lang]['correct'] if u_ans == r_ans else LANG_DATA[lang]['wrong']
    await c.answer(res, show_alert=True)
    await c.message.delete()
    await cmd_quiz(c.message)

@dp.message_handler(lambda m: "⭐" in m.text or "Saved" in m.text)
async def cmd_saved(message: types.Message):
    uid = message.from_user.id
    lang = get_user_lang(uid)
    conn = sqlite3.connect('factbot.db')
    rows = conn.execute("SELECT f.* FROM facts f JOIN saved s ON f.id=s.fid WHERE s.uid=?", (uid,)).fetchall()
    conn.close()
    if not rows: return await message.answer(LANG_DATA[lang]['empty_saved'])
    for r in rows:
        txt = r[2] if lang=='uz' else (r[3] if lang=='ru' else r[4])
        await message.answer(f"⭐ <b>[{r[1].upper()}]</b>\n{txt}", parse_mode="HTML")

# --- RENDER PORT BINDING ---
async def on_startup(x):
    init_db()
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is Alive"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)