#!/usr/bin/env python3
import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode

load_dotenv()

from database import init_db
from handlers import register_handlers
from admin_panel import register_admin_handlers
from keyboards import set_main_menu
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = eval(os.getenv("ADMIN_IDS", "[]"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

async def on_startup():
    init_db()
    await set_main_menu(bot)
    register_handlers(dp, bot, ADMIN_IDS)
    register_admin_handlers(dp, bot, ADMIN_IDS)
    start_scheduler(bot)   # запуск ежедневной рассылки карты дня
    logging.info("Бот Аркадий Викторович запущен")

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())