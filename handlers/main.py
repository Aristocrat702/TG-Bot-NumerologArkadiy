import datetime
import asyncio
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import main_menu, quick_topics_menu, menu_button, cancel_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    get_user_subscription_status,
    get_free_questions_remaining,
    increment_free_query,
    get_cached_response,
    save_cached_response,
    add_xp,
    update_last_active,
    calculate_destiny_number,
    get_city_coords,
    get_weather_by_coords,
    get_dialog_history,
    get_zodiac_sign,
    get_user_gender
)
from utils.notifications import get_subscription_button

router = Router()

class MainStates(StatesGroup):
    waiting_birth_date = State()
    waiting_partner_birth_date = State()
    waiting_question = State()

last_answer = {}
pending_matrix = {}

# ---------- МОЁ ЧИСЛО ----------
@router.message(F.text == "🔢 МОЁ ЧИСЛО")
async def show_my_number(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта функция доступна только в личном чате.")
        return
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date, destiny_number, name FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await message.answer("Сначала введите дату рождения через /start.")
        return
    destiny = row[1]
    is_subscriber = get_user_subscription_status(user_id)
    gender = get_user_gender(user_id)
    cached = get_cached_response(user_id, f"birth_{destiny}_{'sub' if is_subscriber else 'free'}")
    if cached:
        response = cached
        reply_markup = None if is_subscriber else get_subscription_button()
    else:
        status_msg = await message.answer("🧐 Аркадий Викторович изучает ваш гороскоп...")
        # Получаем промпты из БД
        from database import get_prompts_for_function
        prompts = get_prompts_for_function("number")
        if is_subscriber:
            prompt_template = prompts["paid"] if prompts else "Число судьбы: %s. Дай развёрнутую характеристику (6-8 предложений): сильные стороны, слабости, ключевой жизненный вызов, совет по самореализации. Будь прямолинеен, но с теплотой."
            prompt = prompt_template % destiny
            response = await get_yandex_gpt_response(prompt, user_id, function_name="number", gender=gender)
            reply_markup = None
        else:
            prompt_template = prompts["free"] if prompts else "Число судьбы: %s. Дай характеристику (5-6 предложений): укажи 2 сильные стороны, 1 слабость, 1 главную задачу в жизни. В конце добавь фразу: «Хотите узнать, как это число влияет на ваши отношения, карьеру и деньги? Полный разбор – по подписке»."
            prompt = prompt_template % destiny
            response = await get_yandex_gpt_response(prompt, user_id, function_name="number", gender=gender)
            reply_markup = get_subscription_button()
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, f"birth_{destiny}_{'sub' if is_subscriber else 'free'}", response)
    add_xp(user_id, "daily_visit")
    await message.answer(
        f"🔢 Ваше число судьбы: {destiny}\n\n{response}",
        reply_markup=reply_markup or quick_topics_menu,
        parse_mode="HTML"
    )

