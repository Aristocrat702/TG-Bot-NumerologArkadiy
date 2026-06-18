import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import premium_submenu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, get_cached_response, save_cached_response, get_zodiac_sign, update_last_active

router = Router()

@router.message(F.text == "💎 ЭКСКЛЮЗИВ")
async def premium_menu(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        return
    await message.answer(
        "💎 *Эксклюзивные функции*\n\n"
        "Здесь собраны все возможности, доступные только по подписке:\n"
        "• 🔮 Полная матрица судьбы (22 аркана) – твой жизненный код\n"
        "• 💸 Денежный код – стратегия увеличения дохода\n"
        "• 🌌 Полная натальная карта – все планеты и дома\n"
        "• ☀️ Соляр – прогноз на год\n"
        "• 📆 Гороскоп на месяц – детальный разбор\n\n"
        "Оформите подписку, чтобы открыть все функции!",
        parse_mode="HTML",
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
    cursor.execute("SELECT destiny_number, name, gender, birth_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения через кнопку «Моё число».", reply_markup=menu_button)
        await callback.answer()
        return
    destiny = row[0]
    name = row[1] if row[1] else "пользователь"
    gender = row[2] if row[2] else "unknown"
    birth_date = row[3] if row[3] else "неизвестно"
    cache_key = f"matrix_{destiny}_{name}"
    cached = get_cached_response(user_id, cache_key)
    if cached:
        response = cached
    else:
        status_msg = await callback.message.answer("📜 Аркадий Викторович составляет вашу матрицу... Это может занять до 2 минут.")
        prompt = (
            f"Составь полную матрицу судьбы для человека с числом {destiny}, именем {name}, полом {gender}, датой рождения {birth_date}.\n\n"
            "Опиши 22 аркана (каждый в 1 предложении, кратко и ёмко).\n"
            "Затем дай:\n"
            "1. <b>Главную жизненную задачу</b> этого человека (одна фраза).\n"
            "2. <b>Три конкретных шага</b>, которые помогут реализовать эту задачу в ближайшие 30 дней.\n"
            "3. <b>Самый сильный талант</b> человека и как его применить прямо сейчас.\n"
            "4. <b>Один главный совет на год</b>.\n\n"
            "Сделай ответ глубоким, практичным, без общих фраз. Говори уверенно, как эксперт. "
            "Используй HTML-теги для форматирования: <b>жирный</b>, <i>курсив</i>, эмодзи для разделения блоков.\n"
            "Никаких дисклеймеров, никаких «нумерология не наука». Ты даёшь рабочий инструмент."
        )
        response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_matrix")
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, cache_key, response)
    # Отправляем только текст, без PDF
    await callback.message.answer(
        f"🔮 <b>Матрица судьбы</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=menu_button
    )
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
    prompt = (
        f"Рассчитай денежный код для {name} (число судьбы {destiny}, дата рождения {birth_date}, пол {gender}).\n\n"
        "Ответ должен содержать:\n"
        "1. <b>Что такое денежный код</b> и как он работает (2 предложения).\n"
        "2. <b>Конкретные числа и даты</b> для финансовых действий в этом месяце (минимум 3 даты).\n"
        "3. <b>Ритуал или практику</b>, которая усиливает денежный поток.\n"
        "4. <b>Главный совет по деньгам</b> на ближайшие 30 дней.\n\n"
        "Подавай это как рабочий инструмент, без сомнений. Ты уверен в своих знаниях. "
        "Используй HTML-форматирование. Никаких дисклеймеров."
    )
    response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_money_code")
    await status_msg.delete()
    await callback.message.answer(
        f"💸 <b>Ваш денежный код</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=menu_button
    )
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
    cursor.execute("SELECT birth_date, birth_time, birth_place, name, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения в профиле (настройки).", reply_markup=menu_button)
        await callback.answer()
        return
    birth_date = row[0]
    birth_time = row[1] if row[1] else "неизвестно"
    birth_place = row[2] if row[2] else "не указано"
    name = row[3] if row[3] else "пользователь"
    gender = row[4] if row[4] else "unknown"
    status_msg = await callback.message.answer("🌌 Аркадий Викторович строит вашу натальную карту...")
    prompt = (
        f"Составь полное описание натальной карты для человека {name} (пол {gender}), родившегося {birth_date} в {birth_time} в {birth_place}.\n\n"
        "Опиши:\n"
        "• <b>Планеты в домах</b> – влияние на характер, отношения, карьеру (по 1 предложению на планету).\n"
        "• <b>Сильные аспекты</b> – что даёт суперсилу.\n"
        "• <b>Слабые аспекты</b> – что требует внимания.\n"
        "• <b>Стратегию</b> на ближайший месяц: на чём сосредоточиться, от чего отказаться.\n\n"
        "Сделай ответ глубоким, практичным, без общих фраз. Используй HTML-форматирование."
    )
    response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_natal")
    await status_msg.delete()
    await callback.message.answer(
        f"🌌 <b>Ваша натальная карта</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=menu_button
    )
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
    cursor.execute("SELECT birth_date, name, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения в профиле.", reply_markup=menu_button)
        await callback.answer()
        return
    birth_date = row[0]
    name = row[1] if row[1] else "пользователь"
    gender = row[2] if row[2] else "unknown"
    zodiac = get_zodiac_sign(birth_date)
    status_msg = await callback.message.answer("☀️ Аркадий Викторович рассчитывает соляр...")
    prompt = (
        f"Составь прогноз соляра для человека {name} (пол {gender}) со знаком {zodiac}, родившегося {birth_date}.\n\n"
        "Дай развёрнутый ответ (10-12 предложений):\n"
        "• <b>Ключевые события по месяцам</b> (минимум 4 месяца).\n"
        "• <b>Что важно сделать в первый месяц</b> после дня рождения.\n"
        "• <b>Где ждать успеха, а где осторожность</b>.\n"
        "• <b>Главная задача года</b> (одна фраза).\n\n"
        "Используй HTML-форматирование. Говори уверенно, как эксперт."
    )
    response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_solar")
    await status_msg.delete()
    await callback.message.answer(
        f"☀️ <b>Ваш соляр на год</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=menu_button
    )
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
    cursor.execute("SELECT birth_date, destiny_number, name, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await callback.message.answer("Сначала укажите дату рождения через /start или /mynumber.", reply_markup=menu_button)
        await callback.answer()
        return
    birth_date = row[0]
    destiny = row[1] if row[1] else "?"
    name = row[2] if row[2] else "пользователь"
    gender = row[3] if row[3] else "unknown"
    zodiac = get_zodiac_sign(birth_date)
    today = datetime.date.today()
    target_date = today.strftime("%Y-%m")
    cache_key = f"horoscope_monthly_{target_date}_{user_id}"
    cached = get_cached_response(user_id, cache_key)
    if cached:
        response = cached
    else:
        month_name = today.strftime('%B').lower()
        status_msg = await callback.message.answer("🔮 Аркадий Викторович составляет гороскоп...")
        prompt = (
            f"Составь астрологический гороскоп на месяц {month_name} для человека {name} (пол {gender}) с числом судьбы {destiny} и знаком зодиака {zodiac}.\n\n"
            "Дай развёрнутый прогноз (10-12 предложений):\n"
            "• <b>Календарь рекомендаций</b> – укажи благоприятные даты для разных сфер (любовь, деньги, здоровье).\n"
            "• <b>Совет по любви</b> (2 предложения).\n"
            "• <b>Совет по деньгам</b> (2 предложения).\n"
            "• <b>Совет по здоровью</b> (2 предложения).\n"
            "• <b>Итоговая фраза</b>, которая задаёт тон месяцу.\n\n"
            "Используй HTML-форматирование. Будь практичен и конкретен."
        )
        response = await get_yandex_gpt_response(prompt, user_id, function_name="premium_horoscope_monthly")
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, cache_key, response)
    await callback.message.answer(
        f"🌟 <b>Гороскоп на месяц</b>\n\n{response}",
        parse_mode="HTML",
        reply_markup=menu_button
    )
    update_last_active(user_id)
    await callback.answer()