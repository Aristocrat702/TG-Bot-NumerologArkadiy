from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
import datetime
import asyncio
import logging
from utils import backup_database, add_subscription_days

scheduler = AsyncIOScheduler()

async def send_daily_card(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, destiny_number FROM users WHERE subscription_active=1 AND send_daily=1")
    users = cursor.fetchall()
    conn.close()
    for user in users:
        user_id = user[0]
        destiny = user[1] if user[1] else "?"
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай короткий прогноз (3-5 предложений) с практическим действием."
        response = await get_yandex_gpt_response(prompt, user_id)
        try:
            await bot.send_message(user_id, f"🎁 *Карта дня*\n\n{response}", parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить карту дня пользователю {user_id}: {e}")
        await asyncio.sleep(0.1)

async def weekly_leaderboard(bot: Bot, admin_id: int):
    """Раз в неделю (воскресенье 20:00) отправляет топ-5 подписчиков и начисляет +3 дня"""
    week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, COUNT(*) as cnt FROM dialog_history
        WHERE role = "user" AND timestamp > ? 
        AND user_id IN (SELECT user_id FROM users WHERE subscription_active=1)
        GROUP BY user_id ORDER BY cnt DESC LIMIT 5
    ''', (week_ago,))
    top = cursor.fetchall()
    conn.close()
    if not top:
        return
    text = "🏆 *Топ активных подписчиков за неделю:*\n\n"
    for i, (uid, cnt) in enumerate(top, 1):
        # Получим имя пользователя из БД
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT name FROM users WHERE user_id=?", (uid,))
        name_row = cursor2.fetchone()
        conn2.close()
        name = name_row[0] if name_row else str(uid)
        text += f"{i}. {name} — {cnt} сообщений\n"
        # Начисляем бонус
        add_subscription_days(uid, 3)
    await bot.send_message(admin_id, text)

async def daily_backup():
    backup_database()
    logging.info("Резервное копирование базы данных выполнено")

def start_scheduler(bot: Bot, admin_id: int):
    # Ежедневная карта дня в 12:00
    scheduler.add_job(send_daily_card, 'cron', hour=12, minute=0, args=[bot], timezone='Europe/Moscow')
    # Еженедельный лидерборд по воскресеньям в 20:00
    scheduler.add_job(weekly_leaderboard, 'cron', day_of_week='sun', hour=20, minute=0, args=[bot, admin_id], timezone='Europe/Moscow')
    # Ежедневный бэкап БД в 3:00
    scheduler.add_job(daily_backup, 'cron', hour=3, minute=0, timezone='Europe/Moscow')
    scheduler.start()
    logging.info("Планировщик заданий запущен")