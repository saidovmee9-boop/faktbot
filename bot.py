import os
import sqlite3
import asyncio
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
import hashlib


scheduler = AsyncIOScheduler(
    timezone=timezone("Asia/Tashkent"),
    job_defaults={"coalesce": True, "max_instances": 1}
)


TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
def db():
    return sqlite3.connect("bot.db")

def init_db():
    with db() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS saved (
            uid INTEGER,
            text TEXT,
            UNIQUE(uid, text)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            uid INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
        """)
        # NEW
        c.execute("""
        CREATE TABLE IF NOT EXISTS user_seen (
            uid INTEGER,
            fact TEXT,
            UNIQUE(uid, fact)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS group_seen (
            gid INTEGER,
            fact TEXT,
            UNIQUE(gid, fact)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            gid INTEGER PRIMARY KEY
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS global_seen (
            fact TEXT PRIMARY KEY
        )
        """)

init_db()

# ================= FACTS =================
FACTS = {
    "science": [
("Asalarilar odam yuzini taniydi","Пчёлы узнают лица","Bees recognize human faces"),
("Sakkizoyoqda 3 ta yurak bor","У осьминога 3 сердца","Octopus has 3 hearts"),
("Kosmosda ovoz tarqalmaydi","В космосе нет звука","Sound does not travel in space"),
("Odam tanasida 37 trillion hujayra bor","В теле 37 триллионов клеток","Human body has 37 trillion cells"),
("Ko‘z miyadan tez ishlaydi","Глаза быстрее мозга","Eyes process faster than brain"),
("Miya 20% energiya ishlatadi","Мозг использует 20% энергии","Brain uses 20% energy"),
("Suv uch holatda mavjud","Вода имеет 3 состояния","Water has 3 states"),
("Ahtapotning qoni ko‘k rangda","У осьминога синяя кровь","Octopus has blue blood"),
("Inson tanasidagi bakteriyalar hujayralardan ko‘p","В теле больше бактерий чем клеток","There are more bacteria than cells in the body"),
("Kosmosda suyuqlik shar shaklida bo‘ladi","В космосе жидкость принимает форму шара","Liquids form spheres in space"),
("Shimpanze DNKsi odamnikiga 98% o‘xshaydi","ДНК шимпанзе совпадает на 98%","Chimp DNA is 98% similar to humans"),
("Qora tuynuk vaqtni sekinlashtiradi","Чёрная дыра замедляет время","Black holes slow down time"),


("Qon kislorod tashiydi","Кровь переносит кислород","Blood carries oxygen"),
("Quyosh gazdan iborat","Солнце состоит из газа","Sun is made of gas"),
("Hujayra hayot asosi","Клетка основа жизни","Cell is basis of life"),
("Nerv tizimi tez ishlaydi","Нервная система быстрая","Nervous system is fast"),
("DNA axborot saqlaydi","ДНК хранит информацию","DNA stores information"),
("Atom juda kichik","Атом очень маленький","Atom is very small"),


("Elektr tok oqimi","Электричество течёт","Electricity flows"),
("Tuproq o‘simlik uchun zarur","Почва важна","Soil is important"),
("Fan rivojlanadi","Наука развивается","Science evolves"),
("Tajriba muhim","Эксперимент важен","Experiment is important"),
("Bilim kuch","Знание сила","Knowledge is power"),
("Tajriba o‘rgatadi","Опыт учит","Experience teaches"),
("Fan kelajak","Наука будущее","Science is future"),
    ],
    "tech": [
        ("Birinchi kompyuter 27 tonna vaznga ega edi","Первый компьютер весил 27 тонн","The first computer weighed 27 tons"),
("Internet dastlab harbiy loyiha sifatida yaratilgan","Интернет был военным проектом","The internet started as a military project"),
("Dastlabki sichqoncha yog‘ochdan yasalgan","Первая мышь была деревянной","The first computer mouse was made of wood"),
("Bir Google qidiruvi oddiy lampochkadan ko‘proq energiya sarflaydi","Один поиск Google потребляет энергию лампочки","A Google search uses energy like a light bulb"),
("YouTube’da har daqiqada 500+ soat video yuklanadi","На YouTube загружается 500 часов видео в минуту","500+ hours of video are uploaded to YouTube every minute"),
("Internetdagi ma’lumotlarning katta qismi “deep web”da","Большая часть интернета — deep web","Most internet data is in the deep web"),
("Bir virus butun tarmoqni ishdan chiqarishi mumkin","Один вирус может остановить сеть","A virus can shut down entire networks"),
("Dunyodagi ilk domen “symbolics.com” edi","Первый домен — symbolics.com","The first domain was symbolics.com"),
("Kompyuter xotirasi sekundiga milliardlab amal bajaradi","Компьютер выполняет миллиарды операций","Computers perform billions of operations per second"),
("NASA kompyuterlari oddiy telefonlardan kuchsizroq bo‘lgan","Компьютеры NASA слабее телефона","Old NASA computers were weaker than phones"),


("AI inson yuzini soniyalarda taniydi","ИИ распознаёт лицо мгновенно","AI recognizes faces instantly"),
("Facebook foydalanuvchilari milliardlab","Пользователей Facebook миллиарды","Facebook has billions of users"),
("Bitcoin tarmog‘i butun davlatdan ko‘p energiya ishlatadi","Bitcoin потребляет энергию страны","Bitcoin uses energy like a country"),
("Internet o‘chsa global iqtisod zarar ko‘radi","Интернет влияет на экономику","Internet affects global economy"),
("Dasturchilar kod bilan dunyoni boshqaradi","Код управляет миром","Code runs the world"),
("GPS sun’iy yo‘ldoshlar orqali ishlaydi","GPS работает через спутники","GPS uses satellites"),


("Robotlar operatsiya qiladi","Роботы делают операции","Robots perform surgeries"),
("3D printer uy qurishi mumkin","3D принтер строит дом","3D printers can build houses"),
("Drone orqali yuk yetkaziladi","Дроны доставляют товары","Drones deliver packages"),
("Avtopilot mashina o‘zi yuradi","Автопилот ведёт машину","Self-driving cars exist"),
("Bulut texnologiyasi ma’lumot saqlaydi","Облако хранит данные","Cloud stores data"),
("Internet kabeli okean ostidan o‘tadi","Кабели идут под океаном","Internet cables run under oceans"),
("Kiberhujum davlatga zarar yetkazadi","Кибератака разрушает системы","Cyberattacks damage nations"),
("Parol buzish soniyalar ichida bo‘lishi mumkin","Пароль взламывается быстро","Passwords can be cracked quickly"),
("Ma’lumot eng qimmat resurs","Данные — новый ресурс","Data is the new oil"),

("Google har soniyada minglab qidiruvni qayta ishlaydi","Google обрабатывает тысячи запросов","Google handles thousands of searches per second"),
("Kompyuterlar 0 va 1 bilan ishlaydi","Компьютеры работают на 0 и 1","Computers use binary"),
("Kod xato bo‘lsa tizim yiqiladi","Ошибка ломает систему","A bug can crash systems"),
("Dastur millionlab satrdan iborat bo‘lishi mumkin","Код состоит из миллионов строк","Software can have millions of lines"),
("Sun’iy intellekt o‘rganadi","ИИ учится","AI learns from data"),
("Internet tezligi yorug‘likka yaqin","Интернет почти как свет","Internet speed approaches light"),
("Serverlar issiq chiqargani uchun sovutiladi","Серверы охлаждаются","Servers need cooling"),
("Hacker tizimga yashirin kiradi","Хакер проникает в систему","Hackers infiltrate systems"),
("Kriptografiya ma’lumotni himoya qiladi","Криптография защищает","Cryptography protects data"),
("Blockchain o‘zgarmas yozuv beradi","Блокчейн неизменяем","Blockchain is immutable"),

("VR real hayotga o‘xshash tajriba beradi","VR создаёт реальность","VR creates immersive worlds"),
("AR real dunyoni boyitadi","AR дополняет реальность","AR enhances reality"),
("Chatbotlar odam bilan gaplashadi","Чатботы общаются","Chatbots talk like humans"),
("Sun’iy ovoz insonnikiga o‘xshaydi","ИИ голос похож на человека","AI voices sound human"),
("Robotlar zavodda ishlaydi","Роботы работают на заводах","Robots work in factories"),
("Texnologiya tez rivojlanmoqda","Технологии быстро растут","Technology grows fast"),
("Kompyuterlar tez hisoblaydi","Компьютеры считают быстро","Computers calculate fast"),
("Dasturiy ta’minot muhim","Софт важен","Software is crucial"),

("Sun’iy yo‘ldoshlar Yer atrofida aylanadi","Спутники вращаются","Satellites orbit Earth"),
("Internet millionlab serverdan iborat","Интернет из серверов","Internet has millions of servers"),
("Ma’lumotlar markazlarda saqlanadi","Данные в дата-центрах","Data stored in data centers"),
("Katta kompaniyalar ma’lumot yig‘adi","Компании собирают данные","Companies collect data"),
("AI kasallik aniqlaydi","ИИ выявляет болезни","AI detects diseases"),
("Robotlar odam o‘rnini bosadi","Роботы заменяют людей","Robots replace humans"),
("Texnologiya ishni osonlashtiradi","Технологии упрощают","Tech simplifies life"),
("Dasturchilar yuqori maosh oladi","Программисты получают много","Developers earn well"),
("Kod yozish muhim ko‘nikma","Кодирование важно","Coding is essential"),

    ],
    "history": [
        ("Qadimgi Rimda beton suv ostida ham qotgan","Римский бетон твердел под водой","Roman concrete could set underwater"),
("Vikinglar Amerikaga Kolumbdan 500 yil oldin borgan","Викинги были в Америке раньше Колумба","Vikings reached America 500 years before Columbus"),
("Kleopatra piramidalardan ko‘ra iPhone’ga yaqinroq davrda yashagan","Клеопатра ближе к iPhone чем к пирамидам","Cleopatra is closer to iPhone than pyramids"),
("Giza piramidalari qurilganda hali junli mamontlar yashagan","Мамонты жили при пирамидах","Woolly mammoths lived when pyramids were built"),
("Qadimgi Misrda elektr batareyaga o‘xshash qurilmalar bo‘lgan bo‘lishi mumkin","В Египте могли быть батареи","Ancient Egypt may have had batteries"),
("Rimliklar betonni suv ostida qurish uchun ishlatgan","Римляне строили под водой","Romans used underwater concrete"),
("Qadimgi Rimda ba’zi shaharlar hozirgidan tozaroq bo‘lgan","Некоторые римские города чище современных","Some Roman cities were cleaner than modern ones"),
("Napoleon baland bo‘yli edi (afsona noto‘g‘ri)","Наполеон не был низким","Napoleon was not short"),
("O‘rta asrlar “qorong‘i davr” emas edi","Средневековье не тёмное","Middle Ages were not truly dark"),
("Vikinglar dubulg‘ada shox ishlatmagan","Викинги не носили рога","Vikings did not wear horned helmets"),

("Qadimgi Yunonistonda robotga o‘xshash mexanizmlar bo‘lgan","В Греции были механизмы","Ancient Greeks had proto-robots"),
("Antikythera mexanizmi birinchi kompyuter hisoblanadi","Антикитерский механизм — первый компьютер","Antikythera mechanism is first computer"),
("Qadimgi Xitoyda porox tasodifan kashf etilgan","Порох открыт случайно","Gunpowder was discovered accidentally"),
("Mayyalar astronomiyada juda aniq hisob-kitob qilgan","Майя точно считали астрономию","Maya had precise astronomy"),
("Inklar yozuvsiz imperiya boshqargan","Инки без письменности","Inca ruled without writing"),
("Qadimgi Rimda 1 kunlik suv tizimi zamonaviydan kuchli bo‘lgan","Римская вода лучше современной","Roman water system was advanced"),
("Qadimgi Misr shifokorlari operatsiya qilgan","Египет делал операции","Egyptians performed surgeries"),
("Yunonlar Yer dumaloq deb bilgan","Греки знали что Земля круглая","Greeks knew Earth is round"),
("O‘rta asrlarda ba’zi shaharlar kanalizatsiyaga ega edi","Были канализации в средние века","Some medieval cities had sewage"),
("Rim armiyasi 50 km/kuniga yurgan","Римская армия шла 50 км","Roman army marched 50 km/day"),

("Qadimgi Xitoyda qog‘oz pul ishlatilgan","В Китае были бумажные деньги","China used paper money"),
("Skiflar ot ustida tug‘ilgan kabi yashagan","Скифы жили на лошадях","Scythians lived on horses"),
("Spartaliklar bolalarni qattiq harbiy tarbiya qilgan","Спарта жесткое воспитание","Sparta had harsh training"),
("Qadimgi Hindistonda matematika juda rivojlangan","Индия развила математику","Ancient India advanced math"),
("0 soni Hindistonda kashf qilingan","Ноль из Индии","Zero was invented in India"),
("Arab olimlari tibbiyot asosini yaratgan","Арабы развили медицину","Arab scholars advanced medicine"),
("Qadimgi Rimda liftga o‘xshash qurilmalar bo‘lgan","В Риме были лифты","Romans had elevators"),
("Gladiatorlar hamma vaqt o‘lmagan","Гладиаторы не всегда умирали","Gladiators didn’t always die"),
("Qadimgi Misrda mushuk muqaddas bo‘lgan","Кошки священные в Египте","Cats were sacred in Egypt"),
("Fir’avnlar o‘z ismlarini yashirishgan","Фараоны скрывали имена","Pharaohs hid names"),

("Atlantida afsonasi qadimiy yunonlardan kelgan","Атлантида от греков","Atlantis from Greeks"),
("Ba’zi qadimgi shaharlar butunlay yo‘qolgan","Города исчезали полностью","Some cities vanished"),
("Pompey vulqon ostida qolgan","Помпеи под вулканом","Pompeii buried by volcano"),
("Rim imperiyasi 1000 yildan ortiq yashagan","Рим 1000 лет","Roman Empire lasted 1000+ years"),
("Mongollar tarixdagi eng katta imperiyani yaratgan","Монголы крупнейшая империя","Mongols had largest empire"),
("Chingizxon juda kuchli strateg bo‘lgan","Чингисхан стратег","Genghis Khan was a strategist"),
("Iskandar Zulqarnayn 30 yoshida imperiya boshqargan","Александр Великий в 30","Alexander ruled at 30"),
("Ba’zi qadimgi xaritalar Antarktidani bilgan","Древние знали Антарктиду","Ancient maps showed Antarctica"),
("O‘rta asrlarda ilm yo‘q emas edi","Наука была в средние века","Science existed in Middle Ages"),
("Qadimgi Rimda gazeta bo‘lgan","В Риме была газета","Romans had newspapers"),

("Vikinglar juda yaxshi dengizchi bo‘lgan","Викинги отличные моряки","Vikings were great sailors"),
("Qadimgi Xitoy devori bir nechta devordan iborat","Китайская стена сложная","Great Wall is multiple walls"),
("Ba’zi qadimgi urushlar yillar davom etgan","Войны длились годами","Wars lasted years"),
("Rim imperiyasi 3 qismga bo‘lingan","Рим разделился","Rome split into parts"),
("Qadimgi Gretsiyada Olimpiada boshlangan","Олимпиада из Греции","Olympics started in Greece"),
("Sparta va Afina urushgan","Спарта против Афин","Sparta vs Athens war"),
("Qadimgi Misrda tibbiyot kitoblari bo‘lgan","Египет имел медицину","Egypt had medical books"),
("Mayyalar 0 ni ishlatgan","Майя использовали ноль","Maya used zero"),
("Rimliklar yo‘l qurishda juda kuchli bo‘lgan","Рим строил дороги","Romans built roads"),
("Ba’zi Rim yo‘llari hozir ham ishlatiladi","Римские дороги живы","Some Roman roads still exist"),

("Qadimgi Hindistonda kosmos haqida yozilgan","Индия знала космос","India had astronomy texts"),
("Arablar algebra yaratgan","Арабы создали алгебру","Arabs invented algebra"),
("O‘rta asrlarda universitetlar bo‘lgan","Были университеты","Universities existed"),
("Qadimgi Xitoyda kompas bor edi","Китай имел компас","China had compass"),
("Rim armiyasi juda tartibli bo‘lgan","Римская армия дисциплина","Roman army was disciplined"),
("Vikinglar Amerikaga “Vinland” degan","Викинги назвали Винланд","Vikings called it Vinland"),
("Qadimgi Misrda tibbiy papiruslar bor edi","Египет папирусы","Egypt had medical papyri"),
("Tarixda yo‘qolgan tillar juda ko‘p","Исчезнувшие языки","Many lost languages exist"),
("Tarix ko‘p narsani yashiradi","История скрывает многое","History hides many things"),
    ]
}

# ================= AI =================
subjects = [
    ("Odam miyasi","Мозг человека","Human brain"),
    ("Koinot","Вселенная","Universe"),
    ("Sun’iy intellekt","Искусственный интеллект","Artificial intelligence"),
    ("Texnologiya","Технологии","Technology"),
    ("Yer sayyorasi","Планета Земля","Planet Earth"),
    ("Qora tuynuklar","Чёрные дыры","Black holes"),
    ("Vaqt","Время","Time"),
    ("Energiya","Энергия","Energy"),
    ("Elektr","Электричество","Electricity"),
    ("Atomlar","Атомы","Atoms"),
    ("Kimyo","Химия","Chemistry"),
    ("Fizika","Физика","Physics"),
    ("Biologiya","Биология","Biology"),
    ("Genetika","Генетика","Genetics"),
    ("DNK","ДНК","DNA"),
    ("Robotlar","Роботы","Robots"),
    ("Kosmos kemalari","Космические корабли","Spacecraft"),
    ("Sun’iy yo‘ldoshlar","Спутники","Satellites"),
    ("Internet","Интернет","Internet"),
    ("Kompyuterlar","Компьютеры","Computers"),
    ("Dasturlash","Программирование","Programming"),
    ("Ma’lumotlar","Данные","Data"),
    ("Okeanlar","Океаны","Oceans"),
    ("Iqlim","Климат","Climate"),
    ("Yer yadrosi","Ядро Земли","Earth core"),
    ("Yulduzlar","Звёзды","Stars"),
    ("Galaktikalar","Галактики","Galaxies"),
    ("Nur","Свет","Light"),
    ("Ovoz","Звук","Sound"),
    ("Inson tanasi","Человеческое тело","Human body"),
]
actions = [
    ("evolyutsiyada o‘zgaradi","изменяется в эволюции","changes in evolution"),
    ("tabiiy jarayonlarga bo‘ysunadi","подчиняется природным процессам","follows natural processes"),
    ("fizik qonunlar bilan boshqariladi","управляется физическими законами","governed by physical laws"),
    ("energiya bilan bog‘liq","связан с энергией","energy-related"),
    ("kimyoviy reaksiyada sodir bo‘ladi","происходит в химических реакциях","occurs in chemical reactions"),
    ("signallar orqali ishlaydi","работает через сигналы","works via signals"),
    ("molekulyar darajada ishlaydi","работает на молекулярном уровне","works at molecular level"),
    ("tizim sifatida ishlaydi","работает как система","works as a system"),
    ("vaqt o‘tishi bilan o‘zgaradi","изменяется со временем","changes over time"),
    ("interaksiya natijasida yuzaga keladi","возникает из взаимодействия","arises from interaction"),
]

extras = [
    ("hali to‘liq o‘rganilmagan","не до конца изучено","not fully understood"),
    ("tadqiqotlar davom etmoqda","исследования продолжаются","research ongoing"),
    ("mexanizmi noma’lum","механизм неизвестен","mechanism unknown"),
    ("gipoteza darajasida","на уровне гипотезы","at hypothesis level"),
    ("eksperimental tasdiq kerak","требует проверки","needs verification"),
    ("ko‘p omilga bog‘liq","зависит от факторов","depends on factors"),
    ("murakkab tizim","сложная система","complex system"),
    ("global ahamiyatga ega","глобально важно","globally important"),
    ("ilmiy o‘rganilmoqda","изучается наукой","being studied"),
    ("amaliy qo‘llanadi","имеет применение","has applications"),
]

def generate_ai_fact():
    s = random.choice(subjects)
    a = random.choice(actions)
    e = random.choice(extras)
    return (
        f"{s[0]} {a[0]} {e[0]}",
        f"{s[1]} {a[1]} {e[1]}",
        f"{s[2]} {a[2]} {e[2]}"
    )

# ================= UNIQUE =================
def get_unique_fact_user(uid, cat):
    facts = FACTS[cat]
    random.shuffle(facts)

    with db() as c:
        for fact in facts:
            exists = c.execute(
                "SELECT 1 FROM user_seen WHERE uid=? AND fact=?",
                (uid, fact[0])
            ).fetchone()

            if not exists:
                c.execute(
                    "INSERT OR IGNORE INTO user_seen VALUES (?,?)",
                    (uid, fact[0])
                )
                return fact

    # agar hammasi tugasa random qaytaradi
    return random.choice(facts)

def get_unique_facts_group(gid, count=10):
    with db() as c:
        seen = set(r[0] for r in c.execute(
            "SELECT fact FROM group_seen WHERE gid=?",
            (gid,)
        ))

    all_facts = []
    for cat in FACTS.values():
        all_facts.extend(cat)

    random.shuffle(all_facts)

    result = []

    for fact in all_facts:
        if fact[0] not in seen:
            result.append(fact)

            with db() as c:
                c.execute(
                    "INSERT OR IGNORE INTO group_seen VALUES (?,?)",
                    (gid, fact[0])
                )

            if len(result) >= count:
                return result

    # agar fakt tugasa AI generatsiya
    while len(result) < count:
        result.append(generate_ai_fact())

    return result
# ================= MENU =================
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔬 Science","💻 Tech")
    kb.add("📜 History")
    kb.add("❤️ Saved","📊 Stats")
    return kb

# ================= STATE =================
state = {}

# ================= SHOW =================
async def show(uid, chat_id, new_fact=None, edit=False):
    st = state[uid]
    cat = st["cat"]

    if new_fact is None:
        new_fact = get_unique_fact_user(uid, cat)

    if st["current"] and new_fact != st["current"]:
        st["back"].append(st["current"])

    st["current"] = new_fact
    st["forward"].clear()

    text = f"🇺🇿 {new_fact[0]}\n🇷🇺 {new_fact[1]}\n🇬🇧 {new_fact[2]}"

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Prev", callback_data="prev"),
        InlineKeyboardButton("Next ➡️", callback_data="next")
    )
    kb.add(InlineKeyboardButton("❤️ Save", callback_data="save"))

    if edit and st.get("msg_id"):
        await bot.edit_message_text(text, chat_id, st["msg_id"], reply_markup=kb)
        return

    msg = await bot.send_message(chat_id, text, reply_markup=kb)
    st["msg_id"] = msg.message_id

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    if m.chat.type in ["group", "supergroup"]:
        with db() as c:
            c.execute(
                "INSERT OR IGNORE INTO groups VALUES (?)",
                (m.chat.id,)
            )

    await m.answer("🚀 Ultimate Fact Bot ishga tushdi")



# IGNORE GROUP 👇
@dp.message_handler(lambda m: m.chat.type != "private")
async def ignore_group(m: types.Message):
    return



# ================= CATEGORY =================
@dp.message_handler(lambda m: m.text in ["🔬 Science","💻 Tech","📜 History"] and m.chat.type == "private")
async def cat_handler(m):
    uid = m.from_user.id

    if "Science" in m.text:
        cat = "science"
    elif "Tech" in m.text:
        cat = "tech"
    else:
        cat = "history"

    state[uid] = {
    "cat": cat,
    "msg_id": None,
    "current": None,
    "back": [],
    "forward": []
}

    await show(uid, m.chat.id)



@dp.message_handler(lambda m: m.text == "❤️ Saved" and m.chat.type == "private")
async def saved(m: types.Message):
    with db() as c:
        rows = c.execute(
            "SELECT text FROM saved WHERE uid=? ORDER BY rowid DESC LIMIT 20",
            (m.from_user.id,)
        ).fetchall()

    if not rows:
        return await m.answer("Hech narsa saqlanmagan")

    text = "❤️ Saved facts:\n\n" + "\n\n".join(r[0] for r in rows)

    await m.answer(text)



@dp.message_handler(lambda m: m.text == "📊 Stats" and m.chat.type == "private")
async def stats(m: types.Message):
    uid = m.from_user.id

    with db() as c:
        saved_count = c.execute(
            "SELECT COUNT(*) FROM saved WHERE uid=?",
            (uid,)
        ).fetchone()[0]

        seen_count = c.execute(
            "SELECT COUNT(*) FROM user_seen WHERE uid=?",
            (uid,)
        ).fetchone()[0]

    await m.answer(
        f"📊 Statistika:\n\n"
        f"❤️ Saved faktlar: {saved_count}\n"
        f"👁 Ko‘rilgan faktlar: {seen_count}"
    )


# ================= NAV =================
@dp.callback_query_handler(lambda c: c.data in ["next","prev"] and c.message.chat.type == "private")
async def nav(c):
    uid = c.from_user.id
    st = state.get(uid)

    if not st:
        return await c.answer()

     # ================= NEXT =================
    if c.data == "next":
        if st["forward"]:
            fact = st["forward"].pop()
            st["back"].append(st["current"])
        else:
            fact = get_unique_fact_user(uid, st["cat"])
            if st["current"]:
                st["back"].append(st["current"])

        st["current"] = fact

        text = f"🇺🇿 {fact[0]}\n🇷🇺 {fact[1]}\n🇬🇧 {fact[2]}"

        await bot.edit_message_text(
            text,
            c.message.chat.id,
            st["msg_id"],
            reply_markup=c.message.reply_markup
        )

    # ================= PREV =================
    elif c.data == "prev":
        if not st["back"]:
            return await c.answer("Oldinga yo‘q")

        fact = st["back"].pop()
        st["forward"].append(st["current"])
        st["current"] = fact

        text = f"🇺🇿 {fact[0]}\n🇷🇺 {fact[1]}\n🇬🇧 {fact[2]}"

        await bot.edit_message_text(
            text,
            c.message.chat.id,
            st["msg_id"],
            reply_markup=c.message.reply_markup
        )

    await c.answer()

# ================= SAVE =================
@dp.callback_query_handler(lambda c: c.data == "save" and c.message.chat.type == "private")
async def save(c):
    try:
        with db() as conn:
            conn.execute("INSERT OR IGNORE INTO saved VALUES (?,?)",
                         (c.from_user.id, c.message.text))

            conn.execute("""
                INSERT INTO stats(uid, count)
                VALUES(?, 1)
                ON CONFLICT(uid) DO UPDATE SET count = count + 1
            """, (c.from_user.id,))

        await c.answer("❤️ Saved")
    except:
        await c.answer("❗ Error")


# ================= GROUP ADD =================
@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def any_msg(m: types.Message):
    if m.chat.type in ["group", "supergroup"]:
        with db() as c:
            c.execute(
                "INSERT OR IGNORE INTO groups VALUES (?)",
                (m.chat.id,)
            )

# ================= DAILY =================
async def send_daily():
    print("SEND DAILY CALLED")  # test uchun

    with db() as c:
        groups = c.execute("SELECT gid FROM groups").fetchall()

    for g in groups:
        gid = g[0]

        facts = get_unique_facts_group(gid, 10)

        for f in facts:
            try:
                await bot.send_message(
                    gid,
                    f"🇺🇿 {f[0]}\n🇷🇺 {f[1]}\n🇬🇧 {f[2]}"
                )
                await asyncio.sleep(0.5)
            except Exception as e:
                print("ERROR:", e)
# ================= WEB =================
async def handle(r):
    return web.Response(text="OK")

async def web_app():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()

async def on_startup(dp):
    # 1) boshqa bot instance’larni to‘xtatadi
    await bot.delete_webhook(drop_pending_updates=True)

    # 2) scheduler faqat 1 marta
    global scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)

    scheduler = AsyncIOScheduler(
        timezone=timezone("Asia/Tashkent"),
        job_defaults={"coalesce": True, "max_instances": 1}
    )

    scheduler.add_job(
    send_daily,
    "cron",
    hour=8,
    minute=0,
    id="daily_facts",
    replace_existing=True
)

    scheduler.start()

    # 3) web server
    asyncio.create_task(web_app())
    
# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup
    )