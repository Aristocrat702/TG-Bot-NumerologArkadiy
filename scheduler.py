from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
import datetime
import asyncio
import logging
import pytz
from utils import (
    backup_database, add_subscription_days, get_challenge_progress,
    get_zodiac_sign, get_cached_response, save_cached_response,
    format_subscription_remaining, check_and_expire_subscriptions
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu

scheduler = AsyncIOScheduler()

# ---------- СУЩЕСТВУЮЩИЕ ЗАДАЧИ ----------
async def send_daily_card(bot: Bot):
    """Отправляет карту дня подписчикам в 9:00 МСК."""
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
    """Воскресенье 20:00 – топ активных подписчиков."""
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
    """Ежедневный бэкап БД в 3:00 МСК."""
    backup_database()
    logging.info("Резервное копирование базы данных выполнено")

async def send_challenge_reminders(bot: Bot):
    """Напоминания по челленджу в 10:00 МСК."""
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

async def send_daily_horoscope(bot: Bot):
    """Гороскоп на день в 9:00 по местному времени пользователя."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, birth_date, destiny_number, timezone FROM users WHERE send_daily=1")
    users = cursor.fetchall()
    conn.close()
    now_utc = datetime.datetime.utcnow()
    for user in users:
        user_id = user[0]
        birth_date = user[1]
        destiny = user[2] if user[2] else "?"
        timezone_str = user[3] if user[3] else "Europe/Moscow"
        try:
            tz = pytz.timezone(timezone_str)
        except:
            tz = pytz.timezone("Europe/Moscow")
        local_time = now_utc + tz.utcoffset(now_utc)
        if local_time.hour == 9:
            zodiac = get_zodiac_sign(birth_date) if birth_date else "неизвестно"
            prompt = (
                f"Составь астрологический гороскоп на сегодня ({datetime.datetime.now().strftime('%d.%m.%Y')}) "
                f"для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. "
                "Дай краткий прогноз (3-5 предложений) и добавь один конкретный совет."
            )
            response = await get_yandex_gpt_response(prompt, user_id)
            if "не специализируюсь" in response.lower() or "не могу" in response.lower():
                new_prompt = prompt.replace("гороскоп", "нумерологический прогноз")
                response = await get_yandex_gpt_response(new_prompt, user_id)
                if "не специализируюсь" in response.lower():
                    response = "🌟 Сегодня хороший день для новых начинаний. Ваше число судьбы дарит уверенность. Сделайте шаг вперёд."
            try:
                await bot.send_message(user_id, f"🌟 *Ваш гороскоп на сегодня*\n\n{response}", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Не удалось отправить гороскоп {user_id}: {e}")
        await asyncio.sleep(0.1)

async def send_monthly_horoscope(bot: Bot):
    """Гороскоп на месяц 1-го числа в 10:00 по местному времени (только подписчики)."""
    if datetime.date.today().day != 1:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, birth_date, destiny_number, timezone FROM users WHERE subscription_active=1 AND send_daily=1")
    users = cursor.fetchall()
    conn.close()
    now_utc = datetime.datetime.utcnow()
    month_name = datetime.date.today().strftime('%B').lower()
    for user in users:
        user_id = user[0]
        birth_date = user[1]
        destiny = user[2] if user[2] else "?"
        timezone_str = user[3] if user[3] else "Europe/Moscow"
        try:
            tz = pytz.timezone(timezone_str)
        except:
            tz = pytz.timezone("Europe/Moscow")
        local_time = now_utc + tz.utcoffset(now_utc)
        if local_time.hour == 10:
            zodiac = get_zodiac_sign(birth_date) if birth_date else "неизвестно"
            prompt = (
                f"Составь астрологический гороскоп на месяц {month_name} для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. "
                "Дай развёрнутый прогноз (8-10 предложений) по сферам: любовь, деньги, здоровье. Укажи благоприятные периоды и дай общий совет."
            )
            response = await get_yandex_gpt_response(prompt, user_id)
            if "не специализируюсь" in response.lower() or "не могу" in response.lower():
                new_prompt = prompt.replace("гороскоп", "нумерологический прогноз")
                response = await get_yandex_gpt_response(new_prompt, user_id)
                if "не специализируюсь" in response.lower():
                    response = "В этом месяце вас ждут позитивные перемены в работе и финансах. Обратите внимание на здоровье. Благоприятные дни: 5, 12, 21."
            try:
                await bot.send_message(user_id, f"🌟 *Ваш гороскоп на месяц {month_name.capitalize()}*\n\n{response}", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Не удалось отправить месячный гороскоп {user_id}: {e}")
        await asyncio.sleep(0.1)

# ---------- НОВЫЕ ЗАДАЧИ ----------
async def send_motivation(bot: Bot):
    """Ежедневно в 11:00 отправляет подписчикам мотивирующую фразу."""
    today_str = datetime.date.today().isoformat()
    cache_key = f"motivation_{today_str}"
    cached = get_cached_response(0, cache_key)
    if cached:
        phrase = cached
    else:
        prompt = "Придумай короткую, мудрую, мотивирующую фразу или аффирмацию в стиле Аркадия Викторовича (нумеролога и психолога). Не более 2 предложений. Не используй шаблонные фразы."
        phrase = await get_yandex_gpt_response(prompt, 0)
        if "Ошибка" in phrase or len(phrase) < 10:
            fallback = [
                "Числа не врут, но и вы не обманывайте себя. Слушайте душу.",
                "Ваше число судьбы – это компас. Следуйте ему без страха.",
                "Ошибки – это тоже цифры, которые ведут к правильному ответу.",
                "Не бойтесь начинать с нуля. Ноль – это начало нового цикла.",
                "Каждое утро вы перезагружаете свою личную статистику. Используйте это.",
                "Гармония приходит, когда внутреннее число совпадает с внешним действием.",
                "Счастье – это не случайность, а сумма правильных решений.",
                "Ваш путь уникален, как отпечаток пальца. Не сравнивайте.",
                "Смелость – это когда ваш страх умножают на веру в себя.",
                "Маленькие победы складываются в большую судьбу."
            ]
            import random
            phrase = random.choice(fallback)
        save_cached_response(0, cache_key, phrase)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE subscription_active=1 AND send_daily=1")
    users = cursor.fetchall()
    conn.close()
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, f"🧠 *Аркадий говорит:*\n\n{phrase}", parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить мотивацию {user_id}: {e}")
        await asyncio.sleep(0.1)

async def check_subscription_expiry(bot: Bot):
    """Проверяет подписки и за 3 дня до окончания отправляет напоминание."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, subscription_end FROM users WHERE subscription_active=1 AND subscription_end IS NOT NULL")
    users = cursor.fetchall()
    conn.close()
    today = datetime.date.today()
    for (user_id, end_str) in users:
        try:
            end_date = datetime.datetime.fromisoformat(end_str).date()
            days_left = (end_date - today).days
            if days_left == 3:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💎 Продлить подписку", callback_data="renew_subscription")],
                    [InlineKeyboardButton(text="🔙 Позже", callback_data="back_to_menu")]
                ])
                await bot.send_message(user_id, f"⚠️ *Ваша подписка закончится через 3 дня!*\n\nНе оставайтесь без полной матрицы и безлимитных вопросов. Продлите подписку сейчас, чтобы не прерывать доступ.", parse_mode="Markdown", reply_markup=kb)
        except:
            pass

