from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import main_menu, profile_menu, menu_button
from database import get_user, update_user, get_subscription_status, get_achievements
from utils import admin_log
import datetime

router = Router()

@router.message(F.text == "👤 МОЙ ПРОФИЛЬ")
async def show_profile(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("Сначала запустите бота через /start")
        return
    sub_status = "Активна" if get_subscription_status(user_id) else "Не активна"
    text = (
        f"👤 Профиль:\n"
        f"Имя: {user['name']}\n"
        f"Дата рождения: {user.get('birth_date', 'не указана')}\n"
        f"Число судьбы: {user.get('birth_number', 'не рассчитано')}\n"
        f"Подписка: {sub_status}\n"
        f"Телефон: {user.get('phone', 'не указан')}\n"
        f"Город: {user.get('city', 'не указан')}\n"
        f"Время рождения: {user.get('birth_time', 'не указано')}\n"
        f"Место рождения: {user.get('birth_place', 'не указано')}\n"
        f"Уровень: {user.get('level', 1)}"
    )
    await message.answer(text, reply_markup=profile_menu)

# Обработка кнопок профиля (выборочно)
@router.message(F.text == "✏️ СМЕНИТЬ ИМЯ")
async def change_name(message: Message):
    await message.answer("Введите новое имя:", reply_markup=None)
    # Сохраняем состояние, что пользователь хочет сменить имя (можно через FSM или временное хранилище)
    # Для простоты пропустим реализацию FSM

@router.message(F.text == "⭐ КУПИТЬ ПОДПИСКУ")
async def buy_subscription(message: Message):
    await message.answer(
        "Подписка стоит 249 ₽ в месяц. Оплата через Telegram Stars.\n"
        "Нажмите кнопку ниже, чтобы оплатить.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Оплатить Stars", callback_data="pay_subscription")]
            ]
        )
    )

@router.callback_query(F.data == "pay_subscription")
async def process_payment(callback: CallbackQuery):
    # Здесь логика платежей через Stars
    await callback.answer("Функция оплаты в разработке", show_alert=True)

@router.message(F.text == "🎁 БЕСПЛАТНЫЕ ДНИ")
async def referral_info(message: Message):
    await message.answer("Пригласите друга, и получите бонусные дни подписки. Ваша реферальная ссылка: ...")

@router.message(F.text == "🏆 ДОСТИЖЕНИЯ")
async def show_achievements(message: Message):
    user_id = message.from_user.id
    ach = get_achievements(user_id)
    if ach:
        await message.answer("Ваши достижения:\n" + "\n".join(ach))
    else:
        await message.answer("У вас пока нет достижений. Продолжайте пользоваться ботом!")

@router.message(F.text == "⚙️ НАСТРОЙКИ")
async def settings_menu(message: Message):
    await message.answer("Настройки:\nУкажите телефон, город, время рождения, место рождения.", reply_markup=None)

@router.message(F.text == "📜 ИСТОРИЯ ЗАПРОСОВ")
async def history(message: Message):
    await message.answer("Последние 10 запросов будут показаны здесь.")

@router.message(F.text == "🎟️ ВВЕСТИ ПРОМОКОД")
async def enter_promo(message: Message):
    await message.answer("Введите промокод:")

@router.message(F.text == "👥 ПРИГЛАСИТЬ В ГРУППУ")
async def invite_group(message: Message):
    await message.answer("Добавьте бота в чат командой /startarkadiy, чтобы активировать автоматические рассылки.")

@router.message(F.text == "❓ ПОМОЩЬ")
async def help_command(message: Message):
    await message.answer(
        "Справка: используйте кнопки меню для доступа к функциям.\n"
        "Если нужна помощь, напишите @Aristocrat102."
    )

@router.message(F.text == "✖️ ЗАКРЫТЬ")
async def close_profile(message: Message):
    await message.answer("Закрыто.", reply_markup=main_menu)