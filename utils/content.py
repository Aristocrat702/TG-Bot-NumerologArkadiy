import random
import datetime
import hashlib
from .db import get_connection
from yandex_gpt import get_yandex_gpt_response

TOPICS = [
    ("psychology", 35),
    ("relationships", 25),
    ("support", 25),
    ("self_knowledge", 10),
    ("numerology", 3),
    ("astrology", 2),
]

NIGHT_MESSAGES = [
    "Спокойной ночи, друзья! Пусть сны будут ясными, а завтрашний день – добрым.",
    "Уходя, оставляю вам тишину. Отдыхайте. Завтра будет новый день.",
    "Звёзды уже зажглись. Я тоже гашу свет. До встречи завтра.",
    "Ночь – время для восстановления. Спите спокойно."
]

MORNING_MESSAGES = [
    "Доброе утро! Новый день – новые возможности. Я с вами.",
    "Просыпайтесь! Мир ждёт вас. Сегодня мы разберёмся с тем, что вчера казалось сложным.",
    "Утро – время для планов. Пусть сегодняшний день будет удачным.",
    "Доброе утро! Начните день с улыбки. Я рядом."
]

def generate_night_message() -> str:
    return random.choice(NIGHT_MESSAGES)

def generate_morning_message() -> str:
    return random.choice(MORNING_MESSAGES)

async def generate_group_message(chat_id: int, is_long: bool = False) -> str:
    topics, weights = zip(*TOPICS)
    topic = random.choices(topics, weights=weights, k=1)[0]

    if is_long:
        length_desc = "развёрнутое (8–10 предложений), цепляющее, с интригой"
    else:
        length_desc = "короткое (2–3 предложения), интригующее"

    prompt = (
        f"Ты — Аркадий Викторович, мудрый собеседник. Напиши сообщение для группы людей на тему '{topic}'. "
        f"Сообщение должно быть {length_desc}. "
        "Оно должно быть тёплым, поддерживающим, без сложных терминов. "
        "Если тема психология, отношения или поддержка – сделай акцент на эмоциях, советах, аффирмациях. "
        "Если нумерология или астрология – дай краткий, но интересный факт. "
        "Сообщение должно быть уникальным, не повторять предыдущие формулировки. "
        "Не используй штампы, избегай политики и религии. "
        "Заканчивай интригой или вопросом."
    )

    response = await get_yandex_gpt_response(prompt, 0)

    conn = get_connection()
    cursor = conn.cursor()
    msg_hash = hashlib.sha256(response.encode()).hexdigest()
    week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    cursor.execute("SELECT 1 FROM group_sent_log WHERE message_hash = ? AND sent_at >= ?", (msg_hash, week_ago))
    if cursor.fetchone():
        for attempt in range(3):
            new_prompt = prompt + f" (попытка {attempt+1}, используй другой подход)"
            response = await get_yandex_gpt_response(new_prompt, 0)
            msg_hash = hashlib.sha256(response.encode()).hexdigest()
            cursor.execute("SELECT 1 FROM group_sent_log WHERE message_hash = ? AND sent_at >= ?", (msg_hash, week_ago))
            if not cursor.fetchone():
                break
    conn.close()
    return response