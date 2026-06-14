import datetime
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, get_zodiac_sign

class HoroscopeStates(StatesGroup):
    waiting_choice = State()

def register_horoscope_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    async def get_horoscope_from_ai(prompt: str, user_id: int) -> str:
        """Пытается получить ответ от YandexGPT, при отказе переформулирует запрос."""
        response = await get_yandex_gpt_response(prompt, user_id)
        # Если ответ содержит отказ, меняем формулировку
        if ("не специализируюсь" in response.lower() or 
            "не могу" in response.lower() or 
            "отказываюсь" in response.lower()):
            # Заменяем "гороскоп" на "нумерологический прогноз"
            new_prompt = prompt.replace("гороскоп", "нумерологический прогноз")
            response = await get_yandex_gpt_response(new_prompt, user_id)
            if "не специализируюсь" in response.lower() or "не могу" in response.lower():
                # Fallback
                return "🌟 Сегодня хороший день для новых начинаний. Ваше число судьбы дарит уверенность. Сделайте шаг вперёд."
        return response

    @dp.message(F.text == "🌟 ГОРОСКОП")
    async def horoscope_menu(message: types.Message, state: FSMContext):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 На сегодня", callback_data="horoscope_daily")],
            [InlineKeyboardButton(text="📆 На месяц", callback_data="horoscope_monthly")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ])
        await message.answer("🌟 *Астрологический гороскоп*\n\nВыберите период:", parse_mode="Markdown", reply_markup=kb)
        await state.set_state(HoroscopeStates.waiting_choice)

    @dp.callback_query(HoroscopeStates.waiting_choice, F.data.startswith("horoscope_"))
    async def process_horoscope_choice(callback: types.CallbackQuery, state: FSMContext):
        horizon = callback.data.split("_")[1]  # "daily" или "monthly"
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)

        if horizon == "monthly" and not is_subscriber:
            await callback.message.answer("❌ Гороскоп на месяц доступен только по подписке. Оформите подписку в профиле.", reply_markup=main_menu)
            await state.clear()
            await callback.answer()
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала укажите дату рождения через /start или /mynumber.", reply_markup=main_menu)
            await state.clear()
            await callback.answer()
            return

        birth_date = row[0]
        destiny = row[1] if row[1] else "?"
        zodiac = get_zodiac_sign(birth_date)
        today = datetime.date.today()

        status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")

        if horizon == "daily":
            prompt = (
                f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) "
                f"для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. "
                "Дай краткий прогноз (3-5 предложений) и добавь один конкретный совет на день."
            )
            response = await get_horoscope_from_ai(prompt, user_id)
            title = "на сегодня"
        else:
            month_name = today.strftime('%B').lower()
            prompt = (
                f"Составь астрологический гороскоп на месяц {month_name} для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. "
                "Дай развёрнутый прогноз (8-10 предложений) по сферам: любовь, деньги, здоровье. "
                "Укажи благоприятные периоды и дай общий совет."
            )
            response = await get_horoscope_from_ai(prompt, user_id)
            title = "на месяц"

        await status_msg.delete()
        await callback.message.answer(
            f"🌟 *Гороскоп {title}*\n\n{response}",
            parse_mode="Markdown", reply_markup=main_menu
        )
        await state.clear()
        await callback.answer()