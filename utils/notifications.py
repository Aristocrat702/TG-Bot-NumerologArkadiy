import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yandex_gpt import get_yandex_gpt_response

def get_subscription_button() -> InlineKeyboardMarkup:
    """Возвращает inline-кнопку для перехода к покупке подписки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Полная версия – по подписке", callback_data="buy_subscription")]
    ])

# ---------- PUSH-УВЕДОМЛЕНИЯ ----------
async def generate_morning_greeting(user_id: int, destiny: int, is_subscriber: bool):
    if is_subscriber:
        prompt = f"Составь утреннее приветствие (2-3 предложения) и короткий гороскоп на сегодня для человека с числом судьбы {destiny}. Ответ должен быть тёплым, вдохновляющим, с советом на день."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, None
    else:
        prompt = f"Составь короткое утреннее приветствие (1-2 предложения) и тизер гороскопа на сегодня для человека с числом судьбы {destiny}. Добавь фразу: «Полный гороскоп и карта дня – по подписке»."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, get_subscription_button()

async def generate_motivation(user_id: int, destiny: int, is_subscriber: bool):
    if is_subscriber:
        prompt = f"Напиши мотивирующую фразу (3-4 предложения) с учётом числа судьбы {destiny}. Добавь вопрос в конце, чтобы вовлечь пользователя."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, None
    else:
        prompt = f"Напиши короткую мотивирующую фразу (1-2 предложения) с вопросом в конце. Добавь приписку: «Больше мотивации и практик – по подписке»."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, get_subscription_button()

async def generate_daily_card(user_id: int, destiny: int, is_subscriber: bool):
    if is_subscriber:
        prompt = f"Составь карту дня (5-7 предложений) для человека с числом судьбы {destiny}. Включи практический совет и психологическую практику."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, None
    else:
        prompt = f"Составь краткую карту дня (2-3 предложения) для человека с числом судьбы {destiny}. Добавь фразу: «Полная карта дня с практиками – по подписке»."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, get_subscription_button()

async def generate_fact(user_id: int, destiny: int, is_subscriber: bool):
    if is_subscriber:
        prompt = f"Дай интересный факт о числе {destiny} или знаке зодиака (если известен). Факт должен быть полезным и интригующим. 2-3 предложения."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, None
    else:
        prompt = f"Дай короткий интересный факт о числе {destiny} (1-2 предложения). Добавь фразу: «Ещё больше фактов и прогнозов – по подписке»."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, get_subscription_button()

async def generate_evening_advice(user_id: int, destiny: int, is_subscriber: bool):
    if is_subscriber:
        prompt = f"Напиши вечерний совет (3-4 предложения) для человека с числом судьбы {destiny}. Это должна быть практика для рефлексии или завершения дня."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, None
    else:
        prompt = f"Напиши короткий вечерний совет (1-2 предложения) для человека с числом судьбы {destiny}. Добавь фразу: «Полные практики и советы – по подписке»."
        text = await get_yandex_gpt_response(prompt, user_id)
        return text, get_subscription_button()

# ---------- АДАПТИВНЫЕ УВЕДОМЛЕНИЯ ----------
async def generate_adaptive_3_days(user_id: int, destiny: int, is_subscriber: bool):
    prompt = f"Напиши тёплое, цепляющее сообщение (3-4 предложения) для человека с числом судьбы {destiny}, который не заходил в бот 3 дня. Сообщение должно быть интригующим, с вопросом в конце, чтобы человек захотел вернуться. Используй обращение «друг мой» или «уважаемый»."
    text = await get_yandex_gpt_response(prompt, user_id)
    return text, None

async def generate_adaptive_7_days(user_id: int, destiny: int, is_subscriber: bool):
    prompt = f"Напиши сообщение (4-5 предложений) для человека с числом судьбы {destiny}, который не заходил 7 дней. Скажи, что у него есть персональный прогноз, и он может узнать что-то важное о себе. Добавь фразу: «Загляните – не пожалеете!»."
    text = await get_yandex_gpt_response(prompt, user_id)
    return text, None

async def generate_adaptive_14_days(user_id: int, destiny: int, is_subscriber: bool):
    prompt = f"Напиши сообщение (4-5 предложений) для человека с числом судьбы {destiny}, который не заходил 14 дней. Спроси, всё ли в порядке, и предложи короткую аффирмацию. Добавь фразу: «Будем рады видеть вас снова!»."
    text = await get_yandex_gpt_response(prompt, user_id)
    return text, None

# ---------- НАПОМИНАНИЕ О ПОДПИСКЕ ----------
async def generate_subscription_reminder(user_id: int, destiny: int):
    prompt = f"Напиши сообщение (3-4 предложения) для человека с числом судьбы {destiny}, у которого заканчивается подписка через 3 дня. Предложи продлить подписку, упомяни преимущества (матрица, безлимитные вопросы, прогнозы). Будь дружелюбен и ненавязчив."
    text = await get_yandex_gpt_response(prompt, user_id)
    return text, get_subscription_button()