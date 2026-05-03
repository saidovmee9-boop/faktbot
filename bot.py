import os
import sqlite3
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiohttp import web

# --- KONFIGURATSIYA (RENDER UCHUN) ---
# Tokenni Render'dagi Environment Variables'dan olamiz
API_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS facts 
                      (id INTEGER PRIMARY KEY, category TEXT, uz TEXT, ru TEXT, en TEXT, is_true INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS seen_facts (user_id INTEGER, fact_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS saved_facts (user_id INTEGER, fact_id INTEGER)''')
    
    cursor.execute("SELECT count(*) FROM facts")
    if cursor.fetchone()[0] == 0:
        sample_facts = [
            ('Fan', 'Yulduzlar aslida miltillamaydi.', 'Звезды на самом деле не мерцают.', 'Stars don’t actually twinkle.', 1),
            ('Tarix', 'Napoleon bo''yi juda past bo''lmagan.', 'Наполеон не был очень маленького роста.', 'Napoleon was not very short.', 1),
            ('Dunyo', 'Fillar sakray olmaydi.', 'Слоны не умеют прыгать.', 'Elephants cannot jump.', 1),
            ('Fan', 'Asal hech qachon aynimaydi.', 'Мёд никогда не портится.', 'Honey never spoils.', 1)
        ]
        cursor.executemany("INSERT INTO facts (category, uz, ru, en, is_true) VALUES (?,?,?,?,?)", sample_facts)
    conn.commit()
    conn.close()

init_db()

# --- WEB SERVER (RENDER UCHUN) ---
async def handle(request):
    return web.Response(text="Bot is running smoothly!")

async def on_startup(dispatcher):
    # Bu funksiya Render'dagi portni eshitishni boshlaydi
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"Server started on port {PORT}")

# --- YORDAMCHI FUNKSIYALAR ---
def get_user_lang(user_id):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 'uz'

def get_keyboard(lang):
    texts = {
        'uz': ["🔍 Faktlar", "🎮 Quiz", "🌟 Saqlanganlar", "🎲 Tasodifiy", "🌐 Til"],
        'ru': ["🔍 Факты", "🎮 Квиз", "🌟 Сохраненные", "🎲 Случайно", "🌐 Язык"],
        'en': ["🔍 Facts", "🎮 Quiz", "🌟 Saved", "🎲 Random", "🌐 Language"]
    }
    t = texts[lang]
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton(t[0]), KeyboardButton(t[1]))
    markup.add(KeyboardButton(t[2]), KeyboardButton(t[3]))
    markup.add(KeyboardButton(t[4]))
    return markup

# --- HANDLERLAR ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    lang = get_user_lang(user_id)
    await message.answer("Xush kelibsiz! / Welcome! / Добро пожаловать!", reply_markup=get_keyboard(lang))

@dp.message_handler(lambda m: "🌐" in m.text)
async def change_lang(message: types.Message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"))
    markup.add(InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"))
    markup.add(InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en"))
    await message.answer("Tilni tanlang:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('setlang_'))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lang = ? WHERE id = ?", (lang, callback.from_user.id))
    conn.commit()
    conn.close()
    await callback.message.delete()
    await callback.message.answer("✅", reply_markup=get_keyboard(lang))

@dp.message_handler(lambda m: any(icon in m.text for icon in ["🎲", "🔍"]))
async def send_fact(message: types.Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM facts WHERE id NOT IN 
                      (SELECT fact_id FROM seen_facts WHERE user_id = ?) 
                      ORDER BY RANDOM() LIMIT 1""", (user_id,))
    fact = cursor.fetchone()
    if not fact:
        msg = {"uz": "Barcha faktlarni ko'rdingiz!", "ru": "Вы всё видели!", "en": "No more facts!"}
        await message.answer(msg[lang])
        return
    cursor.execute("INSERT INTO seen_facts VALUES (?, ?)", (user_id, fact[0]))
    conn.commit()
    conn.close()
    text = fact[2] if lang == 'uz' else (fact[3] if lang == 'ru' else fact[4])
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💾 Save", callback_data=f"save_{fact[0]}"),
               InlineKeyboardButton("➡️ Next", callback_data="next_fact"))
    await message.answer(f"<b>[{fact[1]}]</b>\n\n{text}", parse_mode="HTML", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data == "next_fact")
async def next_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await send_fact(callback.message)

@dp.callback_query_handler(lambda c: c.data.startswith('save_'))
async def save_callback(callback: types.CallbackQuery):
    fact_id = int(callback.data.split('_')[1])
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO saved_facts VALUES (?, ?)", (callback.from_user.id, fact_id))
    conn.commit()
    conn.close()
    await callback.answer("Saved! ⭐")

@dp.message_handler(lambda m: "🎮" in m.text)
async def quiz_mode(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facts ORDER BY RANDOM() LIMIT 1")
    fact = cursor.fetchone()
    conn.close()
    text = fact[2] if lang == 'uz' else (fact[3] if lang == 'ru' else fact[4])
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ True", callback_data=f"q_1_{fact[5]}"),
               InlineKeyboardButton("❌ False", callback_data=f"q_0_{fact[5]}"))
    await message.answer(f"Quiz: {text}", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('q_'))
async def check_q(callback: types.CallbackQuery):
    _, user_ans, real_ans = callback.data.split('_')
    if user_ans == real_ans:
        await callback.answer("To'g'ri! 🎯", show_alert=True)
    else:
        await callback.answer("Xato! ❌", show_alert=True)
    await callback.message.delete()
    await quiz_mode(callback.message)

@dp.message_handler(lambda m: "🌟" in m.text)
async def show_saved(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("""SELECT facts.* FROM facts 
                      JOIN saved_facts ON facts.id = saved_facts.fact_id 
                      WHERE saved_facts.user_id = ?""", (message.from_user.id,))
    saved = cursor.fetchall()
    conn.close()
    if not saved:
        await message.answer("Hali saqlanganlar yo'q.")
        return
    for f in saved:
        text = f[2] if lang == 'uz' else (f[3] if lang == 'ru' else f[4])
        await message.answer(f"⭐ {text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)