# ---------- СКАЧАТЬ PDF (заглушка) ----------
@router.callback_query(F.data == "download_pdf")
async def download_pdf(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer("PDF-отчёт доступен только по подписке в разделе «Эксклюзив».")
    await callback.answer()

# ---------- СОВМЕСТИМОСТЬ ----------
@router.message(F.text == "❤️ СОВМЕСТИМОСТЬ")
async def ask_partner_birth(message: types.Message, state: FSMContext):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта функция доступна только в личном чате.")
        return
    await message.answer(
        "Введите дату рождения партнёра в формате ДД.ММ.ГГГГ",
        reply_markup=cancel_button()
    )
    await state.set_state(MainStates.waiting_partner_birth_date)

@router.message(MainStates.waiting_partner_birth_date)
async def process_compatibility(message: types.Message, state: FSMContext):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта функция доступна только в личном чате.")
        await state.clear()
        return
    user_id = message.from_user.id
    partner_text = message.text.strip()
    try:
        day, month, year = map(int, partner_text.split('.'))
        partner_birth = f"{day:02d}.{month:02d}.{year:04d}"
        partner_destiny = calculate_destiny_number(partner_birth)
        partner_zodiac = get_zodiac_sign(partner_birth)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, birth_date FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала укажите свою дату рождения через кнопку «Моё число».", reply_markup=menu_button)
            await state.clear()
            return
        my_destiny = row[0]
        my_birth = row[1]
        my_zodiac = get_zodiac_sign(my_birth) if my_birth else "неизвестен"
        is_subscriber = get_user_subscription_status(user_id)
        gender = get_user_gender(user_id)

        status_msg = await message.answer("🔍 Анализирую совместимость...")
        from database import get_prompts_for_function
        prompts = get_prompts_for_function("compatibility")
        if is_subscriber:
            prompt_template = prompts["paid"] if prompts else "Число судьбы пользователя %s (знак %s), число партнёра %s (знак %s). Опиши совместимость развёрнуто (10-12 предложений) по 5 сферам: любовь, дружба, деньги, секс, интеллект. Дай рекомендации, как улучшить отношения. Будь честен и практичен."
            prompt = prompt_template % (my_destiny, my_zodiac, partner_destiny, partner_zodiac)
            response = await get_yandex_gpt_response(prompt, user_id, function_name="compatibility", gender=gender)
            reply_markup = menu_button
        else:
            prompt_template = prompts["free"] if prompts else "Число судьбы пользователя %s (знак %s), число партнёра %s (знак %s). Дай краткое описание совместимости (4-5 предложений). Напиши, что их связывает, что будет сложно, и дай один совет. В конце добавь фразу: «Полный разбор по 5 сферам с рекомендациями – по подписке»."
            prompt = prompt_template % (my_destiny, my_zodiac, partner_destiny, partner_zodiac)
            response = await get_yandex_gpt_response(prompt, user_id, function_name="compatibility", gender=gender)
            reply_markup = get_subscription_button()
        await status_msg.delete()
        last_answer[user_id] = response
        await message.answer(
            f"❤️ Совместимость\n\n{response}",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        await state.clear()
    except Exception:
        await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ", reply_markup=cancel_button())

# ---------- КАРТА ДНЯ ----------
@router.message(F.text == "🎁 КАРТА ДНЯ")
async def daily_card(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта функция доступна только в личном чате.")
        return
    user_id = message.from_user.id
    is_subscriber = get_user_subscription_status(user_id)
    gender = get_user_gender(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT destiny_number, city FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    destiny = row[0] if row else "?"
    city = row[1] if row and row[1] else None
    
    weather_str = ""
    if city:
        lat, lon = await get_city_coords(city)
        if lat and lon:
            weather_str = await get_weather_by_coords(lat, lon)
            if weather_str and "Не удалось" not in weather_str and "Ошибка" not in weather_str:
                weather_str = f"\n\n🌤️ Погода в {city}: {weather_str}"
            else:
                weather_str = ""
    
    status_msg = await message.answer("🌙 Аркадий Викторович заглядывает в будущее...")
    from database import get_prompts_for_function
    prompts = get_prompts_for_function("daily_card")
    if is_subscriber:
        prompt_template = prompts["paid"] if prompts else "Сегодняшняя карта дня для числа судьбы %s. Дай развёрнутый прогноз (6-8 предложений): общий настрой, практическое действие, психологическая практика, вопрос для рефлексии."
        prompt = prompt_template % destiny
        response = await get_yandex_gpt_response(prompt, user_id, function_name="daily_card", gender=gender)
        reply_markup = menu_button
    else:
        prompt_template = prompts["free"] if prompts else "Сегодняшняя карта дня для числа судьбы %s. Дай краткий прогноз (5-6 предложений): что важно сегодня, один практический совет, вопрос, чтобы задуматься. В конце добавь фразу: «Полная карта дня с практиками и погодой – по подписке»."
        prompt = prompt_template % destiny
        response = await get_yandex_gpt_response(prompt, user_id, function_name="daily_card", gender=gender)
        reply_markup = get_subscription_button()
    await status_msg.delete()
    last_answer[user_id] = response
    await message.answer(
        f"🎁 Карта дня\n\n{response}{weather_str}",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# ---------- КОНСУЛЬТАЦИЯ (бывшая "ЗАДАТЬ ВОПРОС") ----------
@router.message(F.text == "💬 КОНСУЛЬТАЦИЯ")
async def ask_consultation(message: types.Message, state: FSMContext):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта функция доступна только в личном чате.")
        return
    user_id = message.from_user.id
    is_subscriber = get_user_subscription_status(user_id)
    
    text = (
        "💬 Консультация с Аркадием Викторовичем\n\n"
        "Вы можете задать вопрос по следующим темам:\n"
        "• 🔢 Нумерология – числа судьбы, матрица, совместимость\n"
        "• 🧠 Психология – отношения, самооценка, мотивация, стресс\n"
        "• 🌟 Астрология – гороскопы, натальная карта, транзиты\n"
        "• 🧠 Сексология – интимная жизнь, совместимость, желания\n\n"
        "Опишите вашу ситуацию максимально подробно – и я дам развёрнутый ответ.\n\n"
    )
    if is_subscriber:
        text += "💎 Вы подписчик – вопросы безлимитны. Можете задавать сколько угодно."
        reply_markup = cancel_button()
    else:
        remaining = get_free_questions_remaining(user_id)
        text += f"🎁 У вас осталось {remaining} бесплатных вопросов на сегодня.\n"
        text += "Оформите подписку (249 ₽/мес) для безлимитных консультаций."
        reply_markup = cancel_button()
    
    await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    await state.set_state(MainStates.waiting_question)

@router.message(MainStates.waiting_question)
async def process_consultation(message: types.Message, state: FSMContext):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        await state.clear()
        return
    user_id = message.from_user.id
    question = message.text
    gender = get_user_gender(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    destiny = row[0] if row else "?"
    name = row[1] if row else "друг"

    is_subscriber = get_user_subscription_status(user_id)
    
    # Проверка на нецелевой вопрос
    allowed_keywords = ["число", "судьба", "матрица", "совместимость", "гороскоп", "натальный", "транзит", "соляр",
                        "психолог", "отношения", "самооценка", "мотивация", "стресс", "тревога", "депрессия",
                        "астролог", "знак зодиака", "планета", "секс", "интим", "влюбленность", "брак", "дружба",
                        "денежный код", "удача", "успех", "карьера", "финансы"]
    if len(question) < 5 or not any(word in question.lower() for word in allowed_keywords):
        await message.answer(
            "🧐 Друг мой, я специализируюсь на нумерологии, психологии, астрологии и сексологии. "
            "Похоже, ваш вопрос не относится к этим темам. Пожалуйста, уточните, что вас интересует в рамках этих направлений.",
            reply_markup=menu_button
        )
        await state.clear()
        return

    status_msg = await message.answer("🧐 Изучаю ваш вопрос...")
    from database import get_prompts_for_function
    prompts = get_prompts_for_function("consultation")
    if is_subscriber:
        prompt_template = prompts["paid"] if prompts else "Человек с числом судьбы %s по имени %s спрашивает: %s. Ответь развёрнуто, как психолог, нумеролог, астролог и сексолог (если уместно), с практическими советами. Используй стиль Аркадия Викторовича."
        prompt = prompt_template % (destiny, name, question)
        response = await get_yandex_gpt_response(prompt, user_id, function_name="consultation", gender=gender)
        await status_msg.delete()
        add_xp(user_id, "ask_question")
        await message.answer(
            response,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="ask_another_question")]
            ])
        )
        await state.clear()
        return

    remaining = get_free_questions_remaining(user_id)
    if remaining <= 0:
        await status_msg.delete()
        await message.answer("Лимит бесплатных вопросов на сегодня исчерпан. Оформите подписку в профиле.", reply_markup=menu_button)
        await state.clear()
        return

    prompt_template = prompts["free"] if prompts else "Человек с числом судьбы %s спрашивает: %s. Дай очень короткий ответ (1-2 предложения), который даст чёткое понимание, но не раскрывай всех деталей. В конце добавь фразу: «Полный разбор и советы – по подписке»."
    prompt = prompt_template % (destiny, question)
    short_response = await get_yandex_gpt_response(prompt, user_id, function_name="consultation", gender=gender)
    increment_free_query(user_id)
    await status_msg.delete()
    await message.answer(
        f"🔮 {short_response}\n\nУ вас осталось {remaining-1} бесплатных вопросов на сегодня. Хотите безлимит? Оформите подписку в профиле.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="ask_another_question")]
        ])
    )
    await state.clear()

