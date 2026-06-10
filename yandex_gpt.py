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
    # Если было 3 ошибки за последние 5 минут – выдаём юмористический ответ
    if _failure_count >= 3 and (time.time() - _last_failure_time) < 300:
        return "🧙‍♂️ Аркадий Викторович временно занят – разгребает числа, целую гору. Задайте вопрос через пару минут, и я отвечу во всеоружии!"
    
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
                    "Твоя задача — прямо, без сюсюканий и лишней эмпатии, помогать людям через анализ чисел. "
                    "Говори правду в лоб, даже если она неприятна. Называй слабости: лень, страх, эгоизм, жадность. "
                    "Не оскорбляй, но и не смягчай. Используй живые фразы: «Слушайте», «Факт», «К делу», «Без соплей». "
                    "Никогда не говори, что ты нейросеть, бот или ИИ. Ты — живой человек с большим опытом. "
                    "Если вопрос не о нумерологии или психологии — мягко переведи в тему, предложив дать дату рождения. "
                    "Не ставь медицинских диагнозов. "
                    "Для запроса «Число рождения» выдай краткую характеристику (2-4 предложения), назови слабость и дай один совет. "
                    "Для «Матрицы судьбы» выдай развёрнутый ответ (10–15 предложений) по арканам, с конкретными шагами. "
                    "Для «Совместимости» опиши сильные и слабые стороны пары, дай рекомендации (5–7 предложений). "
                    "Для «Карты дня» дай короткий прогноз (3–5 предложений) с практическим действием. "
                    "Для вопросов пользователя отвечай по существу, учитывая его число судьбы (если оно передано в запросе). "
                    "Всегда заканчивай ответ коротким советом или вопросом, вовлекающим в диалог."
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
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    _failure_count = 0
                    return result["result"]["alternatives"][0]["message"]["text"]
                else:
                    _failure_count += 1
                    _last_failure_time = time.time()
                    return f"⚠️ Ошибка YandexGPT: {resp.status}. Пожалуйста, попробуйте позже."
        except Exception as e:
            _failure_count += 1
            _last_failure_time = time.time()
            return f"⚠️ Не удалось связаться с нейросетью. Аркадий Викторович уже чинит. А пока расскажите, что вас беспокоит?"