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

# ===== ОБРАБОТЧИК КНОПКИ "АСТРОЛОГИЯ" (НА УРОВНЕ МОДУЛЯ) =====
@router.message(F.text == "🌟 АСТРОЛОГИЯ")
async def astro_menu(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта функция доступна только в личном чате.")
        return
    await message.answer("🌟 *Астрологический раздел*\n\nВыберите, что вас интересует:", parse_mode="Markdown", reply_markup=astro_submenu)

# ---------- НАТАЛЬНАЯ КАРТА (тизер) ----------
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
    birth_time = row[1] if row[1] else "неизвестно"
    birth_place = row[2] if row[2] else "не указано"

    status_msg = await callback.message.answer("🌌 Аркадий Викторович строит вашу натальную карту...")
    prompt = f"Дай очень краткое описание (2-3 предложения) того, что можно узнать из натальной карты человека, родившегося {birth_date}. Добавь интригу и фразу: «Полная натальная карта с планетами и аспектами – по подписке в разделе «Эксклюзив»»."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="natal", gender=gender)
    await status_msg.delete()
    await callback.message.answer(f"🌌 *Ваша натальная карта (тизер)*\n\n{response}", parse_mode="Markdown", reply_markup=get_subscription_button())
    update_last_active(user_id)
    await callback.answer()

# ---------- ТРАНЗИТЫ (тизер) ----------
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
    prompt = f"Дай короткий тизер транзитов (2-3 предложения) для человека со знаком {zodiac} на ближайший месяц. Добавь интригу и фразу: «Полный прогноз транзитов с датами – по подписке в разделе «Эксклюзив»»."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="transits", gender=gender)
    await status_msg.delete()
    await callback.message.answer(f"🔄 *Транзиты на месяц (тизер)*\n\n{response}", parse_mode="Markdown", reply_markup=get_subscription_button())
    update_last_active(user_id)
    await callback.answer()

# ---------- СОЛЯР (тизер) ----------
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
    prompt = f"Дай короткий тизер соляра (2-3 предложения) для человека со знаком {zodiac} на предстоящий год. Добавь интригу и фразу: «Полный прогноз соляра на год – по подписке в разделе «Эксклюзив»»."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="solar", gender=gender)
    await status_msg.delete()
    await callback.message.answer(f"☀️ *Ваш соляр на год (тизер)*\n\n{response}", parse_mode="Markdown", reply_markup=get_subscription_button())
    update_last_active(user_id)
    await callback.answer()

# ---------- ГОРОСКОП НА ДЕНЬ (бесплатный, полный) ----------
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
            prompt = f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай развёрнутый прогноз (6-7 предложений) по 2 сферам (любовь и работа/деньги). Добавь совет на день."
            response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_daily", gender=gender)
            reply_markup = menu_button
        else:
            prompt = f"Составь астрологический гороскоп на сегодня ({today.strftime('%d.%m.%Y')}) для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай цепляющий прогноз (5-6 предложений): укажи, что важно сегодня, дай один совет, задай вопрос для размышления. В конце добавь фразу: «Полный гороскоп на месяц и ежедневные прогнозы – по подписке»."
            response = await get_yandex_gpt_response(prompt, user_id, function_name="horoscope_daily", gender=gender)
            reply_markup = get_subscription_button()
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, cache_key, response)
    await callback.message.answer(f"🌟 *Гороскоп на сегодня*\n\n{response}", parse_mode="Markdown", reply_markup=reply_markup)
    update_last_active(user_id)
    await callback.answer()