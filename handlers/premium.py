import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.enums import ChatType
from keyboards import premium_submenu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, get_cached_response, save_cached_response, get_zodiac_sign, update_last_active
# Импорт PDF временно закомментирован, чтобы не было ошибки
# from utils.pdf import generate_pdf_matrix

router = Router()

@router.message(F.text == "💎 ЭКСКЛЮЗИВ")
async def premium_menu(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        return
    await message.answer(
        "💎 *Эксклюзивные функции*\n\n"
        "Здесь собраны все возможности, доступные только по подписке:\n"
        "• 🔮 Полная матрица судьбы (22 аркана) с глубоким разбором\n"
        "• 💸 Денежный код – стратегия увеличения дохода\n"
        "• 🌌 Полная натальная карта\n"
        "• ☀️ Соляр\n"
        "• 📆 Гороскоп на месяц\n\n"
        "Оформите подписку, чтобы открыть все функции!",
        parse_mode="Markdown",
        reply_markup=premium_submenu
    )

async def check_subscription_and_redirect(callback: types.CallbackQuery, function_name: str):
    user_id = callback.from_user.id
    if not get_user_subscription_status(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить подписку", callback_data="buy_subscription")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        await callback.message.answer(
            f"❌ Эта функция доступна только по подписке.\n"
            f"Оформите подписку, чтобы получить доступ к {function_name}.",
            reply_markup=kb
        )
        await callback.answer()
        return False
    return True

@router.callback_query(F.data == "premium_matrix")
async def premium_matrix(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    if not await check_subscription_and_redirect(callback, "матрице судьбы"):
        return
    user_id = callback.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT destiny_number, name, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения через кнопку «Моё число».", reply_markup=menu_button)
        await callback.answer()
        return
    destiny = row[0]
    name = row[1] if row[1] else "пользователь"
    gender = row[2] if row[2] else "unknown"
    cache_key = f"matrix_{destiny}"
    cached = get_cached_response(user_id, cache_key)
    if cached:
        response = cached
        await callback.message.answer(f"🔮 *Матрица судьбы*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        await callback.answer()
        return
    status_msg = await callback.message.answer("📜 Аркадий Викторович составляет вашу матрицу... Это может занять до 2 минут.")
    # Усиленный промпт для матрицы
    prompt = f"Составь полную матрицу судьбы для числа {destiny}. Опиши 22 аркана (каждый 1-2 предложения). В конце дай: 1. Твою главную жизненную задачу. 2. Три конкретных шага, которые помогут её реализовать. 3. Самый сильный твой талант и как его применить. Ответ должен быть глубоким, практичным и персонализированным. Учти, что пользователь — {gender} с именем {name}."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_matrix")
    await status_msg.delete()
    if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
        save_cached_response(user_id, cache_key, response)
    # Кнопка PDF убрана – информация выводится только в чате
    await callback.message.answer(f"🔮 *Матрица судьбы*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
    update_last_active(user_id)
    await callback.answer()

@router.callback_query(F.data == "premium_money_code")
async def premium_money_code(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    if not await check_subscription_and_redirect(callback, "денежному коду"):
        return
    user_id = callback.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, birth_date, destiny_number, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[1]:
        await callback.message.answer("Сначала укажите дату рождения в профиле.", reply_markup=menu_button)
        await callback.answer()
        return
    name = row[0] or "пользователь"
    birth_date = row[1]
    destiny = row[2] or "?"
    gender = row[3] if row[3] else "unknown"
    status_msg = await callback.message.answer("💸 Аркадий Викторович рассчитывает ваш денежный код...")
    prompt = f"Рассчитай денежный код для человека {name} с датой рождения {birth_date} и числом судьбы {destiny}. Дай развёрнутый ответ (10-12 предложений): что такое денежный код, как его использовать, конкретные рекомендации по улучшению финансового потока, благоприятные дни для денежных операций. Учти пол пользователя ({gender})."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_money_code")
    await status_msg.delete()
    await callback.message.answer(f"💸 *Ваш денежный код*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
    update_last_active(user_id)
    await callback.answer()

@router.callback_query(F.data == "premium_natal")
async def premium_natal(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    if not await check_subscription_and_redirect(callback, "полной натальной карте"):
        return
    user_id = callback.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date, birth_time, birth_place, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения в профиле (настройки).", reply_markup=menu_button)
        await callback.answer()
        return
    birth_date = row[0]
    birth_time = row[1] if row[1] else "неизвестно"
    birth_place = row[2] if row[2] else "не указано"
    gender = row[3] if row[3] else "unknown"
    status_msg = await callback.message.answer("🌌 Аркадий Викторович строит вашу натальную карту...")
    prompt = f"Составь полное описание натальной карты для человека, родившегося {birth_date} в {birth_time} в {birth_place}. Укажи основные планеты, дома, аспекты. Дай развёрнутый, содержательный прогноз (12-15 предложений). Опиши влияние каждой планеты на характер, отношения, карьеру. Дай практические советы, как использовать сильные стороны. Учти пол ({gender})."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_natal")
    await status_msg.delete()
    await callback.message.answer(f"🌌 *Ваша натальная карта*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
    update_last_active(user_id)
    await callback.answer()

@router.callback_query(F.data == "premium_solar")
async def premium_solar(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    if not await check_subscription_and_redirect(callback, "соляру"):
        return
    user_id = callback.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения в профиле.", reply_markup=menu_button)
        await callback.answer()
        return
    birth_date = row[0]
    gender = row[1] if row[1] else "unknown"
    zodiac = get_zodiac_sign(birth_date)
    status_msg = await callback.message.answer("☀️ Аркадий Викторович рассчитывает соляр...")
    prompt = f"Составь прогноз соляра для человека со знаком {zodiac} на предстоящий год. Укажи ключевые события по месяцам, периоды роста и возможные трудности. Дай развёрнутый ответ (12-15 предложений). Что важно сделать в первый месяц после дня рождения? Где ждать успеха, где осторожность. Учти пол ({gender})."
    response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_solar")
    await status_msg.delete()
    await callback.message.answer(f"☀️ *Ваш соляр на год*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
    update_last_active(user_id)
    await callback.answer()

@router.callback_query(F.data == "premium_horoscope_monthly")
async def premium_horoscope_monthly(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    if not await check_subscription_and_redirect(callback, "гороскопу на месяц"):
        return
    user_id = callback.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date, destiny_number, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения через /start или /mynumber.", reply_markup=menu_button)
        await callback.answer()
        return
    birth_date = row[0]
    destiny = row[1] if row[1] else "?"
    gender = row[2] if row[2] else "unknown"
    zodiac = get_zodiac_sign(birth_date)
    today = datetime.date.today()
    target_date = today.strftime("%Y-%m")
    cache_key = f"horoscope_monthly_{target_date}_{user_id}"
    cached = get_cached_response(user_id, cache_key)
    if cached:
        response = cached
    else:
        month_name = today.strftime('%B').lower()
        prompt = f"Составь астрологический гороскоп на месяц {month_name} для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай развёрнутый прогноз (12-15 предложений) по сферам: любовь, деньги, здоровье, карьера. Укажи благоприятные периоды по датам, дай конкретные рекомендации на каждый период. Учти пол ({gender})."
        status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
        response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_horoscope_monthly")
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, cache_key, response)
    await callback.message.answer(f"🌟 *Гороскоп на месяц*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
    update_last_active(user_id)
    await callback.answer()