#!/usr/bin/env python3
import asyncio
import logging
import os
import ast
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()

from database import init_db
from handlers import register_handlers
from admin_panel import register_admin_handlers
from keyboards import set_main_menu
from scheduler import start_scheduler
from settings import BOT_VERSION, LOGS_DIR, HEALTHCHECK_PORT

# Создаём папку для логов, если её нет
os.makedirs(LOGS_DIR, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'bot.log')),
        logging.StreamHandler()
    ]
)

# Загружаем переменные из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = ast.literal_eval(os.getenv("ADMIN_IDS", "[]"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

# Хранилище для FSM
storage = MemoryStorage()

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)


async def on_startup():
    """Функция, выполняемая при запуске бота."""
    # Инициализация базы данных
    init_db()
    
    # Установка команд бота (только /start)
    await set_main_menu(bot)
    
    # Регистрация обработчиков (пользовательские хендлеры)
    register_handlers(dp, bot, ADMIN_IDS, BOT_VERSION)
    
    # Регистрация хендлеров админ-панели
    register_admin_handlers(dp, bot, ADMIN_IDS)
    
    # Запуск планировщика задач (включая push-уведомления и групповую рассылку)
    start_scheduler(bot, ADMIN_IDS[0] if ADMIN_IDS else None, BOT_VERSION)
    
    logging.info(f"Бот Аркадий Викторович запущен, версия {BOT_VERSION}")
    
    # Запуск healthcheck-сервера (для мониторинга)
    asyncio.create_task(run_healthcheck())


async def run_healthcheck():
    """Запускает простой HTTP-сервер для проверки работоспособности бота."""
    from aiohttp import web
    app = web.Application()
    
    async def healthcheck(request):
        return web.json_response({"status": "ok", "version": BOT_VERSION})
    
    app.router.add_get('/', healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', HEALTHCHECK_PORT)
    await site.start()
    logging.info(f"Healthcheck сервер запущен на порту {HEALTHCHECK_PORT}")


async def main():
    """Главная функция запуска бота."""
    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())