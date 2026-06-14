import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import horoscope_choice_menu, menu_button
from database import get_connection
from utils import (
    get_user_subscription_status, get_zodiac_sign, get_or_generate_horoscope
)

last_answer = {}

def register_horoscope_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "🌟 ГОРОСКОП")
    async def horoscope_menu(message: types.Message):
        await message.answer(
            "🌟 *Гороскоп*\n\n"
            "Выберите, на какой период вы хотите получить прогноз.\n"
            "• Гороскоп на сегодня – бесплатно для всех.\n"
            "• Гороскоп на месяц – доступен только по подписке.",
            parse_mode="Markdown",
            reply_markup=horoscope_choice_menu
        )

    @dp.callback_query(F.data == "horoscope_daily")
    async def daily_horoscope(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, birth_date, subscription_active FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0] or not row[1]:
            await callback.message.answer("Сначала укажите дату рождения через /start или кнопку «МОЁ ЧИСЛО».")
            await callback.answer()
            return
        destiny = row[0]
        birth_date = row[1]
        zodiac = get_zodiac_sign(birth_date)
        is_subscriber = row[2] == 1
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        status_msg = await callback.message.answer("🌟 Аркадий Викторович готовит ваш гороскоп на сегодня...")
        response = await get_or_generate_horoscope(user_id, destiny, zodiac, "daily", today_str, is_subscriber)
        await status_msg.delete()
        await callback.message.answer(f"🌟 *Гороскоп на сегодня*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        await callback.answer()

    @dp.callback_query(F.data == "horoscope_monthly")
    async def monthly_horoscope(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, birth_date, subscription_active FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0] or not row[1]:
            await callback.message.answer("Сначала укажите дату рождения через /start или кнопку «МОЁ ЧИСЛО».")
            await callback.answer()
            return
        destiny = row[0]
        birth_date = row[1]
        zodiac = get_zodiac_sign(birth_date)
        is_subscriber = row[2] == 1
        if not is_subscriber:
            await callback.message.answer("❌ Гороскоп на месяц доступен только по подписке. Оформите подписку в профиле.", reply_markup=menu_button)
            await callback.answer()
            return
        today = datetime.datetime.now()
        month_str = today.strftime("%Y-%m")
        status_msg = await callback.message.answer("🌟 Аркадий Викторович готовит ваш гороскоп на месяц... Это может занять до минуты.")
        response = await get_or_generate_horoscope(user_id, destiny, zodiac, "monthly", month_str, is_subscriber)
        await status_msg.delete()
        await callback.message.answer(f"🌟 *Гороскоп на месяц*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        await callback.answer()