from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
import datetime
import asyncio
import logging
import pytz
import random
from utils import (
    backup_database, add_subscription_days, get_challenge_progress,
    get_zodiac_sign, get_cached_response, save_cached_response,
    format_subscription_remaining, check_and_expire_subscriptions,
    generate_group_message, generate_night_message, generate_morning_message
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu

scheduler = AsyncIOScheduler()

# ---------- СУЩЕСТВУЮЩИЕ ЗАДАЧИ (карта дня, лидерборд, бэкап, челлендж, гороскопы, мотивация, напоминания) ----------
# ... (они уже есть, я их не копирую, чтобы не дублировать. Они остаются без изменений)

# ---------- НОВАЯ ЗАДАЧА ДЛЯ ГРУПП ----------
async def send_group_messages(bot: Bot):
    """Отправляет контент в группы согласно настройкам (каждые 30 минут, ночной режим)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, frequency FROM group_chats WHERE is_active=1")
    groups = cursor.fetchall()
    conn.close()

    now = datetime.datetime.now()
    hour = now.hour

    # Ночной режим: с 23:00 до 08:00 – не отправляем, кроме прощального/утреннего
    if 23 <= hour or hour < 8:
        # Проверяем, нужно ли отправить прощальное (в 22:55) или утреннее (в 08:05)
        # Прощальное отправляем в 22:55
        if hour == 22 and now.minute == 55:
            for chat_id, _ in groups:
                msg = generate_night_message()
                await bot.send_message(chat_id, msg, parse_mode="Markdown")
        # Утреннее в 08:05
        elif hour == 8 and now.minute == 5:
            for chat_id, _ in groups:
                msg = generate_morning_message()
                await bot.send_message(chat_id, msg, parse_mode="Markdown")
        return  # в остальное ночное время – ничего не отправляем

    # Дневное время: отправляем сообщения каждые 30 минут
    # Определяем, нужно ли отправить длинное сообщение (раз в 2 часа)
    is_long = (now.minute % 120 == 0)  # каждые 2 часа

    for chat_id, frequency in groups:
        # Проверяем, сколько сообщений уже отправлено сегодня
        today = datetime.date.today().isoformat()
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM group_sent_log WHERE chat_id=? AND sent_at LIKE ?", (chat_id, f"{today}%"))
        sent_count = cursor2.fetchone()[0]
        conn2.close()

        # Если достигли лимита (frequency * 2 сообщения в час * 24 часа – но ограничим по количеству)
        # frequency – сообщений в час, значит за день максимум frequency * 24
        # Но мы отправляем каждые 30 минут, значит за час 2 сообщения.
        # Если frequency = 2, то в час 2 сообщения, за день до 48.
        # Можно упростить: если sent_count >= frequency * 24, то сегодня больше не отправляем.
        if sent_count >= frequency * 24:
            continue

        # Генерируем сообщение
        msg = await generate_group_message(chat_id, is_long=is_long)
        if msg:
            try:
                await bot.send_message(chat_id, msg, parse_mode="Markdown")
                # Логируем отправку
                conn3 = get_connection()
                cursor3 = conn3.cursor()
                import hashlib
                msg_hash = hashlib.sha256(msg.encode()).hexdigest()
                cursor3.execute("INSERT INTO group_sent_log (chat_id, sent_at, content_type, message_hash, message_text) VALUES (?, ?, ?, ?, ?)",
                                (chat_id, datetime.datetime.now().isoformat(), "auto", msg_hash, msg[:200]))
                conn3.commit()
                conn3.close()
            except Exception as e:
                logging.error(f"Ошибка отправки в группу {chat_id}: {e}")
        await asyncio.sleep(0.5)

# ---------- ЗАПУСК ПЛАНИРОВЩИКА (добавить задачу) ----------
def start_scheduler(bot: Bot, admin_id: int, bot_version: str):
    # ... существующие задачи ...
    # Добавляем новую задачу для групп – каждые 30 минут
    scheduler.add_job(send_group_messages, 'interval', minutes=30, args=[bot])
    scheduler.start()
    logging.info(f"Планировщик заданий запущен, версия бота {bot_version}")