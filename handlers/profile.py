import datetime
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.enums import ChatType
from keyboards import profile_menu, main_menu, menu_button, cancel_button
from database import get_connection, get_user, update_user, get_subscription_status
from yandex_gpt import get_yandex_gpt_response
from utils import (
    generate_referral_link, get_referral_stats, get_free_questions_remaining,
    get_achievements, add_subscription_days, update_last_active,
    get_user_subscription_status, calculate_level,
    get_city_coords, get_timezone_by_coords, translate_timezone,
    format_subscription_remaining, get_bot_config, set_bot_config
)
from settings import LEVELS, PAYMENTS_TOKEN

router = Router()

MANUAL_TIMEZONES = {
    "стерлитамак": "Asia/Yekaterinburg",
    "екатеринбург": "Asia/Yekaterinburg",
    "челябинск": "Asia/Yekaterinburg",
    "тюмень": "Asia/Yekaterinburg",
    "уфа": "Asia/Yekaterinburg",
    "пермь": "Asia/Yekaterinburg",
    "самара": "Europe/Samara",
    "томск": "Asia/Novosibirsk",
    "новосибирск": "Asia/Novosibirsk",
    "красноярск": "Asia/Krasnoyarsk",
    "иркутск": "Asia/Irkutsk",
    "якутск": "Asia/Yakutsk",
    "владивосток": "Asia/Vladivostok",
    "хабаровск": "Asia/Vladivostok",
    "магадан": "Asia/Magadan",
    "петропавловск-камчатский": "Asia/Kamchatka",
    "калининград": "Europe/Kaliningrad",
    "казань": "Europe/Moscow",
    "нижний новгород": "Europe/Moscow",
    "ростов-на-дону": "Europe/Moscow",
    "волгоград": "Europe/Volgograd",
}

class UserStates(StatesGroup):
    waiting_new_name = State()
    waiting_phone = State()
    waiting_city = State()
    waiting_gift_username = State()
    waiting_birth_time = State()
    waiting_birth_place = State()

# ---------- ПРОФИЛЬ ----------
@router.message(F.text == "👤 МОЙ ПРОФИЛЬ")
async def show_profile(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Профиль доступен только в личном чате.")
        return
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, birth_date, destiny_number, subscription_active, subscription_end, phone, city, timezone, birth_time, birth_place FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        await message.answer("Нажмите /start", reply_markup=menu_button)
        return
    name = row[0] or "—"
    birth = row[1] or "—"
    destiny = row[2] or "?"
    sub_active = row[3]
    sub_end_raw = row[4] if row[4] else None
    remaining_str = format_subscription_remaining(sub_end_raw) if sub_end_raw else "—"
    end_date_str = sub_end_raw[:10] if sub_end_raw else "—"
    if sub_end_raw and len(sub_end_raw) >= 10:
        try:
            d = datetime.datetime.fromisoformat(sub_end_raw[:10])
            end_date_str = d.strftime("%d.%m.%Y")
        except:
            pass
    phone = row[5] if row[5] else "—"
    city = row[6] if row[6] else "—"
    birth_time = row[8] if row[8] else "—"
    birth_place = row[9] if row[9] else "—"
    remaining_q = get_free_questions_remaining(user_id)
    level, xp, next_xp = calculate_level(user_id)
    level_name = LEVELS.get(level, {}).get("name", "Новичок")
    progress = int((xp / next_xp) * 20) if next_xp > 0 else 0
    bar = "█" * progress + "░" * (20 - progress)
    text = (f"┌─────────────────────┐\n"
            f"│ 👤 Имя: {name}\n"
            f"│ 🎂 Дата: {birth}\n"
            f"│ 🕒 Время рождения: {birth_time}\n"
            f"│ 📍 Место: {birth_place}\n"
            f"│ 🔢 Число: {destiny}\n"
            f"│ 💳 Подписка: {'Активна' if sub_active else 'Неактивна'}\n"
            f"│ ⏳ {remaining_str}\n"
            f"│ 📅 До: {end_date_str}\n"
            f"│ 🎁 Бесплатных вопросов: {remaining_q}/5\n"
            f"│ 🏆 Уровень: {level} «{level_name}»\n"
            f"│ 📊 [{bar}] {xp}/{next_xp} XP\n"
            f"│ 📞 Телефон: {phone}\n"
            f"│ 🌍 Город: {city}\n"
            f"└─────────────────────┘")
    await message.answer(text, reply_markup=profile_menu)

# ---------- НАСТРОЙКИ ----------
@router.callback_query(F.data == "settings")
async def settings_menu(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "⚙️ *Настройки*\n\nВыберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Сменить имя", callback_data="change_name")],
            [InlineKeyboardButton(text="📱 Добавить/заменить телефон", callback_data="add_phone")],
            [InlineKeyboardButton(text="🌍 Добавить/заменить город", callback_data="add_city")],
            [InlineKeyboardButton(text="🕒 Указать время рождения", callback_data="add_birth_time")],
            [InlineKeyboardButton(text="📍 Указать место рождения", callback_data="add_birth_place")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
    )
    await callback.answer()

