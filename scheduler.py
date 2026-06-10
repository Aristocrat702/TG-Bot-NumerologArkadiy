from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
import datetime
import asyncio
import logging
from utils import backup_database, add_subscription_days, get_challenge_progress

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
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай короткий прогноз (3-5 предложений) с практическим действием. Также добавь одну психологическую практику (например, дыхательное упражнение или совет по саморегуляции)."
        response = await get_yandex_gpt_response(prompt, user_id)
        try:
            await bot.send_message(user_id, f"🎁 *Карта дня*\n\n{response}", parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить карту дня пользователю {user_id}: {e}")
        await asyncio.sleep(0.1)

async def weekly_leaderboard(bot: Bot, admin_id: int):
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
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT name FROM users WHERE user_id=?", (uid,))
        name_row = cursor2.fetchone()
        conn2.close()
        name = name_row[0] if name_row else str(uid)
        text += f"{i}. {name} — {cnt} сообщений\n"
        add_subscription_days(uid, 3, check_referral=False, admin_id=0)
    await bot.send_message(admin_id, text)

async def daily_backup():
    backup_database()
    logging.info("Резервное копирование базы данных выполнено")

async def send_challenge_reminders(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM challenges WHERE completed=0")
    users = cursor.fetchall()
    conn.close()
    tasks = {
        1: "Скажите «нет» человеку, который вас напрягает.",
        2: "Сделайте спонтанный поступок (поменяйте маршрут, купите необычный продукт).",
        3: "Напишите себе письмо «Что я изменю через месяц».",
        4: "Сделайте зарядку 5 минут.",
        5: "Поблагодарите себя за что-то вслух.",
        6: "Отдайте ненужную вещь.",
        7: "Запланируйте конкретную цель на неделю."
    }
    for (uid,) in users:
        progress = get_challenge_progress(uid)
        if not progress:
            continue
        for day, completed in progress:
            if not completed:
                await bot.send_message(uid, f"🔥 Напоминание по челленджу: задание дня {day}: {tasks.get(day, 'Выполните любой шаг')}\n\nНажмите кнопку «Выполнил» в профиле, когда сделаете.")
                break

def start_scheduler(bot: Bot, admin_id: int):
    if admin_id is None:
        logging.warning("admin_id не передан, лидерборд работать не будет")
    scheduler.add_job(send_daily_card, 'cron', hour=12, minute=0, args=[bot], timezone='Europe/Moscow')
    if admin_id:
        scheduler.add_job(weekly_leaderboard, 'cron', day_of_week='sun', hour=20, minute=0, args=[bot, admin_id], timezone='Europe/Moscow')
    scheduler.add_job(daily_backup, 'cron', hour=3, minute=0, timezone='Europe/Moscow')
    scheduler.add_job(send_challenge_reminders, 'cron', hour=10, minute=0, args=[bot], timezone='Europe/Moscow')
    scheduler.start()
    logging.info("Планировщик заданий запущен")