from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
import datetime
import asyncio
import logging
from utils import backup_database, add_subscription_days, get_challenge_progress, get_zodiac_sign, get_or_generate_horoscope, get_cached_response, save_cached_response

scheduler = AsyncIOScheduler()

# ---------- Существующие задачи (карта дня, лидерборд, бэкап, челлендж, будильники) ----------
async def send_daily_card(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, destiny_number FROM users WHERE subscription_active=1 AND send_daily=1")
    users = cursor.fetchall()
    conn.close()
    for user in users:
        user_id = user[0]
        destiny = user[1] if user[1] else "?"
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай короткий прогноз (3-5 предложений) с практическим действием. Также добавь одну психологическую практику."
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

async def send_alarms(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%H:%M")
    cursor.execute("SELECT user_id, alarm_time FROM alarms WHERE is_active=1 AND alarm_time=?", (now,))
    alarms = cursor.fetchall()
    conn.close()
    for (user_id, alarm_time) in alarms:
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT city, destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor2.fetchone()
        conn2.close()
        city = row[0] if row else None
        destiny = row[1] if row else "?"
        weather_str = ""
        if city:
            from utils import get_city_coords, get_weather_by_coords
            lat, lon = await get_city_coords(city)
            if lat and lon:
                weather_str = await get_weather_by_coords(lat, lon)
                weather_str = f"\n\n🌤️ *Погода в {city}:* {weather_str}"
        moon_phase = "🌙 Луна в растущей фазе."
        prompt = f"Для человека с числом судьбы {destiny} в городе {city}. Дай короткий мотивирующий совет на день (1-2 предложения)."
        advice = await get_yandex_gpt_response(prompt, user_id)
        text = f"⏰ *Умный будильник!*\n\n{advice}{weather_str}\n\n{moon_phase}\n\nХорошего дня!"
        await bot.send_message(user_id, text, parse_mode="Markdown")
        conn3 = get_connection()
        cursor3 = conn3.cursor()
        cursor3.execute("UPDATE alarms SET is_active=0 WHERE user_id=? AND alarm_time=?", (user_id, alarm_time))
        conn3.commit()
        conn3.close()
        await asyncio.sleep(0.1)

# ---------- НОВЫЕ ЗАДАЧИ ДЛЯ ГОРОСКОПА ----------
async def send_daily_horoscope(bot: Bot):
    """
    Отправляет гороскоп на сегодня всем пользователям, у которых есть дата рождения.
    Время отправки – 9:00 по местному времени (запускается каждый час, проверяет, кому пора).
    Для пользователей без часового пояса – 9:00 МСК.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, destiny_number, birth_date, timezone FROM users WHERE birth_date IS NOT NULL AND birth_date != ''")
    users = cursor.fetchall()
    conn.close()
    now_utc = datetime.datetime.utcnow()
    for (user_id, destiny, birth_date, tz_str) in users:
        try:
            # Получаем часовой пояс пользователя или МСК по умолчанию
            if tz_str:
                tz = pytz.timezone(tz_str)
            else:
                tz = pytz.timezone("Europe/Moscow")
            local_time = now_utc.astimezone(tz)
            # Отправляем, если сейчас 9:00 по местному времени
            if local_time.hour == 9 and local_time.minute == 0:
                zodiac = get_zodiac_sign(birth_date)
                today_str = datetime.datetime.now().strftime("%Y-%m-%d")
                cache_key = f"horoscope_daily_{today_str}_{user_id}"
                cached = get_cached_response(user_id, cache_key)
                if cached:
                    response = cached
                else:
                    response = await get_or_generate_horoscope(user_id, destiny, zodiac, "daily", today_str, True)
                    # Кэшируем на день, чтобы не генерировать повторно при рассылке
                    save_cached_response(user_id, cache_key, response)
                await bot.send_message(user_id, f"🌟 *Ваш гороскоп на сегодня*\n\n{response}", parse_mode="Markdown")
                await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Ошибка отправки дневного гороскопа пользователю {user_id}: {e}")

async def send_monthly_horoscope(bot: Bot):
    """
    Отправляет гороскоп на месяц 1-го числа в 10:00 по местному времени.
    Только для подписчиков.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, destiny_number, birth_date, timezone FROM users WHERE subscription_active=1 AND birth_date IS NOT NULL AND birth_date != ''")
    users = cursor.fetchall()
    conn.close()
    now_utc = datetime.datetime.utcnow()
    for (user_id, destiny, birth_date, tz_str) in users:
        try:
            if tz_str:
                tz = pytz.timezone(tz_str)
            else:
                tz = pytz.timezone("Europe/Moscow")
            local_time = now_utc.astimezone(tz)
            # Первое число месяца и 10:00 утра
            if local_time.day == 1 and local_time.hour == 10 and local_time.minute == 0:
                zodiac = get_zodiac_sign(birth_date)
                month_str = local_time.strftime("%Y-%m")
                cache_key = f"horoscope_monthly_{month_str}_{user_id}"
                cached = get_cached_response(user_id, cache_key)
                if cached:
                    response = cached
                else:
                    response = await get_or_generate_horoscope(user_id, destiny, zodiac, "monthly", month_str, True)
                    save_cached_response(user_id, cache_key, response)
                await bot.send_message(user_id, f"🌟 *Ваш гороскоп на месяц*\n\n{response}", parse_mode="Markdown")
                await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Ошибка отправки месячного гороскопа пользователю {user_id}: {e}")

# ---------- Запуск планировщика ----------
def start_scheduler(bot: Bot, admin_id: int, bot_version: str):
    if admin_id is None:
        logging.warning("admin_id не передан, лидерборд работать не будет")
    # Существующие задачи
    scheduler.add_job(send_daily_card, 'cron', hour=9, minute=0, args=[bot], timezone='Europe/Moscow')
    if admin_id:
        scheduler.add_job(weekly_leaderboard, 'cron', day_of_week='sun', hour=20, minute=0, args=[bot, admin_id], timezone='Europe/Moscow')
    scheduler.add_job(daily_backup, 'cron', hour=3, minute=0, timezone='Europe/Moscow')
    scheduler.add_job(send_challenge_reminders, 'cron', hour=10, minute=0, args=[bot], timezone='Europe/Moscow')
    scheduler.add_job(send_alarms, 'interval', minutes=1, args=[bot])
    # Новые задачи для гороскопов
    scheduler.add_job(send_daily_horoscope, 'interval', minutes=60, args=[bot])  # проверяем каждый час
    scheduler.add_job(send_monthly_horoscope, 'interval', minutes=60, args=[bot]) # проверяем каждый час
    scheduler.start()
    logging.info(f"Планировщик заданий запущен, версия бота {bot_version}")