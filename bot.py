import logging
import asyncio
import sqlite3
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
# DIQQAT: Yangi tokenni aynan shu yerga qo'shtirnoq ichiga yozing!
API_TOKEN = 'SIZNING_YANGI_TOKENINGIZ'

logging.basicConfig(level=logging.INFO)

# Eski hamma narsani o'chirib, o'rniga shuni yozing:
API_TOKEN = '8694174995:AAHKH0m8oHyAvd_JoMO_fQc_MqUTuZoN5q8' # BotFather bergan tokenni shu yerga qo'ying
bot = Bot(token=API_TOKEN)

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    # Statistika uchun
    cursor.execute('CREATE TABLE IF NOT EXISTS stats (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)')
    # Saqlanganlar uchun
    cursor.execute('CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_text TEXT)')
    # Ko'rilgan faktlarni eslab qolish uchun
    cursor.execute('CREATE TABLE IF NOT EXISTS history (user_id INTEGER, fact_id INTEGER)')
    conn.commit()
    conn.close()

init_db()

# --- FAKTLAR (UZ/RU) ---
# Format: [id, "UZ | RU"]
facts_data = {
    "science": [
        [1, "🧬 Inson tanasidagi barcha DNK zanjirlari yoyilsa, Quyosh tizimidan chiqib ketadi.\n🇷🇺 Если развернуть все цепи ДНК человека, они выйдут за пределы Солнечной системы."],
        [2, "🧬 Suv kosmosda qaynamaydi, balki muzlab qoladi.\n🇷🇺 В космосе вода не кипит, а мгновенно замерзает."],
        [3, "🧬 Yer yuzidagi eng qattiq tabiiy modda - Olmos.\n🇷🇺 Самое твердое природное вещество на Земле — алмаз."]
    ],
    "history": [
        [4, "📜 Qadimgi Misrda mushukni o'ldirish eng og'ir jinoyat hisoblangan.\n🇷🇺 В Древнем Египте убийство кошки считалось тягчайшим преступлением."],
        [5, "📜 Buyuk Britaniya va Zanzibar o'rtasidagi urush 38 daqiqa davom etgan.\n🇷🇺 Война между Великобританией и Занзибаром длилась всего 38 минут."],
        [6, "📜 Napoleon aslida past bo'yli bo'lmagan (168 sm).\n🇷🇺 Наполеон на самом деле не был низкого роста (168 см)."]
    ],
    "tech": [
        [7, "💻 Dunyodagi birinchi veb-sayt hali ham onlayn: info.cern.ch.\n🇷🇺 Первый в мире веб-сайт до сих пор онлайн: info.cern.ch."],
        [8, "💻 'QWERTY' klaviaturasi yozishni sekinlashtirish uchun o'ylab topilgan.\n🇷🇺 Раскладка 'QWERTY' была придумана, чтобы замедлить скорость печати."],
        [9, "💻 Birinchi 1GB xotira qurilmasi muzlatgichdek bo'lgan.\n🇷🇺 Первое запоминающее устройство на 1 ГБ было размером с холодильник."]
    ]
}

# --- RENDER WEB SERVER ---
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# --- YORDAMCHI FUNKSIYALAR ---
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

def get_viewed_ids(user_id):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fact_id FROM history WHERE user_id = ?', (user_id,))
    res = [r[0] for r in cursor.fetchall()]
    conn.close()
    return res

# --- KLAVIATURA ---
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

# --- HANDLERLAR ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Sizga qanday faktlar kerak? Tanlang:", reply_markup=get_main_menu())

@dp.message_handler(lambda m: m.text in ["Science 🧬", "History 📜", "Tech 💻", "Random 🎲"])
async def fact_handler(message: types.Message):
    cat = message.text.split()[0].lower()
    if cat == "random":
        cat = random.choice(["science", "history", "tech"])
    
    viewed = get_viewed_ids(message.from_user.id)
    # Ko'rilmaganini topish
    available_facts = [f for f in facts_data[cat] if f[0] not in viewed]
    
    if not available_facts:
        await message.answer("Siz bu bo'limdagi barcha faktlarni ko'rib bo'ldingiz! ✅")
        return

    fact = available_facts[0]
    idx = facts_data[cat].index(fact)
    
    update_stats(message.from_user.id)
    add_to_history(message.from_user.id, fact[0])
    
    await message.answer(fact[1], reply_markup=get_fact_kb(cat, idx, len(facts_data[cat])))

@dp.callback_query_handler(lambda c: c.data.startswith('move_'))
async def navigation(call: types.CallbackQuery):
    _, cat, idx = call.data.split('_')
    idx = int(idx)
    fact = facts_data[cat][idx]
    
    update_stats(call.from_user.id)
    add_to_history(call.from_user.id, fact[0])
    
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
    await message.answer(f"📊 Siz jami {count} ta faktni ko'rib chiqdingiz!")

@dp.message_handler(text="Saved ⭐")
async def saved_list(message: types.Message):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fact_text FROM saved WHERE user_id = ?', (message.from_user.id,))
    rows = cursor.fetchall()
    if not rows:
        await message.answer("Saqlanganlar bo'sh.")
    else:
        for r in rows[-3:]:
            await message.answer(f"⭐ {r[0]}")

# --- ISHGA TUSHIRISH ---
async def on_startup(dp):
    asyncio.create_task(start_web_server())

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)