from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
import datetime
import asyncio
import logging
import random
import hashlib
from utils import backup_database, add_subscription_days, get_challenge_progress, get_bot_config

scheduler = AsyncIOScheduler()

NIGHT_START = 23
NIGHT_END = 8

TOPICS = [
    ("psychology", 35),
    ("relationships", 25),
    ("support", 25),
    ("self_knowledge", 10),
    ("numerology", 3),
    ("astrology", 2)
]

GOODNIGHT_MESSAGES = [
    "Друзья, Аркадий Викторович уходит в мир чисел. Спокойной ночи! Завтра будут новые открытия.",
    "Нумерология не спит, но я – да. До завтра! Пусть вам снятся правильные числа.",
    "Звёзды тоже отдыхают. И я с ними. Сладких снов!",
    "Час поздний, а мысли всё крутятся? Запишите их, а завтра разберёмся. Спокойной ночи."
]

GOODMORNING_MESSAGES = [
    "Доброе утро! Новый день – новые числа. Сегодня удача на стороне тех, кто действует.",
    "Солнце встало, и я с ним. Желаю вам ясного ума и тёплого сердца.",
    "Просыпайтесь! Числа уже ждут вас. Сегодня отличный день для начинаний.",
    "Доброе утро! Новый день – как чистый лист. Заполните его своими смыслами. Сегодня я с вами."
]

async def is_night_time() -> bool:
    now = datetime.datetime.now().hour
    return now >= NIGHT_START or now < NIGHT_END

async def generate_unique_message(chat_id: int, is_long: bool = False) -> str:
    for attempt in range(5):
        topics_list = [t for t, w in TOPICS for _ in range(w)]
        topic = random.choice(topics_list)
        length = "long" if is_long else "short"
        prompt = f"""
Ты — Аркадий Викторович, мудрый собеседник, который делится полезными, тёплыми и поддерживающими мыслями.

ТЕМА: {topic}
ДЛИНА: {'развёрнутое (8-10 предложений)' if is_long else 'короткое (2-3 предложения)'}

ТРЕБОВАНИЯ:
- Говори просто, человечно, без сложных терминов.
- Если тема психология, отношения, поддержка – сделай сообщение тёплым, с вопросом или интригой в конце.
- Избегай политики, религии, осуждения.
- Не используй штампы вроде «вы должны».
- Сообщение должно быть уникальным, не повторять предыдущие формулировки.

Напиши только текст сообщения, без лишних вступлений.
"""
        response = await get_yandex_gpt_response(prompt, 0)
        if len(response) < 10 or "Ошибка" in response:
            fallback = [
                "Сегодня отличный день, чтобы начать что-то новое. Даже маленький шаг меняет маршрут.",
                "Вы сильнее, чем думаете. Напомните себе об этом сегодня.",
                "Иногда лучшее, что можно сделать – это просто быть рядом."
            ]
            response = random.choice(fallback)

        msg_hash = hashlib.sha256(response.encode()).hexdigest()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM group_sent_log WHERE chat_id=? AND message_hash=?", (chat_id, msg_hash))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO group_sent_log (chat_id, sent_at, message_hash, content_type) VALUES (?, ?, ?, ?)",
                           (chat_id, datetime.datetime.now().isoformat(), msg_hash, topic))
            conn.commit()
            conn.close()
            return response
        conn.close()
    return random.choice([
        "Сегодня хороший день, чтобы задуматься о своих целях. Что вы хотите изменить?",
        "Помните: вы – главный герой своей жизни. Действуйте!"
    ])

