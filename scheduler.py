from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
import datetime
import asyncio
import logging
import random
import hashlib
from utils import backup_database, add_subscription_days, get_challenge_progress

scheduler = AsyncIOScheduler()

# Ночной режим: с 23:00 до 08:00 МСК
NIGHT_START = 23
NIGHT_END = 8

# Список тем с весами (психология, отношения, поддержка – преобладают)
TOPICS = [
    ("psychology", 35),
    ("relationships", 25),
    ("support", 25),
    ("self_knowledge", 10),
    ("numerology", 3),
    ("astrology", 2)
]

# Прощальные и утренние сообщения
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
    """Генерирует уникальное сообщение для группы через YandexGPT с проверкой хеша."""
    # Выбираем тему с весами
    topics_list = [t for t, w in TOPICS for _ in range(w)]
    topic = random.choice(topics_list)

    # Определяем длину
    length = "long" if is_long else "short"
    max_tokens = 500 if is_long else 200

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
    # Если ответ слишком короткий или ошибка – используем fallback
    if len(response) < 10 or "Ошибка" in response:
        fallback = [
            "Сегодня отличный день, чтобы начать что-то новое. Даже маленький шаг меняет маршрут.",
            "Вы сильнее, чем думаете. Напомните себе об этом сегодня.",
            "Иногда лучшее, что можно сделать – это просто быть рядом."
        ]
        response = random.choice(fallback)

    # Проверка уникальности (храним хеши последних 100 сообщений)
    msg_hash = hashlib.sha256(response.encode()).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM group_sent_log WHERE chat_id=? AND message_hash=?", (chat_id, msg_hash))
    if cursor.fetchone()[0] > 0:
        # Если повтор, генерируем заново (рекурсивно, но с ограничением)
        conn.close()
        return await generate_unique_message(chat_id, is_long)
    # Сохраняем хеш
    cursor.execute("INSERT INTO group_sent_log (chat_id, sent_at, message_hash, content_type) VALUES (?, ?, ?, ?)",
                   (chat_id, datetime.datetime.now().isoformat(), msg_hash, topic))
    conn.commit()
    conn.close()
    return response

async def send_group_messages(bot: Bot):
    """Отправляет сообщения в группы (каждые 30 минут, ночью молчит)."""
    if await is_night_time():
        return  # ночью не отправляем

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, frequency FROM group_chats WHERE is_active=1")
    groups = cursor.fetchall()
    conn.close()

    for chat_id, frequency in groups:
        # Проверяем, сколько сообщений уже отправлено сегодня
        today = datetime.date.today().isoformat()
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM group_sent_log WHERE chat_id=? AND sent_at LIKE ?", (chat_id, f"{today}%"))
        sent_count = cursor2.fetchone()[0]
        conn2.close()
        # Если превысили частоту (frequency = сообщений в час, но у нас каждые 30 мин, поэтому умножаем на 2)
        if sent_count >= frequency * 2:
            continue

        # Определяем, нужно ли длинное сообщение (раз в 2 часа)
        is_long = (sent_count % 4 == 0)  # каждое 4-е сообщение (т.е. раз в 2 часа)

        msg = await generate_unique_message(chat_id, is_long)
        try:
            await bot.send_message(chat_id, msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Ошибка отправки в группу {chat_id}: {e}")
        await asyncio.sleep(0.5)

async def send_night_greetings(bot: Bot):
    """Отправляет прощальное и утреннее сообщения."""
    now = datetime.datetime.now()
    if now.hour == 22 and now.minute >= 55:
        # Прощальное сообщение
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
        # Утреннее сообщение
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

def start_scheduler(bot: Bot, admin_id: int, bot_version: str):
    # Остальные задачи (карта дня, лидерборд и т.д.) остаются без изменений
    # Добавляем только задачи для групп
    scheduler.add_job(send_group_messages, 'interval', minutes=30, args=[bot])
    scheduler.add_job(send_night_greetings, 'interval', minutes=1, args=[bot])  # проверяем каждую минуту для точного времени
    scheduler.start()
    logging.info(f"Планировщик заданий запущен, версия бота {bot_version}")