import datetime
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, get_zodiac_sign

class HoroscopeStates(StatesGroup):
    waiting_choice = State()

def register_horoscope_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    async def get_horoscope_from_ai(prompt: str, user_id: int) -> str:
        response = await get_yandex_gpt_response(prompt, user_id)
        if ("не специализируюсь" in response.lower() or 
            "не могу" in response.lower() or 
            "отказываюсь" in response.lower()):
            new_prompt = prompt.replace("гороскоп", "нумерологический прогноз")
            response = await get_yandex_gpt_response(new_prompt, user_id)
            if "не специализируюсь" in response.lower() or "не могу" in response.lower():
                return "🌟 Сегодня хороший день для новых начинаний. Ваше число судьбы дарит уверенность. Сделайте шаг вперёд."
        return response

    @dp.message(F.text == "🌟 АСТРОЛОГИЯ")
    async def astro_menu(message: types.Message):
        from keyboards import astro_submenu
        await message.answer("🌟 *Астрологический раздел*\n\nВыберите, что вас интересует:", parse_mode="Markdown", reply_markup=astro_submenu)

    @dp.message(F.text == "📅 Гороскоп на день")  # если кто-то наберёт текст, но у нас есть кнопка
    async def horoscope_daily_from_message(message: types.Message, state: FSMContext):
        # Аналогично callback, но для удобства оставим
        await message.answer("Используйте кнопку в меню «АСТРОЛОГИЯ».")

    # Фактически обработчики для horoscope_daily и horoscope_monthly уже есть в astro.py, но продублируем здесь для полноты
    @dp.callback_query(F.data == "horoscope_daily")
    async def horoscope_daily(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)
        # daily – бесплатно для всех
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала укажите дату рождения через /start или /mynumber.", reply_markup=menu_button)
            await callback.answer()
            return
        birth_date = row[0]
        destiny = row[1] if row[1] else "?"
        zodiac = get_zodiac_sign(birth_date)
        today = datetime.date.today()
        prompt = (
            f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) "
            f"для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. "
            "Дай краткий прогноз (3-5 предложений) и добавь один конкретный совет."
        )
        status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
        response = await get_horoscope_from_ai(prompt, user_id)
        await status_msg.delete()
        await callback.message.answer(f"🌟 *Гороскоп на сегодня*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        await callback.answer()

    @dp.callback_query(F.data == "horoscope_monthly")
    async def horoscope_monthly(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)
        if not is_subscriber:
            await callback.message.answer("❌ Гороскоп на месяц доступен только по подписке. Оформите подписку в профиле.", reply_markup=menu_button)
            await callback.answer()
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала укажите дату рождения через /start или /mynumber.", reply_markup=menu_button)
            await callback.answer()
            return
        birth_date = row[0]
        destiny = row[1] if row[1] else "?"
        zodiac = get_zodiac_sign(birth_date)
        today = datetime.date.today()
        month_name = today.strftime('%B').lower()
        prompt = (
            f"Составь астрологический гороскоп на месяц {month_name} для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. "
            "Дай развёрнутый прогноз (8-10 предложений) по сферам: любовь, деньги, здоровье. Укажи благоприятные периоды и дай общий совет."
        )
        status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
        response = await get_horoscope_from_ai(prompt, user_id)
        await status_msg.delete()
        await callback.message.answer(f"🌟 *Гороскоп на месяц*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        await callback.answer()