# ---------- СМЕНА ИМЕНИ ----------
@router.callback_query(F.data == "change_name")
async def change_name_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Введите новое имя (не менее 2 символов):",
        reply_markup=cancel_button()
    )
    await state.set_state(UserStates.waiting_new_name)
    await callback.answer()

@router.message(UserStates.waiting_new_name)
async def change_name_save(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_name = message.text.strip()
    if len(new_name) < 2:
        await message.answer("Имя должно быть не короче 2 символов.", reply_markup=cancel_button())
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
    conn.commit()
    conn.close()
    update_last_active(user_id)
    await message.answer(f"Имя изменено на {new_name}.", reply_markup=main_menu)
    await state.clear()

# ---------- РЕФЕРАЛЫ ----------
@router.callback_query(F.data == "referral_info")
async def referral_info(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    link = generate_referral_link(user_id)
    stats = get_referral_stats(user_id)
    text = (
        "🎁 *Реферальная программа*\n\n"
        "Отправьте другу ссылку. Как только друг оформит подписку, вы получите +7 дней полного доступа в подарок.\n\n"
        f"Ваша ссылка: {link}\n\n"
        f"Приведено друзей с подпиской: *{stats['paid']}*\n"
        f"Всего переходов: *{stats['total']}*\n\n"
        "Чем больше друзей, тем больше бонусных дней!"
    )
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=menu_button)
    await callback.answer()

# ---------- ДОСТИЖЕНИЯ ----------
@router.callback_query(F.data == "achievements")
async def show_achievements(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    achievements = get_achievements(user_id)
    if not achievements:
        text = "Пока нет достижений. Начните с расчёта числа судьбы!"
    else:
        text = "🏆 Ваши достижения:\n"
        for ach, date in achievements:
            text += f"• {ach} ({date[:10]})\n"
    await callback.message.answer(text, reply_markup=menu_button)
    await callback.answer()

# ---------- ТЕЛЕФОН ----------
@router.callback_query(F.data == "add_phone")
async def add_phone_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Отправьте ваш номер телефона, нажав на кнопку ниже. Если номер уже есть, он будет заменён.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Отправить номер", callback_data="request_phone")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "request_phone")
async def request_phone(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Пожалуйста, поделитесь номером телефона, нажав кнопку ниже.",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    await state.set_state(UserStates.waiting_phone)
    await callback.answer()

@router.message(UserStates.waiting_phone, F.contact)
async def save_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
    conn.commit()
    conn.close()
    await message.answer("Спасибо! Номер телефона сохранён (или обновлён).", reply_markup=main_menu)
    await state.clear()

# ---------- ГОРОД ----------
@router.callback_query(F.data == "add_city")
async def add_city_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Напишите название вашего города. Если город уже указан, он будет заменён.",
        reply_markup=cancel_button()
    )
    await state.set_state(UserStates.waiting_city)
    await callback.answer()

@router.message(UserStates.waiting_city)
async def process_city(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    city_input = message.text.strip()
    city_lower = city_input.lower()
    if len(city_input) < 2:
        await message.answer("Пожалуйста, введите корректное название города (не менее 2 символов).", reply_markup=cancel_button())
        return

    status_msg = await message.answer("🌍 Определяю местоположение и часовой пояс...")
    lat, lon = await get_city_coords(city_input)
    if lat and lon:
        manual_tz = None
        for key, tz in MANUAL_TIMEZONES.items():
            if key in city_lower:
                manual_tz = tz
                break
        if manual_tz:
            timezone_raw = manual_tz
        else:
            timezone_raw = await get_timezone_by_coords(lat, lon)
        timezone_ru = translate_timezone(timezone_raw)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET city = ?, timezone = ? WHERE user_id = ?", (city_input, timezone_raw, user_id))
        conn.commit()
        conn.close()
        await status_msg.edit_text(f"✅ Город *{city_input}* сохранён.\n🗓️ Часовой пояс: {timezone_ru}")
    else:
        await status_msg.edit_text("❌ Не удалось определить город. Попробуйте написать его на русском или английском языке более точно.")
    await state.clear()

# ---------- ВРЕМЯ РОЖДЕНИЯ ----------
@router.callback_query(F.data == "add_birth_time")
async def add_birth_time_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Введите время рождения в формате ЧЧ:ММ (например, 15:30). Если не знаете – напишите «неизвестно».",
        reply_markup=cancel_button()
    )
    await state.set_state(UserStates.waiting_birth_time)
    await callback.answer()

@router.message(UserStates.waiting_birth_time)
async def save_birth_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    time_str = message.text.strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET birth_time = ? WHERE user_id = ?", (time_str, user_id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Время рождения сохранено: {time_str}", reply_markup=main_menu)
    await state.clear()

# ---------- МЕСТО РОЖДЕНИЯ ----------
@router.callback_query(F.data == "add_birth_place")
async def add_birth_place_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Введите город и страну рождения (например, Москва, Россия).",
        reply_markup=cancel_button()
    )
    await state.set_state(UserStates.waiting_birth_place)
    await callback.answer()

