from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import main_menu, profile_menu, psycho_submenu, astro_submenu
from database import get_user, create_user, update_user
from utils import get_birth_number, get_zodiac_sign
import datetime

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        create_user(user_id, message.from_user.first_name)
        await message.answer(
            f"Здравствуйте, {message.from_user.first_name}!\n"
            "Я — Аркадий Викторович, нумеролог, психолог и астролог с 20-летним стажем.\n"
            "Давайте познакомимся. Укажите вашу дату рождения в формате ДД.ММ.ГГГГ",
            reply_markup=None
        )
    else:
        await message.answer(
            f"С возвращением, {user['name']}! Чем могу помочь?",
            reply_markup=main_menu
        )

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu)

@router.message(F.text == "⬅️ НАЗАД")
async def back_to_main_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu)

# Обработка ввода даты рождения
@router.message(lambda msg: len(msg.text) == 10 and msg.text[2]=='.' and msg.text[5]=='.')
async def process_birth_date(message: Message):
    user_id = message.from_user.id
    try:
        date_obj = datetime.datetime.strptime(message.text, "%d.%m.%Y").date()
        number = get_birth_number(date_obj)
        zodiac = get_zodiac_sign(date_obj)
        update_user(user_id, birth_date=date_obj.isoformat(), birth_number=number, zodiac=zodiac)
        await message.answer(
            f"Ваше число судьбы: {number}\n"
            f"Ваш знак зодиака: {zodiac}\n"
            f"Отлично! Теперь вы можете пользоваться всеми функциями.",
            reply_markup=main_menu
        )
    except ValueError:
        await message.answer("Неверный формат. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ")