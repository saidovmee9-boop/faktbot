import os
import sqlite3
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
        facts = [
            ('🌌 Koinot', 'Quyosh tizimidagi eng issiq sayyora - Venera.', 'Самая горячая планета в Солнечной системе — Венера.', 'The hottest planet in our solar system is Venus.', 1),
            ('🐘 Tabiat', 'Fillar sakray olmaydigan yagona sutemizuvchidir.', 'Слоны — единственные млекопитающие, которые не умеют прыгать.', 'Elephants are the only mammals that can\'t jump.', 1),
            ('📜 Tarix', 'Kleopatra piramidalar qurilganidan ko\'ra iPhone chiqqan vaqtga yaqinroq yashagan.', 'Клеопатра жила ближе к выходу iPhone, чем к строительству пирамид.', 'Cleopatra lived closer to the release of the iPhone than the building of the pyramids.', 1),
            ('🧪 Fan', 'Suv molekulasi 3 ta atomdan iborat.', 'Молекула воды состоит из 3 атомов.', 'A water molecule consists of 3 atoms.', 1)
        ]
        cursor.executemany("INSERT INTO facts (category, uz, ru, en, is_true) VALUES (?,?,?,?,?)", facts)
    conn.commit()
    conn.close()

init_db()

# --- YORDAMCHI FUNKSIYALAR ---
def get_user_lang(user_id):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 'uz'

def main_menu(lang):
    texts = {
        'uz': ["💎 Faktlar", "🕹 Quiz Game", "📁 Saqlanganlar", "🔀 Tasodifiy", "⚙️ Til"],
        'ru': ["💎 Факты", "🕹 Квиз игра", "📁 Сохраненные", "🔀 Случайно", "⚙️ Язык"],
        'en': ["💎 Facts", "🕹 Quiz Game", "📁 Saved", "🔀 Random", "⚙️ Language"]
    }
    t = texts[lang]
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(*(KeyboardButton(text) for text in t))
    return markup

# --- WEB SERVER (RENDER UCHUN) ---
async def handle(request):
    return web.Response(text="Bot ishlayapti...")

async def on_startup(dispatcher):
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

# --- HANDLERLAR ---

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()
    lang = get_user_lang(uid)
    await message.answer("✨ <b>FactBot-ga xush kelibsiz!</b>\n\nMarhamat, bo'limni tanlang:", 
                         parse_mode="HTML", reply_markup=main_menu(lang))

@dp.message_handler(lambda m: "⚙️" in m.text or "Language" in m.text or "Язык" in m.text)
async def lang_menu(message: types.Message):
    btn = InlineKeyboardMarkup(row_width=1)
    btn.add(InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    await message.answer("🌐 Tilni tanlang / Выберите язык / Choose language:", reply_markup=btn)

@dp.callback_query_handler(lambda c: c.data.startswith('lang_'))
async def set_language(callback: types.CallbackQuery):
    new_lang = callback.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lang = ? WHERE id = ?", (new_lang, callback.from_user.id))
    conn.commit()
    conn.close()
    await callback.message.delete()
    await callback.message.answer("✅ Muvaffaqiyatli!", reply_markup=main_menu(new_lang))

@dp.message_handler(lambda m: "💎" in m.text or "🔀" in m.text or "Facts" in m.text or "Факты" in m.text)
async def show_fact(message: types.Message):
    uid = message.from_user.id
    lang = get_user_lang(uid)
    
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM facts WHERE id NOT IN 
                      (SELECT fact_id FROM seen_facts WHERE user_id = ?) 
                      ORDER BY RANDOM() LIMIT 1""", (uid,))
    f = cursor.fetchone()
    
    if not f:
        msg = {"uz": "Hamma faktlarni ko'rib bo'ldingiz! 🏁", "ru": "Вы посмотрели все факты! 🏁", "en": "You have seen all facts! 🏁"}
        return await message.answer(msg[lang])

    cursor.execute("INSERT INTO seen_facts VALUES (?, ?)", (uid, f[0]))
    conn.commit()
    conn.close()

    text = f[2] if lang == 'uz' else (f[3] if lang == 'ru' else f[4])
    
    nav = InlineKeyboardMarkup(row_width=2)
    nav.add(InlineKeyboardButton("⭐ Save", callback_data=f"save_{f[0]}"),
            InlineKeyboardButton("➡️ Next", callback_data="next"))
    
    await message.answer(f"<b>{f[1]}</b>\n\n{text}", parse_mode="HTML", reply_markup=nav)

@dp.callback_query_handler(lambda c: c.data == "next")
async def next_fact(callback: types.CallbackQuery):
    await callback.message.delete()
    await show_fact(callback.message)

@dp.callback_query_handler(lambda c: c.data.startswith('save_'))
async def save_fact(callback: types.CallbackQuery):
    fid = callback.data.split('_')[1]
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO saved_facts VALUES (?, ?)", (callback.from_user.id, fid))
    conn.commit()
    conn.close()
    await callback.answer("Saqlandi! ⭐")

@dp.message_handler(lambda m: "🕹" in m.text or "Quiz" in m.text or "Квиз" in m.text)
async def quiz(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facts ORDER BY RANDOM() LIMIT 1")
    f = cursor.fetchone()
    conn.close()

    text = f[2] if lang == 'uz' else (f[3] if lang == 'ru' else f[4])
    q_markup = InlineKeyboardMarkup(row_width=2)
    q_markup.add(InlineKeyboardButton("✅ True", callback_data=f"check_1_{f[5]}"),
                 InlineKeyboardButton("❌ False", callback_data=f"check_0_{f[5]}"))
    
    head = {"uz": "Bu rostmi?", "ru": "Это правда?", "en": "Is it true?"}
    await message.answer(f"🤔 <b>Quiz:</b>\n\n{text}\n\n<i>{head[lang]}</i>", parse_mode="HTML", reply_markup=q_markup)

@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def check_ans(callback: types.CallbackQuery):
    _, user_val, real_val = callback.data.split('_')
    lang = get_user_lang(callback.from_user.id)
    
    res = "✅ To'g'ri!" if user_val == real_val else "❌ Xato!"
    if lang == 'ru': res = "✅ Правильно!" if user_val == real_val else "❌ Ошибка!"
    if lang == 'en': res = "✅ Correct!" if user_val == real_val else "❌ Wrong!"
    
    await callback.message.edit_text(f"{callback.message.text}\n\n<b>Natija: {res}</b>", parse_mode="HTML")
    await quiz(callback.message) # Keyingi savolni yuborish

@dp.message_handler(lambda m: "📁" in m.text or "Saved" in m.text or "Сохраненные" in m.text)
async def list_saved(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("""SELECT facts.* FROM facts 
                      JOIN saved_facts ON facts.id = saved_facts.fact_id 
                      WHERE saved_facts.user_id = ?""", (message.from_user.id,))
    data = cursor.fetchall()
    conn.close()
    
    if not data:
        return await message.answer("Ro'yxat bo'sh. 🤷‍♂️")
    
    for f in data:
        text = f[2] if lang == 'uz' else (f[3] if lang == 'ru' else f[4])
        await message.answer(f"🌟 <b>{f[1]}</b>\n{text}", parse_mode="HTML")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)