# ---------- КНОПКА "ЕЩЁ ВОПРОС" ----------
@router.callback_query(F.data == "ask_another_question")
async def ask_another_question(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await ask_consultation(callback.message, state)
    await callback.answer()

# ---------- БЫСТРЫЕ ТЕМЫ ----------
@router.callback_query(F.data.startswith("quick_topic_"))
async def quick_topic(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    topic = callback.data.split("_")[-1]
    gender = get_user_gender(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    destiny = row[0] if row else "?"
    is_subscriber = get_user_subscription_status(user_id)
    if is_subscriber:
        prompt = f"Человек с числом судьбы {destiny} спрашивает про {topic}. Дай развёрнутый ответ (5-7 предложений) с практическими советами."
        response = await get_yandex_gpt_response(prompt, user_id, function_name="quick_topic", gender=gender)
        reply_markup = menu_button
    else:
        prompt = f"Человек с числом судьбы {destiny} спрашивает про {topic}. Дай краткий ответ (3-4 предложения) с основной сутью. В конце добавь фразу: «Углублённый разбор и стратегии – по подписке»."
        response = await get_yandex_gpt_response(prompt, user_id, function_name="quick_topic", gender=gender)
        reply_markup = get_subscription_button()
    status_msg = await callback.message.answer("🔮 Аркадий Викторович размышляет...")
    await status_msg.delete()
    await callback.message.answer(
        f"📌 {topic.capitalize()}\n\n{response}",
        parse_mode="HTML",
        reply_markup=reply_markup or menu_button
    )
    await callback.answer()

# ---------- КОМАНДА /MYNUMBER ----------
@router.message(Command("mynumber"))
async def mynumber_command(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта команда доступна только в личном чате.")
        return
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        await message.answer("Сначала введите дату рождения через /start или кнопку «Моё число».")
        return
    destiny = row[0]
    await message.answer(
        f"Ваше число судьбы: {destiny}. Хотите подробнее? Нажмите «Моё число» в меню.",
        parse_mode="HTML"
    )