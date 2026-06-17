from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards import psycho_submenu, main_menu, menu_button
from database import get_user, save_psycho_result, save_mood
from yandex_gpt import get_yandex_response

router = Router()

@router.message(F.text == "🧠 ПСИХОЛОГИЯ")
async def psycho_menu(message: Message):
    await message.answer("Психология:", reply_markup=psycho_submenu)

@router.message(F.text == "🧠 ПСИХОТЕСТ")
async def start_psycho_test(message: Message):
    await message.answer("Начнём психотест. Вопрос 1: ...\nВыберите вариант: (кнопки)", reply_markup=None)
    # Здесь логика теста с вариантами

@router.message(F.text == "📓 ДНЕВНИК НАСТРОЕНИЯ")
async def mood_diary(message: Message):
    await message.answer("Оцените настроение от 1 до 5 и напишите комментарий:")

@router.message(F.text == "👔 СТИЛЬ И УДАЧА")
async def style_test(message: Message):
    await message.answer("Тест на стиль и удачу. Вопрос 1: ...")

@router.message(F.text == "📊 МОИ РЕЗУЛЬТАТЫ ТЕСТА")
async def show_test_results(message: Message):
    await message.answer("Здесь будут ваши последние результаты.")