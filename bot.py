import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from handlers import register_handlers
from keyboards import set_main_menu
from scheduler import start_scheduler
from utils import setup_logging

load_dotenv()
setup_logging()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = eval(os.getenv("ADMIN_IDS", "[]"))
BOT_VERSION = "5.0"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

async def main():
    await set_main_menu(bot)
    register_handlers(dp, bot, ADMIN_IDS, BOT_VERSION)
    start_scheduler(bot, ADMIN_IDS)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())