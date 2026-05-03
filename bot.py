import sqlite3
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- KONFIGURATSIYA ---
API_TOKEN = '8694174995:AAHKH0m8oHyAvd_JoMO_fQc_MqUTuZoN5q8' 
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


def init_db():
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz')''')
    # Faktlar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS facts 
                      (id INTEGER PRIMARY KEY, category TEXT, 
                       uz TEXT, ru TEXT, en TEXT, is_true INTEGER)''')
    # Ko'rilgan faktlar
    cursor.execute('''CREATE TABLE IF NOT EXISTS seen_facts 
                      (user_id INTEGER, fact_id INTEGER)''')
    # Saqlangan faktlar
    cursor.execute('''CREATE TABLE IF NOT EXISTS saved_facts 
                      (user_id INTEGER, fact_id INTEGER)''')
    
    # Namuna faktlar (Agar baza bo'sh bo'lsa)
    cursor.execute("SELECT count(*) FROM facts")
    if cursor.fetchone()[0] == 0:
        sample_facts = [
            ('Fan', 'Yulduzlar aslida miltillamaydi.', 'Звезды на самом деле не мерцают.', 'Stars don’t actually twinkle.', 1),
            ('Tarix', 'Napoleon bo''yi juda past bo''lmagan.', 'Наполеон не был очень маленького роста.', 'Napoleon was not very short.', 1),
            ('Dunyo', 'Fillar sakray olmaydi.', 'Слоны не умеют прыгать.', 'Elephants cannot jump.', 1)
        ]
        cursor.executemany("INSERT INTO facts (category, uz, ru, en, is_true) VALUES (?,?,?,?,?)", sample_facts)
    
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
    user_id = message.from_id
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    
    lang = get_user_lang(user_id)
    welcome = {"uz": "Xush kelibsiz!", "ru": "Добро пожаловать!", "en": "Welcome!"}
    await message.answer(welcome[lang], reply_markup=get_keyboard(lang))

@dp.message_handler(lambda m: "🌐" in m.text)
async def change_lang(message: types.Message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"))
    markup.add(InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"))
    markup.add(InlineKeyboardButton("🇺🇸 English", callback_data="setlang_en"))
    await message.answer("Tilni tanlang / Выберите язык / Choose language:", reply_markup=markup)

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

@dp.message_handler(lambda m: "🎲" in m.text or "🔍" in m.text)
async def send_fact(message: types.Message):
    user_id = message.from_id
    lang = get_user_lang(user_id)
    
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    # Bitta faktni takrorlamaslik uchun filtr
    cursor.execute("""SELECT * FROM facts WHERE id NOT IN 
                      (SELECT fact_id FROM seen_facts WHERE user_id = ?) 
                      ORDER BY RANDOM() LIMIT 1""", (user_id,))
    fact = cursor.fetchone()
    
    if not fact:
        msg = {"uz": "Faktlar tugadi!", "ru": "Факты закончились!", "en": "No more facts!"}
        await message.answer(msg[lang])
        return

    # Ko'rildi deb belgilash
    cursor.execute("INSERT INTO seen_facts VALUES (?, ?)", (user_id, fact[0]))
    conn.commit()
    conn.close()

    text = fact[2] if lang == 'uz' else (fact[3] if lang == 'ru' else fact[4])
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⬅️", callback_data="prev"), # Bu mantiqni baza orqali kengaytirish mumkin
        InlineKeyboardButton("💾", callback_data=f"save_{fact[0]}"),
        InlineKeyboardButton("➡️", callback_data="next_fact")
    )
    
    await message.answer(f"<b>[{fact[1]}]</b>\n\n{text}", parse_mode="HTML", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data == "next_fact")
async def next_fact_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await send_fact(callback.message)

@dp.callback_query_handler(lambda c: c.data.startswith('save_'))
async def save_fact(callback: types.CallbackQuery):
    fact_id = callback.data.split('_')[1]
    user_id = callback.from_user.id
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO saved_facts VALUES (?, ?)", (user_id, fact_id))
    conn.commit()
    conn.close()
    await callback.answer("⭐ Saved!")

@dp.message_handler(lambda m: "🎮" in m.text)
async def quiz_mode(message: types.Message):
    user_id = message.from_id
    lang = get_user_lang(user_id)
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facts ORDER BY RANDOM() LIMIT 1")
    fact = cursor.fetchone()
    conn.close()

    text = fact[2] if lang == 'uz' else (fact[3] if lang == 'ru' else fact[4])
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Rost", callback_data=f"quiz_1_{fact[5]}"),
        InlineKeyboardButton("❌ Yolg'on", callback_data=f"quiz_0_{fact[5]}")
    )
    q_text = {"uz": "Ushbu fakt rostmi?", "ru": "Это правда?", "en": "Is this true?"}
    await message.answer(f"{text}\n\n{q_text[lang]}", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('quiz_'))
async def check_quiz(callback: types.CallbackQuery):
    data = callback.data.split('_')
    user_choice = int(data[1])
    correct_answer = int(data[2])
    
    if user_choice == correct_answer:
        await callback.answer("To'g'ri! 🎉", show_alert=True)
    else:
        await callback.answer("Xato! 🧐", show_alert=True)
    await callback.message.delete()
    await quiz_mode(callback.message)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)