@router.message(UserStates.waiting_birth_place)
async def save_birth_place(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    place = message.text.strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET birth_place = ? WHERE user_id = ?", (place, user_id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Место рождения сохранено: {place}", reply_markup=main_menu)
    await state.clear()

# ---------- ИСТОРИЯ ----------
@router.callback_query(F.data == "history")
async def show_history(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    from utils import get_dialog_history
    user_id = callback.from_user.id
    history = get_dialog_history(user_id, 10)
    if not history:
        text = "История пуста."
    else:
        text = "📜 *Последние 10 сообщений:*\n\n"
        for role, msg, ts in history:
            emoji = "👤" if role == "user" else "🤖"
            text += f"{ts[:16]} {emoji} {msg[:80]}\n"
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=menu_button)
    await callback.answer()

# ---------- ДОБАВИТЬ В ГРУППУ ----------
@router.callback_query(F.data == "add_to_group")
async def add_to_group_info(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    bot_username = (await callback.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?startgroup=start"
    text = (
        "👥 *Как добавить бота в групповой чат или канал:*\n\n"
        "1. Нажмите на ссылку ниже, чтобы добавить бота в ваш чат:\n"
        f"👉 [Добавить бота в группу]({invite_link})\n\n"
        "2. Бот будет работать как обычный участник – права администратора **не нужны**.\n"
        "3. После добавления просто напишите в чате команду `/startarkadiy` – и бот активируется.\n"
        "4. Бот будет присылать полезные мысли, психологические советы и поддержку (до 2 сообщений в час).\n"
        "5. Если захотите отключить – напишите в чате `/stoparkadiy`.\n\n"
        "Никаких сложных настроек не требуется. Всё работает автоматически."
    )
    await callback.message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
    await callback.answer()

# ---------- О БОТЕ ----------
@router.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    text = (
        "ℹ️ *О боте «Аркадий Викторович»*\n\n"
        "Я — ваш личный нумеролог, психолог и астролог. Вот что я умею:\n\n"
        "🧠 *Бесплатные возможности:*\n"
        "• 🔢 Ваше число судьбы и его характеристика\n"
        "• ❤️ Совместимость с партнёром\n"
        "• 🎁 Карта дня с прогнозом и погодой\n"
        "• 💬 5 бесплатных вопросов в день\n"
        "• 🧠 Психотест и дневник настроения\n"
        "• 🌟 Гороскоп на день\n\n"
        "💎 *Подписка (всего 249 ₽/мес) — это ваш ключ к полному доступу:*\n"
        "• 🔮 Полная матрица судьбы (22 аркана) с PDF-отчётом\n"
        "• 💬 Безлимитные вопросы с развёрнутыми ответами\n"
        "• 📅 Гороскоп на месяц и ежедневные прогнозы\n"
        "• 🌌 Натальная карта, транзиты и соляр\n"
        "• 💸 Денежный код – персональная стратегия увеличения дохода\n"
        "• 📊 Персональные психологические рекомендации\n"
        "• 🔔 Ежедневные мотивирующие фразы и аффирмации\n"
        "• 🎁 Приоритетная поддержка\n\n"
        "💰 *Почему это выгодно?*\n"
        "• Всего 249 ₽ — цена одной чашки кофе, но вы получаете целый месяц профессиональных консультаций.\n"
        "• Вы экономите время и деньги на походах к психологам и астрологам.\n"
        "• Каждый день — новые инсайты и практики для улучшения жизни.\n\n"
        "👥 *Для групповых чатов:*\n"
        "• Активация: /startarkadiy\n"
        "• Деактивация: /stoparkadiy\n"
        "• Бот автоматически делится полезными мыслями и поддержкой.\n\n"
        "📌 *Управление ботом — только через кнопки меню!*"
        "\n\n👤 *Поддержка:* @Aristocrat102\n"
        "Версия бота: 2.1.0"
    )
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=menu_button)
    await callback.answer()

# ---------- КУПИТЬ ПОДПИСКУ ----------
@router.callback_query(F.data == "buy_subscription")
async def buy_subscription(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    price_rub = int(get_bot_config("subscription_price_rub", "249"))
    stars = int(price_rub * 2)
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Подписка на бота «Аркадий Викторович»",
        description=f"Месяц полного доступа: матрица судьбы, безлимитные вопросы, прогнозы. Цена: {price_rub} ₽ (≈ {stars} Stars)",
        payload="subscription_month",
        provider_token=PAYMENTS_TOKEN,
        currency="XTR",
        prices=[LabeledPrice(label="Месяц", amount=stars)],
        start_parameter="subscription"
    )
    await callback.answer()

# ---------- ПОДАРОК ПОДПИСКИ ----------
@router.callback_query(F.data == "gift_subscription")
async def gift_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Введите @username друга, которому хотите подарить подписку (без @):",
        reply_markup=cancel_button()
    )
    await state.set_state(UserStates.waiting_gift_username)
    await callback.answer()

