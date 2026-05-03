import os
import sqlite3
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS saved (uid INTEGER, text TEXT)")
init_db()

# ================= FACTS (3 TIL BIRGA) =================
FACTS = {
    "science": [
        ("Inson DNKsi bananga o‘xshaydi","ДНК человека похожа на банан","Human DNA is similar to banana"),
        ("Miya uxlaganda ham ishlaydi","Мозг работает во сне","Brain works during sleep"),
        ("Suv kosmosda muzlaydi","Вода в космосе замерзает","Water freezes in space"),
        ("Yurak 24/7 ishlaydi","Сердце работает 24/7","Heart works 24/7"),
        ("Odam 70% suv","Человек 70% вода","Human is 70% water"),
        ("Bakteriyalar tanada bor","Бактерии есть в теле","Bacteria exist in body"),
        ("Yer aylanadi","Земля вращается","Earth rotates"),
        ("Miya kuchli","Мозг мощный","Brain is powerful"),
        ("Koinot kengayadi","Вселенная расширяется","Universe expands"),
        ("Tana energiya ishlab chiqaradi","Тело производит энергию","Body produces energy")
    ],
    "tech": [
        ("Internet harbiy loyiha edi","Интернет был военным проектом","Internet was a military project"),
        ("AI rivojlanmoqda","ИИ развивается","AI is evolving"),
        ("Telefon mini kompyuter","Телефон мини ПК","Phone is mini PC"),
        ("Kod dunyoni boshqaradi","Код управляет миром","Code runs the world"),
        ("Cloud tizim bor","Облачные системы","Cloud systems exist"),
        ("Server 24/7 ishlaydi","Сервер работает 24/7","Server runs 24/7"),
        ("Robotlar rivojlanadi","Роботы развиваются","Robots evolve"),
        ("Apps millionlab","Приложений миллионы","Millions of apps"),
        ("Cyber xavfsizlik muhim","Кибербезопасность важна","Cybersecurity matters"),
        ("Data juda qimmat","Данные дорогие","Data is valuable")
    ],
    "history": [
        ("Rim imperiyasi kuchli edi","Римская империя была сильной","Roman Empire was strong"),
        ("Kleopatra mashhur edi","Клеопатра была известной","Cleopatra was famous"),
        ("Vikinglar jangchi edi","Викинги были воинами","Vikings were warriors"),
        ("Piramidalar sirli","Пирамиды загадка","Pyramids are mysterious"),
        ("Tarix juda boy","История богата","History is rich"),
        ("Urushlar bo‘lgan","Были войны","Wars happened"),
        ("Qirollar davri","Эпоха королей","Age of kings"),
        ("Imperiyalar qulagan","Империи пали","Empires fell"),
        ("Qadimiy shaharlar","Древние города","Ancient cities"),
        ("O‘tmish qiziq","Прошлое интересно","Past is interesting")
    ]
}

# ================= STATE =================
state = {}

# ================= MENU =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech")
    kb.add("📜 History","❤️ Saved")
    kb.add("📊 Stats")
    return kb

# ================= SHOW =================
async def show(uid, chat_id):
    st = state[uid]
    cat = st["cat"]
    i = st["i"]

    fact = FACTS[cat][i]

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data="save"))

    text = f"🇺🇿 {fact[0]}\n🇷🇺 {fact[1]}\n🇬🇧 {fact[2]}"

    await bot.send_message(chat_id, text, reply_markup=kb)

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    await m.answer("🚀 Fact Bot Ready", reply_markup=menu())

# ================= CATEGORY =================
@dp.message_handler()
async def h(m):
    uid = m.from_user.id
    t = m.text

    if "Science" in t: cat="science"
    elif "Tech" in t: cat="tech"
    elif "History" in t: cat="history"
    elif "Saved" in t: return await saved(m)
    elif "Stats" in t: return await stats(m)
    else: return

    state[uid] = {"cat":cat,"i":0}
    await show(uid,m.chat.id)

# ================= NAV =================
@dp.callback_query_handler(lambda c:c.data in ["next","prev"])
async def nav(c):
    uid=c.from_user.id
    st=state.get(uid)
    if not st: return

    if c.data=="next":
        st["i"]=(st["i"]+1)%10
    else:
        st["i"]=(st["i"]-1)%10

    await show(uid,c.message.chat.id)

# ================= SAVE =================
@dp.callback_query_handler(lambda c:c.data=="save")
async def save(c):
    with db() as conn:
        conn.execute("INSERT INTO saved VALUES (?,?)",(c.from_user.id,c.message.text))
    await c.answer("❤️ Saved")

# ================= SAVED =================
@dp.message_handler(lambda m:"Saved" in m.text or "❤️" in m.text)
async def saved(m):
    with db() as c:
        rows=c.execute("SELECT text FROM saved WHERE uid=?",(m.from_user.id,)).fetchall()

    if not rows:
        return await m.answer("Empty")

    txt="❤️ SAVED:\n\n"
    for r in rows:
        txt+=f"{r[0]}\n\n"

    await m.answer(txt)

# ================= STATS =================
@dp.message_handler(lambda m:"Stats" in m.text)
async def stats(m):
    with db() as c:
        count=c.execute("SELECT COUNT(*) FROM saved WHERE uid=?",(m.from_user.id,)).fetchone()[0]
    await m.answer(f"📊 Saved: {count}")

# ================= WEB (RENDER SAFE) =================
async def handle(r):
    return web.Response(text="OK")

async def web_app():
    app=web.Application()
    app.router.add_get("/",handle)

    runner=web.AppRunner(app)
    await runner.setup()

    site=web.TCPSite(runner,"0.0.0.0",int(os.getenv("PORT",10000)))
    await site.start()

async def on_startup(dp):
    asyncio.create_task(web_app())

# ================= RUN =================
if __name__=="__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)