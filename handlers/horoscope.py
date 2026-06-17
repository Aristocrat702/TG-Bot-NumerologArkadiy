import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import main_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, get_zodiac_sign, get_cached_response, save_cached_response

router = Router()

class HoroscopeStates(StatesGroup):
    waiting_choice = State()

@router.message(F.text == "📅 Гороскоп на день")
async def horoscope_daily_from_message(message: types.Message, state: FSMContext):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        return
    await message.answer("Используйте кнопку в меню «АСТРОЛОГИЯ».")

@router.callback_query(F.data == "horoscope_daily")
async def horoscope_daily(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
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
    target_date = today.strftime("%Y-%m-%d")
    cache_key = f"horoscope_daily_{target_date}_{user_id}"
    cached = get_cached_response(user_id, cache_key)
    if cached:
        response = cached
    else:
        prompt = (
            f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) "
            f"для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. "
            "Дай краткий прогноз (3-5 предложений) и добавь один конкретный совет."
        )
        status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, cache_key, response)
    await callback.message.answer(f"🌟 *Гороскоп на сегодня*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
    await callback.answer()

@router.callback_query(F.data == "horoscope_monthly")
async def horoscope_monthly(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
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
    target_date = today.strftime("%Y-%m")
    cache_key = f"horoscope_monthly_{target_date}_{user_id}"
    cached = get_cached_response(user_id, cache_key)
    if cached:
        response = cached
    else:
        month_name = today.strftime('%B').lower()
        prompt = (
            f"Составь астрологический гороскоп на месяц {month_name} для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. "
            "Дай развёрнутый прогноз (8-10 предложений) по сферам: любовь, деньги, здоровье. Укажи благоприятные периоды и дай общий совет."
        )
        status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, cache_key, response)
    await callback.message.answer(f"🌟 *Гороскоп на месяц*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
    await callback.answer()