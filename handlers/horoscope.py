import datetime
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import main_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, get_zodiac_sign, get_cached_response, save_cached_response, update_last_active
from utils.notifications import get_subscription_button

router = Router()

def register_horoscope_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.callback_query(F.data == "horoscope_daily")
    async def horoscope_daily(callback: types.CallbackQuery):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Доступно только в личном чате.")
            await callback.answer()
            return
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)
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
        cache_key = f"horoscope_daily_{target_date}_{user_id}_{'sub' if is_subscriber else 'free'}"
        cached = get_cached_response(user_id, cache_key)
        if cached:
            response = cached
            reply_markup = None if is_subscriber else get_subscription_button()
        else:
            status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
            if is_subscriber:
                prompt = f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай развёрнутый прогноз (6-7 предложений) по 2 сферам (любовь и работа/деньги). Добавь совет на день."
                response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_daily")
                reply_markup = menu_button
            else:
                prompt = f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай цепляющий прогноз (5-6 предложений): укажи, что важно сегодня, дай один совет, задай вопрос для размышления. В конце добавь фразу: «Полный гороскоп на месяц и ежедневные прогнозы – по подписке»."
                response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_daily")
                reply_markup = get_subscription_button()
            await status_msg.delete()
            if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
                save_cached_response(user_id, cache_key, response)
        await callback.message.answer(f"🌟 *Гороскоп на сегодня*\n\n{response}", parse_mode="Markdown", reply_markup=reply_markup)
        update_last_active(user_id)
        await callback.answer()

    @dp.callback_query(F.data == "horoscope_monthly")
    async def horoscope_monthly(callback: types.CallbackQuery):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Доступно только в личном чате.")
            await callback.answer()
            return
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)
        if not is_subscriber:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Купить подписку", callback_data="buy_subscription")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
            await callback.message.answer(
                "📆 *Гороскоп на месяц*\n\n"
                "Эта функция доступна только по подписке.\n"
                "Вы получите детальный прогноз на месяц по всем сферам жизни: любовь, карьера, деньги, здоровье.\n"
                "Оформите подписку, чтобы открыть!",
                parse_mode="Markdown",
                reply_markup=kb
            )
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
            prompt = f"Составь астрологический гороскоп на месяц {month_name} для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай развёрнутый прогноз (8-10 предложений) по сферам: любовь, деньги, здоровье. Укажи благоприятные периоды и дай общий совет."
            status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
            response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_monthly")
            await status_msg.delete()
            if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
                save_cached_response(user_id, cache_key, response)
        await callback.message.answer(f"🌟 *Гороскоп на месяц*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        await callback.answer()