@router.message(UserStates.waiting_gift_username)
async def gift_process(message: types.Message, state: FSMContext):
    username = message.text.strip().lstrip('@')
    try:
        chat = await message.bot.get_chat(f"@{username}")
        gifted_user_id = chat.id
    except Exception:
        await message.answer(f"❌ Не удалось найти пользователя @{username}. Проверьте правильность написания.", reply_markup=cancel_button())
        await state.clear()
        return
    price_rub = int(get_bot_config("subscription_price_rub", "249"))
    stars = int(price_rub * 2)
    await message.bot.send_invoice(
        chat_id=message.from_user.id,
        title=f"Подарочная подписка для @{username}",
        description=f"Вы дарите месяц подписки пользователю @{username}. Цена: {price_rub} ₽ (≈ {stars} Stars)",
        payload=f"gift_{gifted_user_id}",
        provider_token=PAYMENTS_TOKEN,
        currency="XTR",
        prices=[LabeledPrice(label="Месяц в подарок", amount=stars)],
        start_parameter="gift"
    )
    await state.clear()

@router.callback_query(F.data == "renew_subscription")
async def renew_subscription(callback: types.CallbackQuery):
    await buy_subscription(callback)

# ---------- ОПЛАТА ----------
@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("gift_"):
        gifted_user_id = int(payload.split("_")[1])
        add_subscription_days(gifted_user_id, 30, check_referral=False, admin_id=0)
        await message.bot.send_message(gifted_user_id, "🎁 *Вам подарили месяц подписки!*\n\nТеперь вам доступны: матрица судьбы, безлимитные вопросы, прогнозы, гороскопы и психологические практики. Спасибо вашему другу!", parse_mode="Markdown")
        await message.answer("✅ Подарок отправлен! Спасибо за доверие.")
    else:
        add_subscription_days(message.from_user.id, 30, check_referral=False, admin_id=0)
        await message.answer("✅ Подписка активирована на 30 дней! Теперь вам доступны матрица судьбы, безлимитные вопросы и все премиум-функции. Спасибо, что с нами!")

