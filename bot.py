import os
import asyncio
import sqlite3
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8694174995:AAHeqynj_AfzkaNuNCdqtJ0xQBdpoyUlusI'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    # Foydalanuvchilar va statistika
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, daily_count INTEGER DEFAULT 0)''')
    # Saqlangan faktlar
    cursor.execute('''CREATE TABLE IF NOT EXISTS saved_facts 
                      (user_id INTEGER, fact_text TEXT)''')
    # Ko'rilgan faktlar (qaytarilmasligi uchun)
    cursor.execute('''CREATE TABLE IF NOT EXISTS viewed_facts 
                      (user_id INTEGER, fact_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- FAKTLAR BAZASI (NAMUNA) ---
# Haqiqiy botda buni JSON yoki kattaroq lug'at qilish tavsiya etiladi
facts_data = {
    "science": [
        "🇺🇿 Suv molekulasi 2 ta vodorod va 1 ta kisloroddan iborat. | 🇷🇺 Молекула воды состоит из 2 водородов и 1 кислорода.",
        "🇺🇿 Yorug'lik tezligi sekundiga 300,000 km. | 🇷🇺 Скорость света 300,000 км/с."
    ],
    "history": [
        "🇺🇿 Amir Temur 1336-yilda tug'ilgan. | 🇷🇺 Амир Темур родился в 1336 году.",
        "🇺🇿 Ikkinchi jahon urushi 1945-yilda tugagan. | 🇷🇺 Вторая мировая война закончилась в 1945 году."
    ],
    "tech": [
        "🇺🇿 Birinchi kompyuter sichqonchasi yog'ochdan yasalgan. | 🇷🇺 Первая компьютерная мышь была сделана из дерева.",
        "🇺🇿 Python tili 1991-yilda yaratilgan. | 🇷🇺 Язык Python был создан в 1991 году."
    ]
}

# --- WEB SERVER (RENDER UCHUN) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# --- YORDAMCHI FUNKSIYALAR ---
def get_user_data(user_id):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("SELECT daily_count FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()[0]
    conn.close()
    return res

def update_stat(user_id):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET daily_count = daily_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- KLAVIATURA ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Science 🧬", "History 📜", "Tech 💻", "Random 🎲", "Saved ⭐", "Statistika 📊")
    return markup

def get_fact_kb(category, index, total, fact_text):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton("⬅️ Orqaga", callback_data=f"prev_{category}_{index}"))
    if index < total - 1:
        buttons.append(InlineKeyboardButton("Oldinga ➡️", callback_data=f"next_{category}_{index}"))
    
    markup.row(*buttons)
    markup.add(InlineKeyboardButton("Saqlash ⭐", callback_data="save_this"))
    return markup

# --- HANDLERLAR ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Xush kelibsiz! Faktlar dunyosiga marhamat.", reply_markup=main_menu())

@dp.message_handler(lambda m: m.text in ["Science 🧬", "History 📜", "Tech 💻", "Random 🎲"])
async def show_fact(message: types.Message):
    cat_map = {"Science 🧬": "science", "History 📜": "history", "Tech 💻": "tech", "Random 🎲": "random"}
    category = cat_map[message.text]
    
    if category == "random":
        category = random.choice(["science", "history", "tech"])
    
    fact = facts_data[category][0]
    update_stat(message.from_user.id)
    await message.answer(fact, reply_markup=get_fact_kb(category, 0, len(facts_data[category]), fact))

@dp.callback_query_handler(lambda c: c.data.startswith(('next_', 'prev_')))
async def navigate_facts(callback: types.CallbackQuery):
    _, category, index = callback.data.split('_')
    index = int(index)
    new_index = index + 1 if callback.data.startswith('next_') else index - 1
    
    fact = facts_data[category][new_index]
    update_stat(callback.from_user.id)
    await callback.message.edit_text(fact, reply_markup=get_fact_kb(category, new_index, len(facts_data[category]), fact))

@dp.callback_query_handler(text="save_this")
async def save_fact(callback: types.CallbackQuery):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO saved_facts VALUES (?, ?)", (callback.from_user.id, callback.message.text))
    conn.commit()
    conn.close()
    await callback.answer("Saqlandi!")

@dp.message_handler(text="Saved ⭐")
async def show_saved(message: types.Message):
    conn = sqlite3.connect('factbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT fact_text FROM saved_facts WHERE user_id = ?", (message.from_user.id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await message.answer("Sizda saqlangan faktlar yo'q.")
    else:
        for r in rows:
            await message.answer(f"⭐ {r[0]}")

@dp.message_handler(text="Statistika 📊")
async def show_stat(message: types.Message):
    count = get_user_data(message.from_user.id)
    await message.answer(f"📊 Siz jami {count} ta fakt ko'rgansiz.")

# --- ISHGA TUSHIRISH ---
async def on_startup(dp):
    await start_web_server()

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)