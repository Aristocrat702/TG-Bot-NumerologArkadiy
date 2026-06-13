import aiohttp
import os
import time
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

_failure_count = 0
_last_failure_time = 0

async def get_yandex_gpt_response(prompt: str, user_id: int) -> str:
    global _failure_count, _last_failure_time
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return "⚠️ Ошибка: не настроен YandexGPT. Администратор уже в курсе."
    if _failure_count >= 3 and (time.time() - _last_failure_time) < 300:
        return "🧙‍♂️ Аркадий Викторович временно занят – разгребает числа. Задайте вопрос через пару минут."
    
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
            "maxTokens": 1500
        },
        "messages": [
            {
                "role": "system",
                "text": (
                    "Ты — Аркадий Викторович, практикующий нумеролог и психолог с 20-летним стажем. "
                    "Твоя задача — прямо, без сюсюканий, помогать людям через анализ чисел. "
                    "Говори правду в лоб. Называй слабости. "
                    "Не говори, что ты нейросеть. Ты — живой человек. "
                    "Если вопрос не о нумерологии или психологии — мягко откажи. "
                    "Для «Матрицы судьбы» дай развёрнутый ответ (10-15 предложений) по арканам, с конкретными шагами."
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
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    _failure_count = 0
                    return result["result"]["alternatives"][0]["message"]["text"]
                else:
                    _failure_count += 1
                    _last_failure_time = time.time()
                    return f"⚠️ Ошибка YandexGPT: {resp.status}. Попробуйте позже."
        except asyncio.TimeoutError:
            _failure_count += 1
            _last_failure_time = time.time()
            return "⏳ Превышено время ожидания. Нейросеть долго думает. Попробуйте ещё раз через минуту."
        except Exception as e:
            _failure_count += 1
            _last_failure_time = time.time()
            return f"⚠️ Не удалось связаться с нейросетью. Аркадий Викторович уже чинит."