import os
import sqlite3
import random
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =====================
# TOKEN
# =====================
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =====================
# DB
# =====================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        c = conn.cursor()

        c.execute("CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_id INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY)")
        c.execute("CREATE TABLE IF NOT EXISTS premium (user_id INTEGER)")

init_db()

# =====================
# FACTS (10 ta har category + 3 til FULL SYNC)
# =====================
FACTS = {
    "science": [
        (1,"Inson DNKsi 60% banan bilan o‘xshash","ДНК человека на 60% как банан","Human DNA is 60% similar to banana"),
        (2,"Miya uxlaganda ham ishlaydi","Мозг работает во сне","Brain works during sleep"),
        (3,"Suv kosmosda muzlaydi","Вода в космосе замерзает","Water freezes in space"),
        (4,"Yurak 24/7 ishlaydi","Сердце работает 24/7","Heart works 24/7"),
        (5,"Bakteriyalar tanamizda yashaydi","Бактерии живут в теле","Bacteria live in body"),
        (6,"Yulduzlar milliard yildir mavjud","Звёзды существуют миллиарды лет","Stars exist billions of years"),
        (7,"Yer aylanishda davom etadi","Земля постоянно вращается","Earth keeps rotating"),
        (8,"Odam miyasi superkompyuter","Мозг как суперкомпьютер","Brain is like supercomputer"),
        (9,"Odam 70% suv","Человек на 70% вода","Human is 70% water"),
        (10,"Quyosh juda issiq","Солнце очень горячее","Sun is very hot")
    ],
    "tech": [
        (11,"Internet harbiy loyiha edi","Интернет был военным проектом","Internet was military project"),
        (12,"AI tez rivojlanmoqda","AI быстро развивается","AI is growing fast"),
        (13,"Telefonlar kichik kompyuter","Телефон это мини ПК","Phone is mini PC"),
        (14,"Kod dunyoni boshqaradi","Код управляет миром","Code runs world"),
        (15,"Serverlar 24/7 ishlaydi","Серверы работают 24/7","Servers run 24/7"),
        (16,"Cloud data saqlaydi","Облако хранит данные","Cloud stores data"),
        (17,"Robotlar ishlab chiqmoqda","Роботы развиваются","Robots evolving"),
        (18,"Internet global tarmoq","Интернет глобальная сеть","Internet is global network"),
        (19,"Apps millionlab bor","Приложений миллионы","Millions of apps"),
        (20,"Cyber security muhim","Кибербезопасность важна","Cybersecurity is important")
    ],
    "history": [
        (21,"Rim imperiyasi kuchli edi","Рим был сильной империей","Rome was powerful"),
        (22,"Kleopatra qadimiy malikasi","Клеопатра древняя королева","Cleopatra was queen"),
        (23,"Vikinglar jangchi edi","Викинги были воинами","Vikings were warriors"),
        (24,"Piramidalar sirli","Пирамиды загадочные","Pyramids are mysterious"),
        (25,"Tarix juda boy","История богата","History is rich"),
        (26,"Imperiyalar qulagan","Империи падали","Empires fell"),
        (27,"Urushlar ko‘p bo‘lgan","Было много войн","Many wars happened"),
        (28,"Qadimiy shaharlar","Древние города","Ancient cities"),
        (29,"O‘tmish qiziq","Прошлое интересно","Past is interesting"),
        (30,"Qirollar davri","Эпоха королей","Age of kings")
    ]
}

# =====================
# STATE
# =====================
state = {}
user_lang = {}

# =====================
# LANG
# =====================
def t(i, lang):
    return FACTS[i[0]][0][1] if lang=="uz" else FACTS[i[0]][0][2] if lang=="ru" else FACTS[i[0]][0][3]

# =====================
# MENU
# =====================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech","📜 History")
    kb.add("❤️ Saved","🌐 Language")
    return kb

# =====================
# SHOW FACT
# =====================
async def show(uid, chat_id):
    st = state[uid]
    cat = st["cat"]
    idx = st["i"]

    fact = FACTS[cat][idx]
    lang = user_lang.get(uid,"uz")

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data=f"save_{fact[0]}"))

    await bot.send_message(chat_id, fact[1], reply_markup=kb)

# =====================
# START
# =====================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    user_lang[m.from_user.id] = "uz"
    await m.answer("🚀 Fact Bot", reply_markup=menu())

# =====================
# CATEGORY
# =====================
@dp.message_handler()
async def h(m):
    uid = m.from_user.id
    t = m.text

    if "Science" in t:
        cat="science"
    elif "Tech" in t:
        cat="tech"
    elif "History" in t:
        cat="history"
    else:
        return

    state[uid] = {"cat":cat,"i":0}
    await show(uid,m.chat.id)

# =====================
# NAV FIX
# =====================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"])
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)
    if not st: return

    if c.data=="next":
        st["i"]=(st["i"]+1)%10
    else:
        st["i"]=(st["i"]-1)%10

    await show(uid,c.message.chat.id)

# =====================
# SAVE FIX (FULL LIST FIXED)
# =====================
@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = int(c.data.split("_")[1])

    with db() as conn:
        conn.execute("INSERT INTO saved VALUES (?,?)",(c.from_user.id,fid))

    await c.answer("❤️ Saved")

# =====================
# SAVED FIX (ALL FACTS SHOW)
# =====================
@dp.message_handler(lambda m:"Saved" in m.text or "❤️" in m.text)
async def saved(m):
    uid=m.from_user.id

    with db() as conn:
        rows=conn.execute("SELECT fact_id FROM saved WHERE user_id=?",(uid,)).fetchall()

    if not rows:
        return await m.answer("Empty")

    txt="❤️ SAVED FACTS:\n\n"

    for r in rows:
        fid=r[0]
        for cat in FACTS:
            for f in FACTS[cat]:
                if f[0]==fid:
                    txt+=f"• {f[1]}\n"

    await m.answer(txt)

# =====================
# AI FACT GENERATOR (FAKE SMART)
# =====================
def ai_fact():
    return "🤖 AI Fact: Koinot har sekund kengaymoqda va yangi galaktikalar paydo bo‘lmoqda."

# =====================
# WEB SERVER
# =====================
async def webh(r):
    return web.Response(text="OK")

async def web():
    app=web.Application()
    app.router.add_get("/",webh)
    runner=web.AppRunner(app)
    await runner.setup()
    site=web.TCPSite(runner,"0.0.0.0",10000)
    await site.start()

async def on_startup(dp):
    asyncio.create_task(web())

if __name__=="__main__":
    executor.start_polling(dp,skip_updates=True,on_startup=on_startup)