async def send_group_messages(bot: Bot):
    """Отправляет контент в группы согласно их настройкам (в 9:00 МСК)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, type FROM group_chats WHERE is_active=1")
    chats = cursor.fetchall()
    conn.close()
    for chat_id, content_type in chats:
        if content_type == "daily_motivation":
            text = "🧠 *Аркадий говорит:*\n\nКаждый день – новая возможность. Доверяйте числам и себе."
        elif content_type == "horoscope":
            text = "🌟 *Гороскоп на сегодня:*\n\nБлагоприятный день для новых начинаний. Обратите внимание на детали."
        elif content_type == "advice":
            text = "💡 *Совет дня:*\n\nНе бойтесь просить о помощи, когда это необходимо."
        else:
            continue
        try:
            await bot.send_message(chat_id, text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Ошибка отправки в группу {chat_id}: {e}")
        await asyncio.sleep(0.1)

# ---------- ЗАПУСК ПЛАНИРОВЩИКА ----------
def start_scheduler(bot: Bot, admin_id: int, bot_version: str):
    if admin_id is None:
        logging.warning("admin_id не передан, лидерборд работать не будет")
    # Существующие задачи
    scheduler.add_job(send_daily_card, 'cron', hour=9, minute=0, args=[bot], timezone='Europe/Moscow')
    if admin_id:
        scheduler.add_job(weekly_leaderboard, 'cron', day_of_week='sun', hour=20, minute=0, args=[bot, admin_id], timezone='Europe/Moscow')
    scheduler.add_job(daily_backup, 'cron', hour=3, minute=0, timezone='Europe/Moscow')
    scheduler.add_job(send_challenge_reminders, 'cron', hour=10, minute=0, args=[bot], timezone='Europe/Moscow')
    scheduler.add_job(send_daily_horoscope, 'interval', minutes=30, args=[bot])
    scheduler.add_job(send_monthly_horoscope, 'cron', day='1', hour=10, minute=0, args=[bot], timezone='Europe/Moscow')
    # Новые задачи
    scheduler.add_job(send_motivation, 'cron', hour=11, minute=0, args=[bot], timezone='Europe/Moscow')
    scheduler.add_job(check_subscription_expiry, 'cron', hour=10, minute=0, args=[bot], timezone='Europe/Moscow')
    scheduler.add_job(send_group_messages, 'cron', hour=9, minute=0, args=[bot], timezone='Europe/Moscow')
    scheduler.add_job(check_and_expire_subscriptions, 'cron', hour=2, minute=0)  # каждую ночь проверяем и отключаем истекшие
    scheduler.start()
    logging.info(f"Планировщик заданий запущен, версия бота {bot_version}")