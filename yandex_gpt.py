import aiohttp
import os
import time
import asyncio
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

_failure_count = 0
_last_failure_time = 0

async def get_yandex_gpt_response(prompt: str, user_id: int) -> str:
    global _failure_count, _last_failure_time
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return "⚠️ Ошибка: не настроен YandexGPT."
    if _failure_count >= 3 and (time.time() - _last_failure_time) < 300:
        return "🧙‍♂️ Аркадий Викторович временно занят – разгребает числа. Попробуйте через пару минут."

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "system",
                "text": (
                    "Ты — Аркадий Викторович, практикующий нумеролог, психолог и астролог с 20-летним стажем. "
                    "Твоя задача — прямо, без сюсюканий, помогать людям через анализ чисел, знаков зодиака и астрологических прогнозов. "
                    "Говори правду в лоб. Называй слабости. Используй живые фразы: «Слушайте», «Факт», «К делу», «Без соплей». "
                    "Обращайся на «вы». Запрещены фразы «я нейросеть», «я ИИ». "
                    "Отвечай на вопросы о нумерологии, психологии, астрологии, гороскопах, совместимости знаков, числах. "
                    "Если вопрос не по этим темам — мягко откажи. "
                    "Для гороскопа на день дай краткий прогноз (3-5 предложений) и добавь одну короткую инструкцию: «Что вам стоит сделать сегодня для удачи?». "
                    "Для гороскопа на месяц дай развёрнутый прогноз (10-12 предложений) по сферам: любовь, деньги, здоровье. Укажи благоприятные и неблагоприятные периоды. "
                    "Для запроса «Число рождения» выдай краткую характеристику (2-4 предложения), назови слабость и дай совет. "
                    "Для «Матрицы судьбы» выдай развёрнутый ответ (10–15 предложений) по арканам, с конкретными шагами. "
                    "Для «Совместимости» опиши сильные и слабые стороны пары, дай рекомендации (5–7 предложений). "
                    "Для «Карты дня» дай короткий прогноз (3–5 предложений) с практическим действием и психологической практикой. "
                    "Не отказывайся от астрологических вопросов. Ты — астролог."
                )
            },
            {
                "role": "user",
                "text": prompt
            }
        ]
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=180)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    _failure_count = 0
                    return result["result"]["alternatives"][0]["message"]["text"]
                else:
                    _failure_count += 1
                    _last_failure_time = time.time()
                    return f"⚠️ Ошибка YandexGPT: {resp.status}. Пожалуйста, попробуйте позже."
        except asyncio.TimeoutError:
            _failure_count += 1
            _last_failure_time = time.time()
            return "⏳ Нейросеть думает слишком долго. Попробуйте ещё раз через минуту."
        except Exception as e:
            _failure_count += 1
            _last_failure_time = time.time()
            return f"⚠️ Ошибка соединения: {str(e)}. Аркадий Викторович уже чинит."