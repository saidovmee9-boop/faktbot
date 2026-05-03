import os
import sqlite3
import random
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ===================== DB =====================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS saved (user_id INTEGER, fact_id INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS stats (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)")
init_db()

# ===================== FACTS (10 TA HAR BO‘LIM) =====================
FACTS = {
    "science": [
        (1,"Inson DNKsi bananga o‘xshash","ДНК похож на банан","DNA is similar to banana"),
        (2,"Miya uxlaganda ham ishlaydi","Мозг работает во сне","Brain works during sleep"),
        (3,"Suv kosmosda muzlaydi","Вода в космосе замерзает","Water freezes in space"),
        (4,"Yurak 24/7 uradi","Сердце работает 24/7","Heart works 24/7"),
        (5,"Odam 70% suv","Человек 70% вода","Human is 70% water"),
        (6,"Quyosh juda issiq","Солнце очень горячее","Sun is very hot"),
        (7,"Bakteriyalar tanada bor","Бактерии в теле","Bacteria in body"),
        (8,"Yer aylanadi","Земля вращается","Earth rotates"),
        (9,"Miya super kuchli","Мозг мощный","Brain is powerful"),
        (10,"Koinot kengaymoqda","Вселенная расширяется","Universe expands")
    ],
    "tech": [
        (11,"Internet harbiy loyiha","Интернет военный проект","Internet was military"),
        (12,"AI tez rivojlanadi","AI развивается","AI is evolving"),
        (13,"Telefon mini kompyuter","Телефон мини ПК","Phone is mini PC"),
        (14,"Kod dunyoni boshqaradi","Код управляет миром","Code runs world"),
        (15,"Cloud tizimlar","Облачные системы","Cloud systems"),
        (16,"Server 24/7 ishlaydi","Сервер 24/7","Server runs 24/7"),
        (17,"Robotlar rivojlanadi","Роботы развиваются","Robots evolve"),
        (18,"Apps millionlab","Приложений миллионы","Millions of apps"),
        (19,"Cyber xavfsizlik muhim","Кибербезопасность важна","Cybersecurity matters"),
        (20,"Data juda qimmat","Данные дорогие","Data is valuable")
    ],
    "history": [
        (21,"Rim imperiyasi kuchli","Рим сильный","Rome was powerful"),
        (22,"Kleopatra malikasi","Клеопатра","Cleopatra queen"),
        (23,"Vikinglar jangchi","Викинги воины","Vikings warriors"),
        (24,"Piramidalar sirli","Пирамиды тайна","Pyramids mystery"),
        (25,"Tarix boy","История богатая","History rich"),
        (26,"Urushlar bo‘lgan","Войны были","Wars happened"),
        (27,"Qirollar davri","Эпоха королей","Age of kings"),
        (28,"Imperiyalar qulagan","Империи пали","Empires fell"),
        (29,"Qadimiy shaharlar","Древние города","Ancient cities"),
        (30,"O‘tmish qiziq","Прошлое интересно","Past is interesting")
    ],
    "ai": [
        (31,"AI insondan tez fikrlaydi","ИИ быстрее человека","AI thinks faster than humans"),
        (32,"AI millionlab data o‘rganadi","ИИ учится на данных","AI learns from data"),
        (33,"AI kelajak texnologiya","ИИ будущее","AI is future tech"),
        (34,"AI yozadi va o‘qiydi","ИИ пишет и читает","AI writes and reads"),
        (35,"AI xatolarni topadi","ИИ находит ошибки","AI finds errors"),
        (36,"AI tibbiyotda ishlatiladi","ИИ в медицине","AI used in medicine"),
        (37,"AI avtomobil boshqaradi","ИИ управляет авто","AI drives cars"),
        (38,"AI tarjima qiladi","ИИ переводит","AI translates"),
        (39,"AI chatbotlar asosida","ИИ чатботы","AI chatbots"),
        (40,"AI o‘rganadi doim","ИИ всегда учится","AI always learns")
    ]
}

# ===================== STATE =====================
state = {}
lang = {}

def tr(row, l):
    if l == "uz": return row[1]
    if l == "ru": return row[2]
    return row[3]

# ===================== MENU =====================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech")
    kb.add("📜 History","🤖 AI Facts")
    kb.add("❤️ Saved","📊 Stats")
    return kb

# ===================== SHOW =====================
async def show(uid, chat_id):
    st = state[uid]
    cat = st["cat"]
    i = st["i"]

    fact = FACTS[cat][i]
    l = lang.get(uid,"uz")

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data=f"save_{fact[0]}"))

    await bot.send_message(chat_id, tr(fact,l), reply_markup=kb)

# ===================== START =====================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    lang[m.from_user.id] = "uz"
    await m.answer("🚀 Fact Bot Ready", reply_markup=menu())

# ===================== CATEGORY =====================
@dp.message_handler()
async def h(m):
    uid = m.from_user.id
    t = m.text

    if "Science" in t: cat="science"
    elif "Tech" in t: cat="tech"
    elif "History" in t: cat="history"
    elif "AI" in t: cat="ai"
    elif "Saved" in t: return await saved(m)
    elif "Stats" in t: return await stats(m)
    else: return

    state[uid] = {"cat":cat,"i":0}
    await show(uid,m.chat.id)

# ===================== NAV =====================
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

# ===================== SAVE FIX =====================
@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save(c):
    fid = int(c.data.split("_")[1])

    with db() as conn:
        conn.execute("INSERT INTO saved VALUES (?,?)",(c.from_user.id,fid))

    await c.answer("❤️ Saved")

# ===================== SAVED FULL FIX =====================
@dp.message_handler(lambda m:"Saved" in m.text)
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

# ===================== STATS =====================
@dp.message_handler(lambda m:"Stats" in m.text)
async def stats(m):
    uid=m.from_user.id
    with db() as conn:
        c=conn.execute("SELECT COUNT(*) FROM saved WHERE user_id=?",(uid,)).fetchone()[0]
    await m.answer(f"📊 Saved: {c}")

# ===================== WEB (RENDER SAFE) =====================
async def handle(r):
    return web.Response(text="OK")

async def web():
    app=web.Application()
    app.router.add_get("/",handle)
    runner=web.AppRunner(app)
    await runner.setup()
    site=web.TCPSite(runner,"0.0.0.0",int(os.getenv("PORT",10000)))
    await site.start()

async def on_startup(dp):
    asyncio.create_task(web())

# ===================== RUN =====================
if __name__=="__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)