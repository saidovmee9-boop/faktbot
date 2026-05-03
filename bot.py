import os
import sqlite3
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiohttp import web

# --- KONFIGURATSIYA ---
API_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- HOLATLAR (FSM) ---
class BotStates(StatesGroup):
    main_menu = State()
    browsing_facts = State()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT DEFAULT "uz")')
    cursor.execute('''CREATE TABLE IF NOT EXISTS facts 
                      (id INTEGER PRIMARY KEY, category TEXT, uz TEXT, ru TEXT, en TEXT, is_true INTEGER)''')
    cursor.execute('CREATE TABLE IF NOT EXISTS seen_facts (user_id INTEGER, fact_id INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS saved_facts (user_id INTEGER, fact_id INTEGER)')
    
    cursor.execute("SELECT count(*) FROM facts")
    if cursor.fetchone()[0] == 0:
        # Kategoriyalarga bo'lingan faktlar
        facts = [
            ('🔬 Science', 'Suv 100 darajada qaynaydi.', 'Вода кипит при 100 градусах.', 'Water boils at 100 degrees.', 1),
            ('💻 Tech', 'Birinchi kompyuter sichqonchasi yog\'ochdan yasalgan.', 'Первая компьютерная мышь была сделана из дерева.', 'The first computer mouse was made of wood.', 1),
            ('📜 History', 'Ikkinchi jahon urushi 1945-yilda tugagan.', 'Вторая мировая война закончилась в 1945 году.', 'WWII ended in 1945.', 1),
            ('🔬 Science', 'Odam tanasida 206 ta suyak bor.', 'В теле человека 206 костей.', 'There are 206 bones in the human body.', 1),
            ('💻 Tech', 'Dunyodagi birinchi domen symbolics.com bo\'lgan.', 'Первым доменом в мире был symbolics.com.', 'The first domain in the world was symbolics.com.', 1)
        ]
        cursor.executemany("INSERT INTO facts (category, uz, ru, en, is_true) VALUES (?,?,?,?,?)", facts)
    conn.commit()
    conn.close()

init_db()

# --- INTERFEYS MATNLARI ---
TEXTS = {
    'uz': {
        'welcome': "🌟 <b>Xush kelibsiz!</b>\n\nQiziqarli faktlar olamiga tayyormisiz?",
        'menu': ["🔬 Science", "💻 Tech", "📜 History", "🔀 Random", "⭐ Saved", "🌐 Til/Lang"],
        'no_facts': "Hamma faktlarni ko'rib bo'ldingiz! ✅",
        'saved_empty': "Saqlangan faktlar yo'q. 🤷‍♂️",
        'quiz_head': "🤔 Rostmi?"
    },
    'ru': {
        'welcome': "🌟 <b>Добро пожаловать!</b>\n\nГотовы к миру интересных фактов?",
        'menu': ["🔬 Science", "💻 Tech", "📜 History", "🔀 Random", "⭐ Saved", "🌐 Til/Lang"],
        'no_facts': "Вы посмотрели все факты! ✅",
        'saved_empty': "Нет сохраненных фактов. 🤷‍♂️",
        'quiz_head': "🤔 Это правда?"
    },
    'en': {
        'welcome': "🌟 <b>Welcome!</b>\n\nAre you ready for the world of facts?",
        'menu': ["🔬 Science", "💻 Tech", "📜 History", "🔀 Random", "⭐ Saved", "🌐 Til/Lang"],
        'no_facts': "You have seen all facts! ✅",
        'saved_empty': "No saved facts yet. 🤷‍♂️",
        'quiz_head': "🤔 Is it true?"
    }
}

def get_user_lang(uid):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE id = ?", (uid,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 'uz'

def main_menu(lang):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [KeyboardButton(text) for text in TEXTS[lang]['menu']]
    markup.add(*buttons)
    return markup

# --- WEB SERVER (RENDER) ---
async def on_startup(dispatcher):
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Running"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

# --- HANDLERLAR ---

@dp.message_handler(commands=['start'], state='*')
async def start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()
    
    lang = get_user_lang(uid)
    await state.set_state(BotStates.main_menu)
    await message.answer(TEXTS[lang]['welcome'], parse_mode="HTML", reply_markup=main_menu(lang))

@dp.message_handler(lambda m: "🌐" in m.text, state='*')
async def lang_switcher(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="l_uz"),
           InlineKeyboardButton("🇷🇺 Русский", callback_data="l_ru"),
           InlineKeyboardButton("🇺🇸 English", callback_data="l_en"))
    await message.answer("Tanlang / Выберите / Choose:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('l_'), state='*')
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lang = ? WHERE id = ?", (lang, callback.from_user.id))
    conn.commit()
    conn.close()
    await callback.message.delete()
    await callback.message.answer("✅ Done!", reply_markup=main_menu(lang))

@dp.message_handler(state=BotStates.main_menu)
async def handle_menu(message: types.Message):
    uid = message.from_user.id
    lang = get_user_lang(uid)
    txt = message.text

    # Kategoriyani aniqlash
    category = None
    if "Science" in txt: category = "🔬 Science"
    elif "Tech" in txt: category = "💻 Tech"
    elif "History" in txt: category = "📜 History"
    elif "Random" in txt: category = "random"
    elif "Saved" in txt: return await show_saved(message, lang)
    else: return

    await fetch_and_send_fact(message, uid, lang, category)

async def fetch_and_send_fact(message, uid, lang, category):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    
    query = "SELECT * FROM facts WHERE id NOT IN (SELECT fact_id FROM seen_facts WHERE user_id = ?)"
    params = [uid]
    
    if category != "random":
        query += " AND category = ?"
        params.append(category)
    
    query += " ORDER BY RANDOM() LIMIT 1"
    cursor.execute(query, params)
    f = cursor.fetchone()
    
    if not f:
        conn.close()
        return await message.answer(TEXTS[lang]['no_facts'])

    cursor.execute("INSERT INTO seen_facts VALUES (?, ?)", (uid, f[0]))
    conn.commit()
    conn.close()

    fact_text = f[2] if lang == 'uz' else (f[3] if lang == 'ru' else f[4])
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("⭐ Save", callback_data=f"s_{f[0]}"),
           InlineKeyboardButton("➡️ Next", callback_data=f"n_{category}"))
    
    await message.answer(f"<b>{f[1]}</b>\n\n{fact_text}", parse_mode="HTML", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('n_'), state='*')
async def next_fact(callback: types.CallbackQuery):
    cat = callback.data.split('_')[1]
    lang = get_user_lang(callback.from_user.id)
    await callback.message.delete()
    await fetch_and_send_fact(callback.message, callback.from_user.id, lang, cat)

@dp.callback_query_handler(lambda c: c.data.startswith('s_'), state='*')
async def save_fact(callback: types.CallbackQuery):
    fid = callback.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO saved_facts VALUES (?, ?)", (callback.from_user.id, fid))
    conn.commit()
    conn.close()
    await callback.answer("⭐ Saved!")

async def show_saved(message, lang):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("""SELECT facts.* FROM facts 
                      JOIN saved_facts ON facts.id = saved_facts.fact_id 
                      WHERE saved_facts.user_id = ?""", (message.from_user.id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return await message.answer(TEXTS[lang]['saved_empty'])
    
    for r in rows:
        t = r[2] if lang == 'uz' else (r[3] if lang == 'ru' else r[4])
        await message.answer(f"⭐ <b>{r[1]}</b>\n{t}", parse_mode="HTML")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)