import random
from yandex_gpt import get_yandex_gpt_response

async def generate_morning_greeting(user_id: int, destiny: int, is_subscriber: bool) -> str:
    """Утреннее приветствие + короткий гороскоп."""
    if is_subscriber:
        prompt = f"Составь утреннее приветствие (2-3 предложения) и короткий гороскоп на сегодня для человека с числом судьбы {destiny}. Ответ должен быть тёплым, вдохновляющим, с советом на день."
    else:
        prompt = f"Составь короткое утреннее приветствие (1-2 предложения) и тизер гороскопа на сегодня для человека с числом судьбы {destiny}. Добавь фразу: «Полный гороскоп и карта дня – по подписке»."
    return await get_yandex_gpt_response(prompt, user_id)

async def generate_motivation(user_id: int, destiny: int, is_subscriber: bool) -> str:
    """Мотивационная фраза / аффирмация."""
    if is_subscriber:
        prompt = f"Напиши мотивирующую фразу (3-4 предложения) с учётом числа судьбы {destiny}. Добавь вопрос в конце, чтобы вовлечь пользователя."
    else:
        prompt = f"Напиши короткую мотивирующую фразу (1-2 предложения) с вопросом в конце. Добавь приписку: «Больше мотивации и практик – по подписке»."
    return await get_yandex_gpt_response(prompt, user_id)

async def generate_daily_card(user_id: int, destiny: int, is_subscriber: bool) -> str:
    """Карта дня (сокращённая для всех)."""
    if is_subscriber:
        prompt = f"Составь карту дня (5-7 предложений) для человека с числом судьбы {destiny}. Включи практический совет и психологическую практику."
    else:
        prompt = f"Составь краткую карту дня (2-3 предложения) для человека с числом судьбы {destiny}. Добавь фразу: «Полная карта дня с практиками – по подписке»."
    return await get_yandex_gpt_response(prompt, user_id)

async def generate_fact(user_id: int, destiny: int, is_subscriber: bool) -> str:
    """Интересный факт (нумерология / астрология)."""
    if is_subscriber:
        prompt = f"Дай интересный факт о числе {destiny} или знаке зодиака (если известен). Факт должен быть полезным и интригующим. 2-3 предложения."
    else:
        prompt = f"Дай короткий интересный факт о числе {destiny} (1-2 предложения). Добавь фразу: «Ещё больше фактов и прогнозов – по подписке»."
    return await get_yandex_gpt_response(prompt, user_id)

async def generate_evening_advice(user_id: int, destiny: int, is_subscriber: bool) -> str:
    """Вечерний совет / рефлексия."""
    if is_subscriber:
        prompt = f"Напиши вечерний совет (3-4 предложения) для человека с числом судьбы {destiny}. Это должна быть практика для рефлексии или завершения дня."
    else:
        prompt = f"Напиши короткий вечерний совет (1-2 предложения) для человека с числом судьбы {destiny}. Добавь фразу: «Полные практики и советы – по подписке»."
    return await get_yandex_gpt_response(prompt, user_id)