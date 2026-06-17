from aiogram import Router, F
from aiogram.types import Message
from keyboards import astro_submenu, menu_button
from database import get_user, update_user
from yandex_gpt import get_yandex_response

router = Router()

@router.message(F.text == "🌌 НАТАЛЬНАЯ КАРТА")
async def natal_chart(message: Message):
    await message.answer("Введите дату, время и место рождения для построения натальной карты (например, 01.01.2000 12:00 Москва)")

@router.message(F.text == "🔄 ТРАНЗИТЫ")
async def transits(message: Message):
    await message.answer("Прогноз транзитов на месяц (требуется дата рождения)")

@router.message(F.text == "☀️ СОЛЯР")
async def solar(message: Message):
    await message.answer("Соляр (годовой прогноз) – требует даты рождения")

@router.message(F.text == "♓ СОВМЕСТИМОСТЬ ПО ЗНАКАМ")
async def compatibility_signs(message: Message):
    await message.answer("В разработке")