# ---------- ДЕНЕЖНЫЙ КОД (только по подписке) ----------
@router.callback_query(F.data == "money_code")
async def money_code(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    if not get_user_subscription_status(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить подписку", callback_data="buy_subscription")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        await callback.message.answer(
            "💸 *Денежный код*\n\n"
            "Это эксклюзивная функция, доступная только по подписке.\n"
            "Вы получите:\n"
            "• Ваш личный денежный код (по дате рождения и имени)\n"
            "• Стратегию увеличения дохода\n"
            "• Благоприятные периоды для инвестиций и крупных покупок\n"
            "• Советы по управлению финансами\n\n"
            "Оформите подписку, чтобы открыть этот раздел!",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await callback.answer()
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, birth_date, destiny_number FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[1]:
        await callback.message.answer("Сначала укажите дату рождения в профиле.", reply_markup=menu_button)
        await callback.answer()
        return
    name = row[0] or "пользователь"
    birth_date = row[1]
    destiny = row[2] or "?"

    status_msg = await callback.message.answer("💸 Аркадий Викторович рассчитывает ваш денежный код...")
    prompt = f"Рассчитай денежный код для человека {name} с датой рождения {birth_date} и числом судьбы {destiny}. Дай развёрнутый ответ (8-10 предложений): что такое денежный код, как его использовать, конкретные рекомендации по улучшению финансового потока, благоприятные дни для денежных операций."
    response = await get_yandex_gpt_response(prompt, user_id)
    await status_msg.delete()
    await callback.message.answer(f"💸 *Ваш денежный код*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
    await callback.answer()

# ---------- КОМАНДЫ ДЛЯ ПОДПИСКИ НА РАССЫЛКУ ----------
@router.message(Command("unsubscribe_daily"))
async def unsubscribe_daily(message: types.Message):
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET send_daily = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await message.answer("Вы отписались от ежедневной рассылки карты дня и гороскопа.", reply_markup=menu_button)

@router.message(Command("subscribe_daily"))
async def subscribe_daily(message: types.Message):
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET send_daily = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await message.answer("Вы подписались на ежедневную рассылку карты дня и гороскопа.", reply_markup=menu_button)