import datetime
import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yandex_gpt import get_yandex_gpt_response
from utils.misc import get_cached_response, save_cached_response

def get_subscription_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Полная версия – по подписке", callback_data="buy_subscription")]
    ])

# ---------- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ КЭШИРОВАНИЯ ----------
async def _get_cached_or_generate(user_id: int, cache_key: str, prompt: str, function_name: str):
    """
    Возвращает (текст, reply_markup). reply_markup всегда None,
    чтобы не добавлять рекламные кнопки в push-уведомления.
    """
    cached = get_cached_response(user_id, cache_key)
    if cached:
        return cached, None
    text = await get_yandex_gpt_response(prompt, user_id, function_name=function_name)
    if "Ошибка" not in text and "Нейросеть" not in text and "таймаут" not in text:
        save_cached_response(user_id, cache_key, text)
    return text, None

# ---------- PUSH-УВЕДОМЛЕНИЯ (БЕЗ РЕКЛАМЫ) ----------
async def generate_morning_greeting(user_id: int, destiny: int, is_subscriber: bool):
    today = datetime.date.today().isoformat()
    cache_key = f"morning_{today}_{destiny}_{'sub' if is_subscriber else 'free'}"
    if is_subscriber:
        prompt = (
            f"Составь утреннее приветствие (3-4 предложения) и короткий гороскоп на сегодня для человека с числом судьбы {destiny}. "
            "Ответ должен быть тёплым, вдохновляющим, с советом на день. "
            "Используй HTML-форматирование для выделения ключевых фраз. Без упоминания подписки."
        )
    else:
        prompt = (
            f"Составь короткое утреннее приветствие (2-3 предложения) и полезный совет на сегодня для человека с числом судьбы {destiny}. "
            "Сделай так, чтобы человек почувствовал поддержку и желание начать день. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    text, _ = await _get_cached_or_generate(user_id, cache_key, prompt, "morning_greeting")
    return text, None

async def generate_motivation(user_id: int, destiny: int, is_subscriber: bool):
    today = datetime.date.today().isoformat()
    cache_key = f"motivation_{today}_{destiny}_{'sub' if is_subscriber else 'free'}"
    if is_subscriber:
        prompt = (
            f"Напиши мотивирующую фразу (3-4 предложения) с учётом числа судьбы {destiny}. "
            "Она должна быть глубокой, заставляющей задуматься, с вопросом в конце. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    else:
        prompt = (
            f"Напиши короткую, но сильную мотивирующую фразу (2-3 предложения) на тему саморазвития, отношений или психологии. "
            "Она должна быть полезной, заставляющей задуматься. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    text, _ = await _get_cached_or_generate(user_id, cache_key, prompt, "motivation")
    return text, None

async def generate_daily_card(user_id: int, destiny: int, is_subscriber: bool):
    today = datetime.date.today().isoformat()
    cache_key = f"daily_card_{today}_{destiny}_{'sub' if is_subscriber else 'free'}"
    if is_subscriber:
        prompt = (
            f"Составь карту дня (5-7 предложений) для человека с числом судьбы {destiny}. "
            "Включи практический совет и психологическую практику. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    else:
        prompt = (
            f"Составь краткий, но ценный совет на сегодня (3-4 предложения) для человека с числом судьбы {destiny}. "
            "Дай практическую рекомендацию, которая поможет улучшить день. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    text, _ = await _get_cached_or_generate(user_id, cache_key, prompt, "daily_card_push")
    return text, None

async def generate_fact(user_id: int, destiny: int, is_subscriber: bool):
    today = datetime.date.today().isoformat()
    cache_key = f"fact_{today}_{destiny}_{'sub' if is_subscriber else 'free'}"
    if is_subscriber:
        prompt = (
            f"Дай интересный и полезный факт (3-4 предложения) о числе {destiny}, знаке зодиака или психологии. "
            "Факт должен быть необычным и запоминающимся. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    else:
        prompt = (
            f"Дай короткий, но увлекательный факт (2-3 предложения) из области психологии, отношений или астрологии. "
            "Он должен быть интересным и полезным. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    text, _ = await _get_cached_or_generate(user_id, cache_key, prompt, "fact")
    return text, None

async def generate_evening_advice(user_id: int, destiny: int, is_subscriber: bool):
    today = datetime.date.today().isoformat()
    cache_key = f"evening_{today}_{destiny}_{'sub' if is_subscriber else 'free'}"
    if is_subscriber:
        prompt = (
            f"Напиши вечерний совет (3-4 предложения) для человека с числом судьбы {destiny}. "
            "Это должна быть практика для рефлексии или завершения дня. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    else:
        prompt = (
            f"Напиши короткий вечерний совет (2-3 предложения) для человека с числом судьбы {destiny}. "
            "Помоги ему подвести итоги дня и настроиться на завтра. "
            "Используй HTML-форматирование. Без упоминания подписки."
        )
    text, _ = await _get_cached_or_generate(user_id, cache_key, prompt, "evening_advice")
    return text, None

# ---------- АДАПТИВНЫЕ УВЕДОМЛЕНИЯ (без рекламы) ----------
async def generate_adaptive_3_days(user_id: int, destiny: int, is_subscriber: bool):
    prompt = (
        f"Напиши тёплое, цепляющее сообщение (3-4 предложения) для человека с числом судьбы {destiny}, который не заходил в бот 3 дня. "
        "Сообщение должно быть с вопросом в конце, чтобы человек захотел вернуться. "
        "Используй обращение «друг мой» или «уважаемый». "
        "Используй HTML-форматирование. Без упоминания подписки."
    )
    text = await get_yandex_gpt_response(prompt, user_id, function_name="adaptive_3")
    return text, None

async def generate_adaptive_7_days(user_id: int, destiny: int, is_subscriber: bool):
    prompt = (
        f"Напиши сообщение (4-5 предложений) для человека с числом судьбы {destiny}, который не заходил 7 дней. "
        "Скажи, что у него есть персональный прогноз, и он может узнать что-то важное о себе. "
        "Добавь фразу: «Загляните – не пожалеете!». "
        "Используй HTML-форматирование. Без упоминания подписки."
    )
    text = await get_yandex_gpt_response(prompt, user_id, function_name="adaptive_7")
    return text, None

async def generate_adaptive_14_days(user_id: int, destiny: int, is_subscriber: bool):
    prompt = (
        f"Напиши сообщение (4-5 предложений) для человека с числом судьбы {destiny}, который не заходил 14 дней. "
        "Спроси, всё ли в порядке, и предложи короткую аффирмацию. "
        "Добавь фразу: «Будем рады видеть вас снова!». "
        "Используй HTML-форматирование. Без упоминания подписки."
    )
    text = await get_yandex_gpt_response(prompt, user_id, function_name="adaptive_14")
    return text, None

# ---------- НАПОМИНАНИЕ О ПОДПИСКЕ (единственное, где нужна кнопка) ----------
async def generate_subscription_reminder(user_id: int, destiny: int):
    prompt = (
        f"Напиши сообщение (3-4 предложения) для человека с числом судьбы {destiny}, у которого заканчивается подписка через 3 дня. "
        "Предложи продлить подписку, упомяни преимущества (матрица, безлимитные вопросы, прогнозы). "
        "Будь дружелюбен и ненавязчив. Используй HTML-форматирование."
    )
    text = await get_yandex_gpt_response(prompt, user_id, function_name="subscription_reminder")
    return text, get_subscription_button()