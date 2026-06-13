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
            "maxTokens": 2000   # увеличено для матрицы
        },
        "messages": [
            {
                "role": "system",
                "text": (
                    "Ты — Аркадий Викторович, практикующий нумеролог и психолог с 20-летним стажем. "
                    "Говори прямо, без сюсюканий. Для запроса «Матрица судьбы» дай развёрнутый ответ на 10-15 предложений."
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
                    return f"⚠️ Ошибка YandexGPT: {resp.status}"
        except asyncio.TimeoutError:
            _failure_count += 1
            _last_failure_time = time.time()
            return "⏳ Нейросеть думает слишком долго. Попробуйте ещё раз через минуту."
        except Exception as e:
            _failure_count += 1
            _last_failure_time = time.time()
            return f"⚠️ Ошибка соединения: {str(e)}"