from aiogram import Router, F
from aiogram.types import Message
from keyboards import astro_submenu, main_menu, menu_button
from database import get_user, get_subscription_status
from yandex_gpt import get_yandex_response
import datetime

router = Router()

@router.message(F.text == "📅 ГОРОСКОП НА ДЕНЬ")
async def daily_horoscope(message: Message):
    user = get_user(message.from_user.id)
    sign = user.get('zodiac', 'Овен') if user else 'Овен'
    prompt = f"Составь гороскоп на сегодня для знака {sign} (кратко, 3-5 предложений)."
    answer = await get_yandex_response(prompt)
    await message.answer(answer)

@router.message(F.text == "📆 ГОРОСКОП НА МЕСЯЦ")
async def monthly_horoscope(message: Message):
    user_id = message.from_user.id
    if not get_subscription_status(user_id):
        await message.answer("Гороскоп на месяц доступен только по подписке.")
        return
    user = get_user(user_id)
    sign = user.get('zodiac', 'Овен')
    prompt = f"Составь гороскоп на текущий месяц для знака {sign} (развёрнутый)."
    answer = await get_yandex_response(prompt)
    await message.answer(answer)