async def send_group_messages(bot: Bot):
    if await is_night_time():
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, frequency FROM group_chats WHERE is_active=1")
    groups = cursor.fetchall()
    conn.close()

    for chat_id, frequency in groups:
        today = datetime.date.today().isoformat()
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM group_sent_log WHERE chat_id=? AND sent_at LIKE ?", (chat_id, f"{today}%"))
        sent_count = cursor2.fetchone()[0]
        conn2.close()
        if sent_count >= frequency * 2:
            continue
        is_long = (sent_count % 4 == 0)
        msg = await generate_unique_message(chat_id, is_long)
        try:
            await bot.send_message(chat_id, msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Ошибка отправки в группу {chat_id}: {e}")
        await asyncio.sleep(0.5)

async def send_night_greetings(bot: Bot):
    now = datetime.datetime.now()
    if now.hour == 22 and now.minute >= 55:
        msg = random.choice(GOODNIGHT_MESSAGES)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM group_chats WHERE is_active=1")
        groups = cursor.fetchall()
        conn.close()
        for (chat_id,) in groups:
            try:
                await bot.send_message(chat_id, msg, parse_mode="Markdown")
            except:
                pass
    elif now.hour == 8 and now.minute <= 5:
        msg = random.choice(GOODMORNING_MESSAGES)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM group_chats WHERE is_active=1")
        groups = cursor.fetchall()
        conn.close()
        for (chat_id,) in groups:
            try:
                await bot.send_message(chat_id, msg, parse_mode="Markdown")
            except:
                pass

async def send_daily_card(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, destiny_number, city FROM users WHERE subscription_active=1")
    users = cursor.fetchall()
    conn.close()
    for user_id, destiny, city in users:
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай короткий прогноз (3-5 предложений) с практическим действием и психологической практикой."
        response = await get_yandex_gpt_response(prompt, user_id)
        try:
            await bot.send_message(user_id, f"🎁 *Карта дня*\n\n{response}", parse_mode="Markdown")
        except:
            pass
        await asyncio.sleep(0.3)

async def send_daily_horoscope(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, birth_date, destiny_number FROM users WHERE subscription_active=1")
    users = cursor.fetchall()
    conn.close()
    for user_id, birth_date, destiny in users:
        if not birth_date:
            continue
        from utils import get_zodiac_sign
        zodiac = get_zodiac_sign(birth_date)
        prompt = f"Составь астрологический гороскоп на сегодня для человека с числом судьбы {destiny} и знаком {zodiac}. Дай краткий прогноз (3-5 предложений)."
        response = await get_yandex_gpt_response(prompt, user_id)
        try:
            await bot.send_message(user_id, f"🌟 *Гороскоп на сегодня*\n\n{response}", parse_mode="Markdown")
        except:
            pass
        await asyncio.sleep(0.3)

async def check_expired_subscriptions(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, subscription_end FROM users WHERE subscription_active=1 AND subscription_end IS NOT NULL")
    rows = cursor.fetchall()
    now = datetime.datetime.now()
    for user_id, end_str in rows:
        try:
            end_date = datetime.datetime.fromisoformat(end_str)
            if end_date < now:
                cursor.execute("UPDATE users SET subscription_active = 0 WHERE user_id = ?", (user_id,))
        except:
            pass
    conn.commit()
    conn.close()

async def weekly_leaderboard(bot: Bot, admin_id: int = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT first_name, subscription_end 
        FROM users 
        WHERE subscription_active=1 
        ORDER BY subscription_end DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        text = "Нет активных подписчиков."
    else:
        text = "🏆 *Топ подписчиков:*\n\n"
        for i, (name, end) in enumerate(rows, 1):
            text += f"{i}. {name or 'Без имени'} — до {end[:10]}\n"
    if admin_id:
        await bot.send_message(admin_id, text, parse_mode="Markdown")
    else:
        admin_ids_str = get_bot_config("admin_ids", "[]")
        try:
            import ast
            admin_ids = ast.literal_eval(admin_ids_str) if isinstance(admin_ids_str, str) else admin_ids_str
            for aid in admin_ids:
                await bot.send_message(aid, text, parse_mode="Markdown")
        except:
            pass

def start_scheduler(bot: Bot, admin_id: int, bot_version: str):
    scheduler.add_job(send_group_messages, IntervalTrigger(minutes=30), args=[bot])
    scheduler.add_job(send_night_greetings, IntervalTrigger(minutes=1), args=[bot])
    scheduler.add_job(send_daily_card, CronTrigger(hour=9, minute=0), args=[bot])
    scheduler.add_job(send_daily_horoscope, CronTrigger(hour=9, minute=5), args=[bot])
    scheduler.add_job(check_expired_subscriptions, CronTrigger(hour=2, minute=0), args=[bot])
    scheduler.add_job(backup_database, CronTrigger(hour=3, minute=0))
    scheduler.add_job(weekly_leaderboard, CronTrigger(day_of_week='sun', hour=20, minute=0), args=[bot, admin_id])
    scheduler.start()
    logging.info(f"Планировщик заданий запущен, версия бота {bot_version}")