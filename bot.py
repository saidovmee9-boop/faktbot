import os
import logging
import random
import sqlite3

from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    views INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    fact TEXT,
    PRIMARY KEY(user_id, fact)
)
""")

conn.commit()

# ================= FACTS (EN + UZ + RU) =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Suv 100°C da qaynaydi", "Вода кипит при 100°C"),
        ("Earth orbits the Sun", "Yer Quyosh atrofida aylanadi", "Земля вращается вокруг Солнца"),
        ("Humans have 206 bones", "Insonda 206 ta suyak bor", "У человека 206 костей"),
    ],
    "history": [
        ("WW2 ended in 1945", "2-jahon urushi 1945 da tugagan", "Вторая мировая война закончилась в 1945"),
        ("Rome was founded in 753 BC", "Rim miloddan avval 753 yilda asos solingan", "Рим основан в 753 году до н.э."),
    ],
    "tech": [
        ("Python is a popular language", "Python mashhur dasturlash tili", "Python — популярный язык программирования"),
        ("AI stands for Artificial Intelligence", "AI — sun'iy intellekt", "ИИ — искусственный интеллект"),
    ]
}

user_data = {}

# ================= AUTO USER REGISTER =================
async def ensure_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

# ================= START MENU =================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "📜 History", "💻 Tech")
    kb.add("🎲 Random", "❤️ Saved", "📊 Stats")
    return kb

# ================= ANY MESSAGE HANDLER (NO /start needed) =================
@dp.message_handler()
async def any_message(message: types.Message):
    await ensure_user(message.from_user.id)

    if message.text in ["📚 Science", "📜 History", "💻 Tech"]:
        await category(message)
        return

    if message.text == "🎲 Random":
        await random_fact(message)
        return

    if message.text == "❤️ Saved":
        await saved(message)
        return

    if message.text == "📊 Stats":
        await stats(message)
        return

    await message.answer("📌 Menyudan foydalaning:", reply_markup=main_kb())


# ================= CATEGORY =================
async def category(message: types.Message):
    cat_map = {
        "📚 Science": "science",
        "📜 History": "history",
        "💻 Tech": "tech"
    }

    cat = cat_map[message.text]
    user_data[message.from_user.id] = {"cat": cat, "index": 0}

    await send_fact(message.chat.id, message.from_user.id, cat, 0)


# ================= SEND FACT (EDIT MESSAGE = IDEAL UX) =================
async def send_fact(chat_id, user_id, cat, index, message_id=None):
    fact_en, fact_uz, fact_ru = FACTS[cat][index]

    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []

    if index > 0:
        buttons.append(types.InlineKeyboardButton("⬅️", callback_data="prev"))
    if index < len(FACTS[cat]) - 1:
        buttons.append(types.InlineKeyboardButton("➡️", callback_data="next"))

    buttons.append(types.InlineKeyboardButton("❤️ Save", callback_data=f"save|{cat}|{index}"))
    kb.add(*buttons)

    cursor.execute("UPDATE users SET views = views + 1 WHERE user_id=?", (user_id,))
    conn.commit()

    text = (
        f"📌 FACT\n\n"
        f"🇬🇧 {fact_en}\n"
        f"🇺🇿 {fact_uz}\n"
        f"🇷🇺 {fact_ru}"
    )

    if message_id:
        await bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    else:
        await bot.send_message(chat_id, text, reply_markup=kb)


# ================= NAVIGATION =================
@dp.callback_query_handler(lambda c: c.data in ["next", "prev"])
async def nav(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in user_data:
        return await call.answer("Avval kategoriya tanlang")

    data = user_data[user_id]
    cat = data["cat"]
    index = data["index"]

    index += 1 if call.data == "next" else -1
    index = max(0, min(index, len(FACTS[cat]) - 1))

    user_data[user_id]["index"] = index

    await send_fact(call.message.chat.id, user_id, cat, index, call.message.message_id)
    await call.answer()


# ================= SAVE =================
@dp.callback_query_handler(lambda c: c.data.startswith("save"))
async def save(call: types.CallbackQuery):
    _, cat, idx = call.data.split("|")
    idx = int(idx)

    fact_en, _, _ = FACTS[cat][idx]

    cursor.execute(
        "INSERT OR IGNORE INTO saved VALUES (?, ?)",
        (call.from_user.id, fact_en)
    )
    conn.commit()

    await call.answer("❤️ Saqlandi!")


# ================= RANDOM =================
async def random_fact(message: types.Message):
    cat = random.choice(list(FACTS.keys()))
    fact_en, fact_uz, fact_ru = random.choice(FACTS[cat])

    await message.answer(
        f"🎲 RANDOM\n\n🇬🇧 {fact_en}\n🇺🇿 {fact_uz}\n🇷🇺 {fact_ru}"
    )


# ================= SAVED =================
async def saved(message: types.Message):
    cursor.execute("SELECT fact FROM saved WHERE user_id=?", (message.from_user.id,))
    data = cursor.fetchall()

    if not data:
        return await message.answer("Hech narsa yo‘q 😢")

    for f in data:
        await message.answer(f"❤️ {f[0]}")


# ================= STATS =================
async def stats(message: types.Message):
    cursor.execute("SELECT views FROM users WHERE user_id=?", (message.from_user.id,))
    row = cursor.fetchone()

    views = row[0] if row else 0
    await message.answer(f"📊 Siz {views} ta fakt ko‘rgansiz")


# ================= WEB SERVER =================
runner = None

async def handle(request):
    return web.Response(text="Bot is running!")

async def on_startup(dp):
    global runner

    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("Web server started")

async def on_shutdown(dp):
    global runner
    if runner:
        await runner.cleanup()


# ================= START =================
if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )