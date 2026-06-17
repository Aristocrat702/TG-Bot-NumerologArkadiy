import datetime
import logging
import random
import hashlib
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import backup_database, add_subscription_days
from utils.notifications import (
    generate_morning_greeting,
    generate_motivation,
    generate_daily_card,
    generate_fact,
    generate_evening_advice,
    generate_adaptive_3_days,
    generate_adaptive_7_days,
    generate_adaptive_14_days,
    generate_subscription_reminder
)
from utils.misc import get_inactivity_days

scheduler = AsyncIOScheduler()

MSK_OFFSET = 3

def is_night_time() -> bool:
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_msk = now_utc + datetime.timedelta(hours=MSK_OFFSET)
    hour = now_msk.hour
    return hour >= 23 or hour < 8

# ---------- ГРУППОВАЯ РАССЫЛКА ----------
async def send_group_messages(bot: Bot):
    logging.info("🔔 send_group_messages вызвана")
    if is_night_time():
        logging.info("🌙 Ночной режим – рассылка в группы пропущена")
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, frequency FROM group_chats WHERE is_active=1")
    groups = cursor.fetchall()
    conn.close()
    if not groups:
        logging.info("📭 Нет активных групп для рассылки")
        return
    for chat_id, frequency in groups:
        today = datetime.date.today().isoformat()
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM group_sent_log WHERE chat_id=? AND sent_at LIKE ?", (chat_id, f"{today}%"))
        sent_count = cursor2.fetchone()[0]
        conn2.close()
        max_messages = frequency * 2
        if sent_count >= max_messages:
            continue
        is_long = (sent_count % 4 == 0)
        msg = await generate_unique_message(chat_id, is_long)
        try:
            await bot.send_message(chat_id, msg, parse_mode="Markdown")
            logging.info(f"✅ Отправлено сообщение в группу {chat_id}")
        except Exception as e:
            logging.error(f"❌ Ошибка отправки в группу {chat_id}: {e}")
        await asyncio.sleep(0.5)

async def generate_unique_message(chat_id: int, is_long: bool = False) -> str:
    topics = [
        ("psychology", 35),
        ("relationships", 25),
        ("support", 25),
        ("self_knowledge", 10),
        ("numerology", 3),
        ("astrology", 2)
    ]
    topics_list = [t for t, w in topics for _ in range(w)]
    for attempt in range(5):
        topic = random.choice(topics_list)
        length_desc = "развёрнутое (8–10 предложений)" if is_long else "короткое (2–3 предложения)"
        prompt = f"""
Ты — Аркадий Викторович, мудрый собеседник, который делится полезными, тёплыми и поддерживающими мыслями.
ТЕМА: {topic}
ДЛИНА: {length_desc}
ТРЕБОВАНИЯ:
- Говори просто, человечно, без сложных терминов.
- Если тема психология, отношения, поддержка – сделай сообщение тёплым, с вопросом или интригой в конце.
- Избегай политики, религии, осуждения.
- Не используй штампы вроде «вы должны».
- Сообщение должно быть уникальным, не повторять предыдущие формулировки.
Напиши только текст сообщения, без лишних вступлений.
"""
        response = await get_yandex_gpt_response(prompt, 0, function_name="group_messages")
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

# ---------- НОЧНОЕ ПРИВЕТСТВИЕ (в 22:00 МСК) ----------
async def send_night_greeting(bot: Bot):
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_msk = now_utc + datetime.timedelta(hours=MSK_OFFSET)
    hour = now_msk.hour
    minute = now_msk.minute
    if hour != 22 or minute < 0 or minute > 5:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM group_chats WHERE is_active=1")
    groups = cursor.fetchall()
    conn.close()
    today = datetime.date.today().isoformat()
    for (chat_id,) in groups:
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute(
            "SELECT 1 FROM group_sent_log WHERE chat_id=? AND content_type='night_greeting' AND sent_at LIKE ?",
            (chat_id, f"{today}%")
        )
        if cursor2.fetchone():
            conn2.close()
            continue
        msg = random.choice([
            "Спокойной ночи, друзья! Пусть сны будут ясными, а завтрашний день – добрым.",
            "Уходя, оставляю вам тишину. Отдыхайте. Завтра будет новый день.",
            "Звёзды уже зажглись. Я тоже гашу свет. До встречи завтра."
        ])
        try:
            await bot.send_message(chat_id, msg, parse_mode="Markdown")
            cursor2.execute(
                "INSERT INTO group_sent_log (chat_id, sent_at, message_hash, content_type) VALUES (?, ?, ?, ?)",
                (chat_id, datetime.datetime.now().isoformat(), hashlib.sha256(msg.encode()).hexdigest(), "night_greeting")
            )
            conn2.commit()
            logging.info(f"🌙 Отправлено ночное приветствие в группу {chat_id}")
        except Exception as e:
            logging.error(f"Ошибка отправки ночного приветствия в группу {chat_id}: {e}")
        conn2.close()
        await asyncio.sleep(0.3)

# ---------- УТРЕННЕЕ ПРИВЕТСТВИЕ (в 08:00 МСК) ----------
async def send_morning_greeting(bot: Bot):
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_msk = now_utc + datetime.timedelta(hours=MSK_OFFSET)
    hour = now_msk.hour
    minute = now_msk.minute
    if hour != 8 or minute < 0 or minute > 5:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM group_chats WHERE is_active=1")
    groups = cursor.fetchall()
    conn.close()
    today = datetime.date.today().isoformat()
    for (chat_id,) in groups:
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute(
            "SELECT 1 FROM group_sent_log WHERE chat_id=? AND content_type='morning_greeting' AND sent_at LIKE ?",
            (chat_id, f"{today}%")
        )
        if cursor2.fetchone():
            conn2.close()
            continue
        msg = random.choice([
            "Доброе утро! Новый день – новые возможности. Я с вами.",
            "Просыпайтесь! Мир ждёт вас. Сегодня мы разберёмся с тем, что вчера казалось сложным.",
            "Утро – время для планов. Пусть сегодняшний день будет удачным."
        ])
        try:
            await bot.send_message(chat_id, msg, parse_mode="Markdown")
            cursor2.execute(
                "INSERT INTO group_sent_log (chat_id, sent_at, message_hash, content_type) VALUES (?, ?, ?, ?)",
                (chat_id, datetime.datetime.now().isoformat(), hashlib.sha256(msg.encode()).hexdigest(), "morning_greeting")
            )
            conn2.commit()
            logging.info(f"☀️ Отправлено утреннее приветствие в группу {chat_id}")
        except Exception as e:
            logging.error(f"Ошибка отправки утреннего приветствия в группу {chat_id}: {e}")
        conn2.close()
        await asyncio.sleep(0.3)

# ---------- PUSH-УВЕДОМЛЕНИЯ ----------
async def send_push_notification(bot: Bot, notification_type: str, generator_func):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, destiny_number, subscription_active FROM users WHERE is_sleeping = 0")
    users = cursor.fetchall()
    conn.close()
    if not users:
        logging.info(f"Нет пользователей для рассылки {notification_type}")
        return
    for user_id, destiny, sub_active in users:
        is_subscriber = bool(sub_active)
        try:
            text, reply_markup = await generator_func(user_id, destiny or 1, is_subscriber)
            if not text:
                continue
            await bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления {notification_type} пользователю {user_id}: {e}")
        await asyncio.sleep(0.3)

# ---------- ЗАДАЧИ PUSH ----------
async def send_morning_notifications(bot: Bot):
    await send_push_notification(bot, "morning", generate_morning_greeting)

async def send_motivation_notifications(bot: Bot):
    await send_push_notification(bot, "motivation", generate_motivation)

async def send_daily_card_notifications(bot: Bot):
    await send_push_notification(bot, "daily_card", generate_daily_card)

async def send_fact_notifications(bot: Bot):
    await send_push_notification(bot, "fact", generate_fact)

async def send_evening_notifications(bot: Bot):
    await send_push_notification(bot, "evening", generate_evening_advice)

# ---------- АДАПТИВНЫЕ ----------
async def send_adaptive_notifications(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, destiny_number, last_active, subscription_active FROM users WHERE is_sleeping = 0")
    users = cursor.fetchall()
    conn.close()
    if not users:
        logging.info("Нет пользователей для адаптивных уведомлений")
        return
    for user_id, destiny, last_active, sub_active in users:
        days = get_inactivity_days(user_id)
        is_subscriber = bool(sub_active)
        if days == 3:
            text, reply_markup = await generate_adaptive_3_days(user_id, destiny or 1, is_subscriber)
        elif days == 7:
            text, reply_markup = await generate_adaptive_7_days(user_id, destiny or 1, is_subscriber)
        elif days == 14:
            text, reply_markup = await generate_adaptive_14_days(user_id, destiny or 1, is_subscriber)
        else:
            continue
        try:
            await bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
            logging.info(f"Отправлено адаптивное уведомление пользователю {user_id} (дней: {days})")
        except Exception as e:
            logging.error(f"Ошибка отправки адаптивного уведомления пользователю {user_id}: {e}")
        await asyncio.sleep(0.3)

# ---------- НАПОМИНАНИЕ О ПОДПИСКЕ ----------
async def send_subscription_reminder(bot: Bot):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()
    three_days_later = now + datetime.timedelta(days=3)
    cursor.execute("SELECT user_id, subscription_end, destiny_number FROM users WHERE subscription_active=1 AND subscription_end IS NOT NULL")
    users = cursor.fetchall()
    conn.close()
    for user_id, end_str, destiny in users:
        try:
            end_date = datetime.datetime.fromisoformat(end_str)
            if end_date <= three_days_later and end_date > now:
                text, reply_markup = await generate_subscription_reminder(user_id, destiny or 1)
                await bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
                logging.info(f"Отправлено напоминание о подписке пользователю {user_id}")
        except Exception as e:
            logging.error(f"Ошибка отправки напоминания о подписке пользователю {user_id}: {e}")
        await asyncio.sleep(0.3)

# ---------- СТАТЬИ СЕКСОЛОГИИ ----------
async def generate_sexology_articles(bot: Bot):
    from database import get_sexology_articles, add_sexology_article, get_bot_config
    from settings import SEXOLOGY_TOPICS
    import random
    conn = get_connection()
    cursor = conn.cursor()
    week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    cursor.execute("SELECT COUNT(*) FROM sexology_articles WHERE created_at >= ?", (week_ago,))
    count = cursor.fetchone()[0]
    conn.close()
    articles_per_week = int(get_bot_config("sexology_articles_per_week", "2"))
    if count >= articles_per_week:
        logging.info("Статей за неделю достаточно, пропускаем генерацию")
        return
    topics = random.sample(SEXOLOGY_TOPICS, min(articles_per_week, len(SEXOLOGY_TOPICS)))
    for topic in topics:
        prompt = f"Напиши короткую полезную статью (5-7 предложений) на тему '{topic}'. Используй стиль Аркадия Викторовича: тепло, профессионально, без сложных терминов. Добавь интригу в конце."
        content = await get_yandex_gpt_response(prompt, 0, function_name="generate_article")
        add_sexology_article(topic, content, topic, "pending")
        logging.info(f"Сгенерирована статья на тему: {topic}")
    logging.info("Генерация статей завершена")

# ---------- ПРОЧИЕ ----------
async def check_expired_subscriptions(bot: Bot):
    logging.info("check_expired_subscriptions выполнена (заглушка)")

async def weekly_leaderboard(bot: Bot, admin_id: int = None):
    logging.info("weekly_leaderboard выполнена (заглушка)")

# ---------- ЗАПУСК ----------
def start_scheduler(bot: Bot, admin_id: int, bot_version: str):
    scheduler.remove_all_jobs()
    scheduler.add_job(send_group_messages, IntervalTrigger(minutes=30), args=[bot], id="send_group_messages")
    scheduler.add_job(send_night_greeting, CronTrigger(hour=22, minute=0), args=[bot], id="night_greeting")
    scheduler.add_job(send_morning_greeting, CronTrigger(hour=8, minute=0), args=[bot], id="morning_greeting")
    scheduler.add_job(send_morning_notifications, CronTrigger(hour=8, minute=0), args=[bot], id="morning_push")
    scheduler.add_job(send_motivation_notifications, CronTrigger(hour=10, minute=0), args=[bot], id="motivation_push")
    scheduler.add_job(send_daily_card_notifications, CronTrigger(hour=12, minute=0), args=[bot], id="daily_card_push")
    scheduler.add_job(send_fact_notifications, CronTrigger(hour=15, minute=0), args=[bot], id="fact_push")
    scheduler.add_job(send_evening_notifications, CronTrigger(hour=18, minute=0), args=[bot], id="evening_push")
    scheduler.add_job(send_adaptive_notifications, CronTrigger(hour=20, minute=0), args=[bot], id="adaptive_push")
    scheduler.add_job(send_subscription_reminder, CronTrigger(hour=10, minute=0), args=[bot], id="subscription_reminder")
    scheduler.add_job(generate_sexology_articles, CronTrigger(day_of_week='tue,fri', hour=12, minute=0), args=[bot], id="generate_sexology_articles")
    scheduler.add_job(check_expired_subscriptions, CronTrigger(hour=2, minute=0), args=[bot], id="check_expired")
    scheduler.add_job(backup_database, CronTrigger(hour=3, minute=0), id="backup_db")
    scheduler.add_job(weekly_leaderboard, CronTrigger(day_of_week='sun', hour=20, minute=0), args=[bot, admin_id], id="weekly_lb")
    scheduler.start()
    logging.info(f"Планировщик запущен с задачами сексологии, версия {bot_version}")