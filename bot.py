import os
import logging
from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.webhook import get_new_configured_app

# ================= SETUP =================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN not found")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# ================= SIMPLE FACT =================
FACT = "Suv 100°C da qaynaydi / Water boils at 100°C"

# ================= HANDLERS =================
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("🚀 Webhook bot ishlayapti!\n\n" + FACT)

# ================= WEB APP =================
async def health(request):
    return web.Response(text="OK")

# ================= WEBHOOK SETUP =================
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

app = get_new_configured_app(
    dispatcher=dp,
    path=WEBHOOK_PATH,
    on_startup=on_startup,
    on_shutdown=on_shutdown
)

app.router.add_get("/", health)

# ================= RUN =================
if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))