import os
import asyncio
import logging
import sqlite3
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. SOZLAMALAR ---
# Tokenni BotFather'dan oling va aynan shu yerga qo'ying
API_TOKEN = '8694174995:AAHKH0m8oHyAvd_JoMO_fQc_MqUTuZoN5q8'

# Loglarni sozlash (xatolarni ko'rish uchun)
logging.basicConfig(level=logging.INFO)

# --- 2. BOT VA DISPATCHERNI YARATISH (Bu qism tepada bo'lishi shart!) ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- 3. MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS stats (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_text TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS history (user_id INTEGER, fact_id INTEGER)')
    conn.commit()
    conn.close()

init_db()

# --- 4. FAKTLAR BAZASI ---
facts_data = {
    "science": [
        [1, "🧬 Inson tanasidagi barcha DNK zanjirlari yoyilsa, Quyosh tizimidan chiqib ketadi.\n🇷🇺 Если развернуть все цепи ДНК человека, они выйдут за пределы Солнечной системы."],
        [2, "🧬 Suv kosmosda qaynamaydi, balki muzlab qoladi.\n🇷🇺 В космосе вода не кипит, а мгновенно замерзает."]
    ],
    "history": [
        [3, "📜 Qadimgi Misrda mushukni o'ldirish jinoyat hisoblangan.\n🇷🇺 В Древнем Египте убийство кошки считалось преступлением."],
        [4, "📜 Napoleon aslida past bo'yli bo'lmagan (168 sm).\n🇷🇺 Наполеон на самом деле не был низкого роста."]
    ],
    "tech": [
        [5, "💻 Birinchi kompyuter sichqonchasi yog'ochdan yasalgan.\n🇷🇺 Первая компьютерная мышь была сделана из дерева."],
        [6, "💻 Birinchi veb-sayt hali ham onlayn: info.cern.ch.\n🇷🇺 Первый веб-сайт до сих пор онлайн."]
    ]
}

# --- 5. RENDER UCHUN WEB SERVER ---
async def handle(request):
    return web.Response(text="Bot is running correctly!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render avtomatik portni 10000 ga ulaydi
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# --- 6. YORDAMCHI FUNKSIYALAR ---
def update_stats(user_id):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO stats (user_id, count) VALUES (?, 0)', (user_id,))
    cursor.execute('UPDATE stats SET count = count + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def add_to_history(user_id, fact_id):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO history VALUES (?, ?)', (user_id, fact_id))
    conn.commit()
    conn.close()

# --- 7. KLAVIATURALAR ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Science 🧬", "History 📜", "Tech 💻", "Random 🎲", "Saved ⭐", "Statistika 📊")
    return markup

def get_fact_kb(category, index, total):
    markup = InlineKeyboardMarkup(row_width=2)
    btns = []
    if index > 0:
        btns.append(InlineKeyboardButton("⬅️ Orqaga", callback_data=f"move_{category}_{index-1}"))
    if index < total - 1:
        btns.append(InlineKeyboardButton("Oldinga ➡️", callback_data=f"move_{category}_{index+1}"))
    markup.row(*btns)
    markup.add(InlineKeyboardButton("Saqlash ⭐", callback_data="save_this"))
    return markup

# --- 8. HANDLERLAR (Xabarlarni qabul qilish) ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Xush kelibsiz! Bo'limni tanlang:", reply_markup=get_main_menu())

@dp.message_handler(lambda m: m.text in ["Science 🧬", "History 📜", "Tech 💻", "Random 🎲"])
async def fact_handler(message: types.Message):
    cat_raw = message.text.split()[0].lower()
    cat = cat_raw if cat_raw != "random" else random.choice(["science", "history", "tech"])
    
    fact = facts_data[cat][0]
    idx = 0
    update_stats(message.from_user.id)
    add_to_history(message.from_user.id, fact[0])
    await message.answer(fact[1], reply_markup=get_fact_kb(cat, idx, len(facts_data[cat])))

@dp.callback_query_handler(lambda c: c.data.startswith('move_'))
async def navigation(call: types.CallbackQuery):
    _, cat, idx = call.data.split('_')
    idx = int(idx)
    fact = facts_data[cat][idx]
    update_stats(call.from_user.id)
    await call.message.edit_text(fact[1], reply_markup=get_fact_kb(cat, idx, len(facts_data[cat])))

@dp.callback_query_handler(text="save_this")
async def saver(call: types.CallbackQuery):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO saved VALUES (?, ?)', (call.from_user.id, call.message.text))
    conn.commit()
    conn.close()
    await call.answer("Saqlandi! ⭐")

@dp.message_handler(text="Statistika 📊")
async def stats(message: types.Message):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('SELECT count FROM stats WHERE user_id = ?', (message.from_user.id,))
    res = cursor.fetchone()
    count = res[0] if res else 0
    await message.answer(f"📊 Siz jami {count} ta faktni ko'rdingiz!")

@dp.message_handler(text="Saved ⭐")
async def saved_list(message: types.Message):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fact_text FROM saved WHERE user_id = ?', (message.from_user.id,))
    rows = cursor.fetchall()
    if not rows:
        await message.answer("Sizda hali saqlangan faktlar yo'q.")
    else:
        for r in rows[-3:]: # Oxirgi 3 tasini ko'rsatadi
            await message.answer(f"⭐ {r[0]}")

# --- 9. ISHGA TUSHIRISH ---
async def on_startup(dp):
    asyncio.create_task(start_web_server())

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)