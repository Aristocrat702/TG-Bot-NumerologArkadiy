import aiohttp
import os
import time
import asyncio
import re
from dotenv import load_dotenv
from database import get_prompts_for_function, get_user

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

_failure_count = 0
_last_failure_time = 0

def clean_response(text: str) -> str:
    """Очищает ответ от недопустимых тегов и заменяет Markdown на HTML."""
    if not text:
        return text
    
    # 1. Заменяем **текст** на <b>текст</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # 2. Заменяем *текст* на <i>текст</i> (если не перекрывается с жирным)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    # 3. Удаляем все блочные теги, которые не поддерживает Telegram
    block_tags = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'span', 'ul', 'ol', 'li']
    for tag in block_tags:
        text = re.sub(rf'<{tag}[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(rf'</{tag}>', '', text, flags=re.IGNORECASE)
    # 4. Убираем лишние пустые строки
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

async def get_yandex_gpt_response(prompt: str, user_id: int, function_name: str = "default", gender: str = None) -> str:
    global _failure_count, _last_failure_time
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return "⚠️ Ошибка: не настроен YandexGPT."
    if _failure_count >= 3 and (time.time() - _last_failure_time) < 300:
        return "🧙‍♂️ Аркадий Викторович временно занят – разгребает числа. Попробуйте через пару минут."

    if gender is None and user_id != 0:
        user = get_user(user_id)
        if user:
            if isinstance(user, dict):
                gender = user.get("gender", "unknown")
            else:
                gender = user[22] if len(user) > 22 and user[22] else "unknown"
        else:
            gender = "unknown"
    elif gender is None:
        gender = "unknown"

    prompts = get_prompts_for_function(function_name)
    if prompts:
        system_prompt = prompts["system"]
    else:
        system_prompt = "Ты — Аркадий Викторович, практикующий нумеролог, психолог и астролог с 20-летним стажем..."

    if gender == "male":
        system_prompt += " Обращайся к пользователю как к мужчине: используй «уважаемый», «дорогой», «мой хороший». Не используй женские обращения."
    elif gender == "female":
        system_prompt += " Обращайся к пользователю как к женщине: используй «уважаемая», «дорогая», «моя хорошая». Не используй мужские обращения."
    else:
        system_prompt += " Обращайся к пользователю нейтрально: «друг мой», «уважаемый» (универсально)."

    system_prompt += (
        "\n\n<b>ВАЖНОЕ ТРЕБОВАНИЕ ПО ФОРМАТИРОВАНИЮ ОТВЕТОВ:</b>\n"
        "Используй только разрешённые теги: <b>, <i>, <u>, <s>, <a>, <code>, <pre>.\n"
        "ЗАПРЕЩЕНО ИСПОЛЬЗОВАТЬ ЛЮБЫЕ БЛОЧНЫЕ ТЕГИ: <p>, <div>, <h1>-<h6>, <br>, <span>, <ul>, <ol>, <li>.\n"
        "Для переноса строк используй обычный перевод строки (\\n).\n"
        "Не используй Markdown (звёздочки, подчёркивания) — я сам преобразую их в HTML.\n"
        "Форматируй ответ структурированно, с эмодзи для разделения блоков.\n"
        "Никогда не используй тег <p>."
    )

    if function_name == "article_generation":
        max_tokens = 1500
    else:
        max_tokens = 2000

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
            "maxTokens": max_tokens
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": prompt}
        ]
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=180)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    _failure_count = 0
                    raw = result["result"]["alternatives"][0]["message"]["text"]
                    return clean_response(raw)
                else:
                    _failure_count += 1
                    _last_failure_time = time.time()
                    return f"⚠️ Ошибка YandexGPT: {resp.status}. Попробуйте позже."
        except asyncio.TimeoutError:
            _failure_count += 1
            _last_failure_time = time.time()
            return "⏳ Нейросеть думает слишком долго. Попробуйте ещё раз."
        except Exception as e:
            _failure_count += 1
            _last_failure_time = time.time()
            return f"⚠️ Ошибка соединения: {str(e)}"