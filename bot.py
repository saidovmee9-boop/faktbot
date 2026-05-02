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
API_TOKEN = 'TOKENINGIZNI_SHU_YERGA_QO_YING'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- 2. MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS stats (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_text TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS history (user_id INTEGER, fact_id INTEGER)')
    conn.commit()
    conn.close()

init_db()

# --- 3. PROFESSIONAL FAKTLAR BAZASI (3 Tilda) ---
facts_data = {
    "science": [
        [1, "🧬 **Inson DNKsi 98% banan bilan bir xil.**\n🇷🇺 ДНК человека на 98% совпадает с ДНК банана.\n🇬🇧 Human DNA is 98% identical to a banana."],
        [2, "🧬 **Suv kosmosda qaynamaydi, balki muzlab qoladi.**\n🇷🇺 В космосе вода не кипит, а мгновенно замерзает.\n🇬🇧 Water doesn't boil in space, it freezes."],
        [3, "🧬 **Ahtapotlarning 3 ta yuragi va 9 ta miyasi bor.**\n🇷🇺 У осьминогов 3 сердца и 9 мозгов.\n🇬🇧 Octopuses have 3 hearts and 9 brains."],
        [4, "🧬 **Inson tanasidagi barcha bakteriyalar vazni 2 kg gacha yetadi.**\n🇷🇺 Все бактерии в теле человека весят около 2 кг.\n🇬🇧 All the bacteria in the human body weigh about 2 kg."],
        [5, "🧬 **Yulduzlararo masofa shu qadar kattaki, agar Quyosh tennis koptogi bo'lsa, eng yaqin yulduz 1000 km uzoqda bo'ladi.**\n🇷🇺 Если Солнце — теннисный мяч, то ближайшая звезда будет в 1000 км.\n🇬🇧 If the Sun were a tennis ball, the nearest star would be 1000 km away."]
    ],
    "history": [
        [6, "📜 **Napoleon aslida past bo'yli bo'lmagan (168 sm).**\n🇷🇺 Наполеон на самом деле не был коротышкой (168 см).\n🇬🇧 Napoleon was not actually short (168 cm)."],
        [7, "📜 **Qadimgi Rimda tish pastasi o'rnida siydik ishlatilgan.**\n🇷🇺 В Древнем Риме мочу использовали вместо зубной пасты.\n🇬🇧 In Ancient Rome, urine was used instead of toothpaste."],
        [8, "📜 **Kleopatra ehromlar qurilgandan ko'ra, iPhone ixtirosiga yaqinroq vaqtda yashagan.**\n🇷🇺 Клеопатра жила ближе к изобретению iPhone, чем к строительству пирамид.\n🇬🇧 Cleopatra lived closer to the invention of the iPhone than the building of the pyramids."],
        [9, "📜 **O'rta asrlarda hayvonlar sud qilinishi mumkin edi.**\n🇷🇺 В Средние века животных могли вызвать в суд.\n🇬🇧 In the Middle Ages, animals could be put on trial."],
        [10, "📜 **Muzqaymoq aslida Xitoyda ixtiro qilingan.**\n🇷🇺 Мороженое было изобретено в Китае.\n🇬🇧 Ice cream was actually invented in China."]
    ],
    "tech": [
        [11, "💻 **Birinchi kompyuter sichqonchasi yog'ochdan yasalgan.**\n🇷🇺 Первая компьютерная мышь была сделана из дерева.\n🇬🇧 The first computer mouse was made of wood."],
        [12, "💻 **Dunyodagi barcha Bitcoinlarning 20% ga yaqini unutilgan parollar tufayli yo'qolgan.**\n🇷🇺 Около 20% всех биткоинов потеряны из-за забытых паролей.\n🇬🇧 About 20% of all Bitcoins are lost due to forgotten passwords."],
        [13, "💻 **Google nomi 'Googol' (1 va 100 ta nol) so'zidan xato yozilish natijasida kelib chiqqan.**\n🇷🇺 Название Google возникло из-за ошибки в слове 'Googol'.\n🇬🇧 Google was named after a misspelling of 'Googol'."],
        [14, "💻 **Internetning og'irligi taxminan bitta kichik qulupnayga teng (elektronlar vazni).**\n🇷🇺 Весь интернет весит примерно как одна клубника.\n🇬🇧 The entire internet weighs about as much as a single strawberry."],
        [15, "💻 **Hozirgi kalkulyatorlar Oydagi birinchi odamni boshqargan kompyuterdan kuchliroq.**\n🇷🇺 Современные калькуляторы мощнее компьютера, отправившего людей на Луну.\n🇬🇧 Modern calculators are more powerful than the computer that sent humans to the Moon."]
    ]
}

# --- 4. RENDER WEB SERVER ---
async def handle(request):
    return web.Response(text="Pro Fact Bot is Online 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# --- 5. YORDAMCHI FUNKSIYALAR ---
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
    cursor.execute('INSERT OR IGNORE INTO history VALUES (?, ?)', (user_id, fact_id))
    conn.commit()
    conn.close()

def get_viewed_ids(user_id):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fact_id FROM history WHERE user_id = ?', (user_id,))
    res = [r[0] for r in cursor.fetchall()]
    conn.close()
    return res

# --- 6. PROFESSIONAL KLAVIATURALAR ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Science 🧬", "History 📜", "Tech 💻", "Random 🎲", "Saved ⭐", "Statistika 📊")
    return markup

def get_fact_kb(category, index, total):
    markup = InlineKeyboardMarkup(row_width=2)
    btns = []
    if index > 0:
        btns.append(InlineKeyboardButton("⬅️ Back / Orqaga", callback_data=f"move_{category}_{index-1}"))
    if index < total - 1:
        btns.append(InlineKeyboardButton("Next / Oldinga ➡️", callback_data=f"move_{category}_{index+1}"))
    markup.row(*btns)
    markup.add(InlineKeyboardButton("Save ⭐ Saqlash", callback_data="save_this"))
    return markup

# --- 7. HANDLERLAR ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    welcome_text = (
        "👋 **Welcome to Pro Fact Bot!**\n\n"
        "✨ Discover amazing facts in 3 languages!\n"
        "✨ 3 tilda ajoyib faktlarni kashf eting!\n"
        "✨ Откройте удивительные факты на 3 языках!"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.message_handler(lambda m: m.text in ["Science 🧬", "History 📜", "Tech 💻", "Random 🎲"])
async def fact_handler(message: types.Message):
    cat_raw = message.text.split()[0].lower()
    category = cat_raw if cat_raw != "random" else random.choice(["science", "history", "tech"])
    
    viewed = get_viewed_ids(message.from_user.id)
    available = [f for f in facts_data[category] if f[0] not in viewed]
    
    # Agar hamma fakt ko'rilgan bo'lsa, birinchisini ko'rsatadi
    fact = available[0] if available else facts_data[category][0]
    idx = facts_data[category].index(fact)
    
    update_stats(message.from_user.id)
    add_to_history(message.from_user.id, fact[0])
    
    await message.answer(fact[1], reply_markup=get_fact_kb(category, idx, len(facts_data[category])), parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('move_'))
async def navigation(call: types.CallbackQuery):
    _, cat, idx = call.data.split('_')
    idx = int(idx)
    fact = facts_data[cat][idx]
    
    update_stats(call.from_user.id)
    add_to_history(call.from_user.id, fact[0])
    
    try:
        await call.message.edit_text(fact[1], reply_markup=get_fact_kb(cat, idx, len(facts_data[cat])), parse_mode="Markdown")
    except:
        await call.answer()

@dp.callback_query_handler(text="save_this")
async def saver(call: types.CallbackQuery):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO saved VALUES (?, ?)', (call.from_user.id, call.message.text))
    conn.commit()
    conn.close()
    await call.answer("✅ Saved / Saqlandi / Сохранено")

@dp.message_handler(text="Statistika 📊")
async def stats(message: types.Message):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('SELECT count FROM stats WHERE user_id = ?', (message.from_user.id,))
    res = cursor.fetchone()
    count = res[0] if res else 0
    await message.answer(f"📊 **Total Facts Viewed:** {count}\n📊 **Jami ko'rilgan:** {count}\n📊 **Всего просмотрено:** {count}", parse_mode="Markdown")

@dp.message_handler(text="Saved ⭐")
async def saved_list(message: types.Message):
    conn = sqlite3.connect('pro_fact.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fact_text FROM saved WHERE user_id = ?', (message.from_user.id,))
    rows = cursor.fetchall()
    if not rows:
        await message.answer("📭 Your list is empty.")
    else:
        for r in rows[-3:]: # Oxirgi 3 tasini chiqaradi
            await message.answer(f"⭐ {r[0]}", parse_mode="Markdown")

# --- 8. ISHGA TUSHIRISH ---
async def on_startup(dp):
    asyncio.create_task(start_web_server())

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)