import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import astro_submenu, main_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import update_last_active, get_zodiac_sign, get_user_subscription_status, get_cached_response, save_cached_response
from utils.misc import get_user_gender
from utils.notifications import get_subscription_button

router = Router()

# ===== ОБРАБОТЧИК КНОПКИ "АСТРОЛОГИЯ" =====
@router.message(F.text == "🌟 АСТРОЛОГИЯ")
async def astro_menu(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта функция доступна только в личном чате.")
        return
    await message.answer(
        "🌟 <b>Астрологический раздел</b>\n\nВыберите, что вас интересует:",
        parse_mode="HTML",
        reply_markup=astro_submenu
    )

# ---------- НАТАЛЬНАЯ КАРТА (кратко) ----------
@router.callback_query(F.data == "astro_natal")
async def natal_chart(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    gender = get_user_gender(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date, birth_time, birth_place FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения в профиле (настройки).", reply_markup=main_menu)
        await callback.answer()
        return
    birth_date = row[0]

    status_msg = await callback.message.answer("🌌 Аркадий Викторович строит вашу натальную карту...")
    prompt = f"Дай очень краткое описание (2-3 предложения) того, что можно узнать из натальной карты человека, родившегося {birth_date}. Сделай так, чтобы человек заинтересовался. В конце добавь фразу: «Полная натальная карта с планетами и аспектами – по подписке в разделе «Эксклюзив»». Используй HTML-теги для выделения ключевых фраз."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="natal", gender=gender)
    await status_msg.delete()
    await callback.message.answer(
        f"🌌 <b>Ваша натальная карта (кратко)</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=get_subscription_button()
    )
    update_last_active(user_id)
    await callback.answer()

# ---------- ТРАНЗИТЫ (кратко) ----------
@router.callback_query(F.data == "astro_transits")
async def transits(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    gender = get_user_gender(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения в профиле.", reply_markup=main_menu)
        await callback.answer()
        return
    birth_date = row[0]
    zodiac = get_zodiac_sign(birth_date)

    status_msg = await callback.message.answer("🔄 Аркадий Викторович анализирует транзиты...")
    prompt = f"Дай краткое описание транзитов (2-3 предложения) для человека со знаком {zodiac} на ближайший месяц. Сделай так, чтобы человеку захотелось узнать больше. В конце добавь фразу: «Полный прогноз транзитов с датами – по подписке в разделе «Эксклюзив»». Используй HTML-теги для выделения ключевых фраз."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="transits", gender=gender)
    await status_msg.delete()
    await callback.message.answer(
        f"🔄 <b>Транзиты на месяц (кратко)</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=get_subscription_button()
    )
    update_last_active(user_id)
    await callback.answer()

# ---------- СОЛЯР (кратко) ----------
@router.callback_query(F.data == "astro_solar")
async def solar(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    gender = get_user_gender(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения в профиле.", reply_markup=main_menu)
        await callback.answer()
        return
    birth_date = row[0]
    zodiac = get_zodiac_sign(birth_date)

    status_msg = await callback.message.answer("☀️ Аркадий Викторович рассчитывает соляр...")
    prompt = f"Дай краткое описание соляра (2-3 предложения) для человека со знаком {zodiac} на предстоящий год. Сделай так, чтобы человек почувствовал, что это важно. В конце добавь фразу: «Полный прогноз соляра на год – по подписке в разделе «Эксклюзив»». Используй HTML-теги для выделения ключевых фраз."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="solar", gender=gender)
    await status_msg.delete()
    await callback.message.answer(
        f"☀️ <b>Ваш соляр на год (кратко)</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=get_subscription_button()
    )
    update_last_active(user_id)
    await callback.answer()

# ---------- ГОРОСКОП НА ДЕНЬ ----------
@router.callback_query(F.data == "horoscope_daily")
async def horoscope_daily(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    is_subscriber = get_user_subscription_status(user_id)
    gender = get_user_gender(user_id)
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
            prompt = f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай развёрнутый прогноз (6-7 предложений) по 2 сферам (любовь и работа/деньги). Добавь совет на день. Используй HTML-теги для выделения ключевых фраз."
            response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_daily", gender=gender)
            reply_markup = menu_button
        else:
            prompt = f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай краткий прогноз (5-6 предложений): что важно сегодня, дай один совет, задай вопрос для размышления. В конце добавь фразу: «Полный гороскоп на месяц и ежедневные прогнозы – по подписке». Используй HTML-теги для выделения ключевых фраз."
            response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_daily", gender=gender)
            reply_markup = get_subscription_button()
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, cache_key, response)
    await callback.message.answer(
        f"🌟 <b>Гороскоп на сегодня</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    update_last_active(user_id)
    await callback.answer()

# ---------- ГОРОСКОП НА МЕСЯЦ ----------
@router.callback_query(F.data == "horoscope_monthly")
async def horoscope_monthly(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    is_subscriber = get_user_subscription_status(user_id)
    gender = get_user_gender(user_id)
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

    if is_subscriber:
        # Полный гороскоп для подписчиков
        cache_key = f"horoscope_monthly_{today.strftime('%Y-%m')}_{user_id}"
        cached = get_cached_response(user_id, cache_key)
        if cached:
            response = cached
        else:
            status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
            prompt = f"Составь астрологический гороскоп на месяц {month_name} для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай развёрнутый прогноз (8-10 предложений) по сферам: любовь, деньги, здоровье. Укажи благоприятные периоды и дай общий совет. Используй HTML-теги для выделения ключевых фраз."
            response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_monthly", gender=gender)
            await status_msg.delete()
            if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
                save_cached_response(user_id, cache_key, response)
        await callback.message.answer(
            f"🌟 <b>Гороскоп на месяц</b>\n\n{response}",
            parse_mode="HTML",
            reply_markup=menu_button
        )
    else:
        # Краткий вариант для бесплатных
        status_msg = await callback.message.answer("🔮 Аркадий Викторович даёт краткий прогноз...")
        prompt = f"Составь краткий, но очень точный астрологический прогноз на месяц {month_name} для человека со знаком {zodiac} и числом судьбы {destiny}. Дай 4 предложения: что его ждёт в любви, деньгах, здоровье – и один самый важный совет. Сделай так, чтобы человек почувствовал, что это про него. В конце добавь фразу: «Полный гороскоп на месяц с деталями – по подписке». Используй HTML-теги для выделения ключевых фраз."
        response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_monthly_free", gender=gender)
        await status_msg.delete()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Получить полный гороскоп", callback_data="buy_subscription")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        await callback.message.answer(
            f"🌟 <b>Гороскоп на месяц (кратко)</b>\n\n{response}",
            parse_mode="HTML",
            reply_markup=kb
        )
    update_last_active(user_id)
    await callback.answer()