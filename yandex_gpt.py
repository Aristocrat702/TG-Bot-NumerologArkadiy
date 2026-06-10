import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

async def get_yandex_gpt_response(prompt: str, user_id: int) -> str:
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return "Ошибка: не настроен YandexGPT."
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
        async with session.post(url, headers=headers, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result["result"]["alternatives"][0]["message"]["text"]
            else:
                return f"Ошибка YandexGPT: {resp.status}"