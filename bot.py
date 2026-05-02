import os
import logging
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

if not TOKEN or not BASE_URL:
    raise Exception("ENV missing")

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
conn = sqlite3.connect("/tmp/bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS saved (
    user_id INTEGER,
    en TEXT,
    ru TEXT,
    uz TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    user_id INTEGER,
    count INTEGER DEFAULT 0
)
""")
conn.commit()

# ================= FACTS (BIG DATABASE) =================
FACTS = {
    "science": [
        ("Water boils at 100°C", "Вода кипит при 100°C", "Suv 100°C da qaynaydi"),
        ("Earth orbits the Sun", "Земля вращается вокруг Солнца", "Yer Quyosh atrofida aylanadi"),
        ("Humans have 206 bones", "У человека 206 костей", "Insonda 206 suyak bor"),
    ],
    "history": [
        ("WW2 ended in 1945", "WW2 закончилась 1945", "WW2 1945 tugagan"),
        ("Roman Empire fell in 476", "Рим пал в 476", "Rim imperiyasi 476 da qulagan"),
    ],
    "tech": [
        ("Internet started in 1983", "Интернет 1983", "Internet 1983"),
        ("AI means Artificial Intelligence", "ИИ — искусственный интеллект", "AI sun’iy intellekt"),
    ]
}

USED = set()
USER_STATE = {}

# ================= LOGIC =================
def get_fact(cat):
    pool = FACTS.get(cat, [])
    available = [f for f in pool if f[0] not in USED]

    if not available:
        USED.clear()
        available = pool

    fact = random.choice(available)
    USED.add(fact[0])
    return fact

def random_fact():
    all_facts = sum(FACTS.values(), [])
    return random.choice(all_facts)

# ================= UI =================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📚 Science", "🏛 History")
    kb.add("💻 Tech", "🎲 Random")
    kb.add("⭐ Saved", "📊 Stats")
    return kb

def nav():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        types.InlineKeyboardButton("➡️ Next", callback_data="next")
    )
    kb.add(types.InlineKeyboardButton("⭐ Save", callback_data="save"))
    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 <b>FACT BOT PRO</b>", parse_mode="HTML", reply_markup=main_menu())

# ================= CATEGORY =================
@dp.message_handler(lambda m: m.text in ["📚 Science", "🏛 History", "💻 Tech"])
async def category(m: types.Message):
    cat = m.text.split()[1].lower()
    fact = get_fact(cat)

    USER_STATE[m.from_user.id] = {"cat": cat, "fact": fact}

    await m.answer(format_fact(cat, fact), reply_markup=nav(), parse_mode="HTML")

# ================= RANDOM =================
@dp.message_handler(lambda m: m.text == "🎲 Random")
async def random_handler(m: types.Message):
    fact = random_fact()

    USER_STATE[m.from_user.id] = {"cat": "random", "fact": fact}

    await m.answer(
        format_fact("🎲 RANDOM", fact),
        reply_markup=nav(),
        parse_mode="HTML"
    )

# ================= NAV =================
@dp.callback_query_handler(lambda c: c.data in ["next", "prev"])
async def nav_handler(c: types.CallbackQuery):
    uid = c.from_user.id

    if uid not in USER_STATE:
        return await c.answer("Start first")

    cat = USER_STATE[uid]["cat"]

    fact = random_fact() if cat == "random" else get_fact(cat)

    USER_STATE[uid]["fact"] = fact

    await c.message.edit_text(
        format_fact(cat.upper(), fact),
        reply_markup=nav(),
        parse_mode="HTML"
    )

    await c.answer()

# ================= SAVE =================
@dp.callback_query_handler(lambda c: c.data == "save")
async def save(c: types.CallbackQuery):
    uid = c.from_user.id
    if uid not in USER_STATE:
        return await c.answer("No fact")

    en, ru, uz = USER_STATE[uid]["fact"]

    cursor.execute("INSERT INTO saved VALUES (?,?,?,?)", (uid, en, ru, uz))
    conn.commit()

    await c.answer("⭐ Saved")

# ================= SAVED =================
@dp.message_handler(lambda m: m.text == "⭐ Saved")
async def saved(m: types.Message):
    cursor.execute("SELECT en, ru, uz FROM saved WHERE user_id=?", (m.from_user.id,))
    rows = cursor.fetchall()

    if not rows:
        return await m.answer("No saved facts")

    text = "⭐ SAVED FACTS:\n\n"
    for r in rows[-10:]:
        text += format_fact("SAVED", r) + "\n\n"

    await m.answer(text, parse_mode="HTML")

# ================= STATS =================
@dp.message_handler(lambda m: m.text == "📊 Stats")
async def stats(m: types.Message):
    cursor.execute("SELECT COUNT(*) FROM saved WHERE user_id=?", (m.from_user.id,))
    count = cursor.fetchone()[0]

    await m.answer(
        f"📊 <b>YOUR STATS</b>\n\n"
        f"⭐ Saved facts: <b>{count}</b>\n"
        f"🔄 Daily tracking ready",
        parse_mode="HTML"
    )

# ================= FORMAT =================
def format_fact(title, fact):
    return (
        f"📚 <b>{title}</b>\n\n"
        f"🇬🇧 {fact[0]}\n"
        f"🇷🇺 {fact[1]}\n"
        f"🇺🇿 {fact[2]}"
    )

# ================= WEBHOOK =================
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )