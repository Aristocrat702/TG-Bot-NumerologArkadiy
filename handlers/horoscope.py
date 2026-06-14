import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, get_zodiac_sign, get_cached_response, save_cached_response

class HoroscopeStates(StatesGroup):
    waiting_choice = State()

def register_horoscope_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):
    @dp.message(F.text == "🌟 ГОРОСКОП")
    async def horoscope_menu(message: types.Message, state: FSMContext):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 На сегодня", callback_data="horoscope_daily")],
            [InlineKeyboardButton(text="📆 На месяц", callback_data="horoscope_monthly")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ])
        await message.answer("🌟 *Гороскоп*\n\nВыберите период:", parse_mode="Markdown", reply_markup=kb)
        await state.set_state(HoroscopeStates.waiting_choice)

    @dp.callback_query(HoroscopeStates.waiting_choice, F.data.startswith("horoscope_"))
    async def process_horoscope_choice(callback: types.CallbackQuery, state: FSMContext):
        horizon = callback.data.split("_")[1]
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
        destiny = row[1]
        zodiac = get_zodiac_sign(birth_date)
        today = datetime.date.today()
        if horizon == "daily":
            target_date = today.strftime("%Y-%m-%d")
            cache_key = f"horoscope_daily_{target_date}_{user_id}"
            prompt = f"Составь гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай краткий прогноз (3-5 предложений)."
        else:
            target_date = today.strftime("%Y-%m")
            cache_key = f"horoscope_monthly_{target_date}_{user_id}"
            month_name = today.strftime('%B').lower()
            prompt = f"Составь гороскоп на месяц {month_name} для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай развёрнутый прогноз (10-12 предложений) по сферам: любовь, деньги, здоровье."

        cached = get_cached_response(user_id, cache_key)
        if cached:
            response = cached
        else:
            status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
                save_cached_response(user_id, cache_key, response)

        await callback.message.answer(f"🌟 *Гороскоп на {'сегодня' if horizon == 'daily' else 'месяц'}*\n\n{response}", parse_mode="Markdown", reply_markup=main_menu)
        await state.clear()
        await callback.answer()