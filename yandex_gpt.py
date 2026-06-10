import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

async def get_yandex_gpt_response(prompt: str, user_id: int) -> str:
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return "шибка: не настроен YandexGPT."
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
            "maxTokens": 500
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты — ркадий икторович, нумеролог и психолог с 20-летним стажем. твечай прямо, без сюсюканий, давай советы."
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
                return f"шибка YandexGPT: {resp.status}"
