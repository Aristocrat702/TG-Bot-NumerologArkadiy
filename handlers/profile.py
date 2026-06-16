import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from keyboards import profile_menu, main_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    generate_referral_link, get_referral_stats, get_free_questions_remaining,
    get_achievements, add_subscription_days, update_last_active,
    get_user_subscription_status, calculate_level,
    get_city_coords, get_timezone_by_coords, translate_timezone,
    format_subscription_remaining
)
from settings import LEVELS, PAYMENTS_TOKEN

# Ручная корректировка часовых поясов
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
    waiting_new_phone = State()
    waiting_new_city = State()

def register_profile_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "👤 МОЙ ПРОФИЛЬ")
    async def show_profile(message: types.Message):
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
        phone = row[5] if row[5] else "—"
        city = row[6] if row[6] else "—"
        birth_time = row[8] if row[8] else "—"
        birth_place = row[9] if row[9] else "—"
        remaining_q = get_free_questions_remaining(user_id)
        level, xp, next_xp = calculate_level(user_id)
        level_name = LEVELS.get(level, {}).get("name", "Новичок")
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
                f"│ 📞 Телефон: {phone}\n"
                f"│ 🌍 Город: {city}\n"
                f"└─────────────────────┘")
        await message.answer(text, reply_markup=profile_menu)

    @dp.callback_query(F.data == "change_name")
    async def change_name_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("Введите новое имя (не менее 2 символов):")
        await state.set_state(UserStates.waiting_new_name)
        await callback.answer()

    @dp.message(UserStates.waiting_new_name)
    async def change_name_save(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        new_name = message.text.strip()
        if len(new_name) < 2:
            await message.answer("Имя должно быть не короче 2 символов.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
        conn.commit()
        conn.close()
        update_last_active(user_id)
        await message.answer(f"Имя изменено на {new_name}.")
        await state.clear()

    @dp.callback_query(F.data == "referral_info")
    async def referral_info(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        link = generate_referral_link(user_id)
        stats = get_referral_stats(user_id)
        text = (
            "🎁 *Бесплатные дни*\n\n"
            "Отправьте другу ссылку. Как только друг оформит подписку, вы получите +7 дней полного доступа в подарок.\n\n"
            f"Ваша ссылка: {link}\n\n"
            f"Приведено друзей с подпиской: *{stats['paid']}*\n"
            f"Всего переходов: *{stats['total']}*\n\n"
            "Чем больше друзей, тем больше бонусных дней!"
        )
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=menu_button)
        await callback.answer()

    @dp.callback_query(F.data == "achievements")
    async def show_achievements(callback: types.CallbackQuery):
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

    @dp.callback_query(F.data == "settings")
    async def settings_menu(callback: types.CallbackQuery):
        await callback.message.answer(
            "⚙️ *Настройки*\n\n"
            "• Отписаться от ежедневной рассылки – /unsubscribe_daily\n"
            "• Подписаться на рассылку – /subscribe_daily\n"
            "• Добавить или заменить номер телефона (для восстановления подписки)\n"
            "• Добавить или заменить город (для прогноза погоды)\n"
            "• Указать время и место рождения (для астрологии) – /setbirth\n\n"
            "Нажмите кнопку ниже, чтобы добавить или заменить данные.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Добавить/заменить телефон", callback_data="add_phone")],
                [InlineKeyboardButton(text="🌍 Добавить/заменить город", callback_data="add_city")],
                [InlineKeyboardButton(text="🕒 Указать время рождения", callback_data="add_birth_time")],
                [InlineKeyboardButton(text="📍 Указать место рождения", callback_data="add_birth_place")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
        )
        await callback.answer()

    @dp.callback_query(F.data == "add_phone")
    async def add_phone_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer(
            "Отправьте ваш номер телефона, нажав на кнопку ниже. Он нужен для восстановления подписки и важных уведомлений. "
            "Если номер уже есть, он будет заменён.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Отправить номер", callback_data="request_phone")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="settings")]
            ])
        )
        await callback.answer()

    @dp.callback_query(F.data == "request_phone")
    async def request_phone(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer(
            "Пожалуйста, поделитесь номером телефона, нажав кнопку ниже.",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
                resize_keyboard=True, one_time_keyboard=True
            )
        )
        await state.set_state(UserStates.waiting_phone)
        await callback.answer()

    @dp.message(UserStates.waiting_phone, F.contact)
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

    @dp.callback_query(F.data == "add_city")
    async def add_city_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer(
            "Напишите название вашего города (например, Москва или Санкт-Петербург). Это нужно для точного прогноза погоды. Если город уже указан, он будет заменён.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="settings")]
            ])
        )
        await state.set_state(UserStates.waiting_city)
        await callback.answer()

    @dp.message(UserStates.waiting_city)
    async def process_city(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        city_input = message.text.strip()
        city_lower = city_input.lower()
        if len(city_input) < 2:
            await message.answer("Пожалуйста, введите корректное название города (не менее 2 символов).")
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
            await status_msg.edit_text("❌ Не удалось определить город. Попробуйте написать его на русском или английском языке более точно (например, 'Санкт-Петербург').")
        await state.clear()

    @dp.callback_query(F.data == "add_birth_time")
    async def add_birth_time_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("Введите время рождения в формате ЧЧ:ММ (например, 15:30). Если не знаете – напишите «неизвестно».")
        await state.set_state(UserStates.waiting_birth_time)
        await callback.answer()

    @dp.message(UserStates.waiting_birth_time)
    async def save_birth_time(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        time_str = message.text.strip()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET birth_time = ? WHERE user_id = ?", (time_str, user_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Время рождения сохранено: {time_str}")
        await state.clear()

    @dp.callback_query(F.data == "add_birth_place")
    async def add_birth_place_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("Введите город и страну рождения (например, Москва, Россия).")
        await state.set_state(UserStates.waiting_birth_place)
        await callback.answer()

    @dp.message(UserStates.waiting_birth_place)
    async def save_birth_place(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        place = message.text.strip()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET birth_place = ? WHERE user_id = ?", (place, user_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Место рождения сохранено: {place}")
        await state.clear()

    @dp.callback_query(F.data == "cancel_sub")
    async def cancel_subscription(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, отменить", callback_data="confirm_cancel_sub")],
            [InlineKeyboardButton(text="❌ Нет, оставить", callback_data="back_to_menu")]
        ])
        await callback.message.answer("Вы уверены, что хотите отменить подписку? Доступ будет прекращён после окончания оплаченного периода.", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data == "confirm_cancel_sub")
    async def confirm_cancel_sub(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET subscription_active = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await callback.message.answer("Подписка отменена. Вы сохраните доступ до окончания оплаченного периода.")
        await callback.answer()

    @dp.callback_query(F.data == "history")
    async def show_history(callback: types.CallbackQuery):
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

    @dp.message(Command("setcity"))
    async def setcity_command(message: types.Message, state: FSMContext):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Использование: /setcity <название города>\nПример: /setcity Москва")
            return
        city_input = args[1].strip()
        city_lower = city_input.lower()
        status_msg = await message.answer("🌍 Определяю местоположение...")
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
            user_id = message.from_user.id
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET city = ?, timezone = ? WHERE user_id = ?", (city_input, timezone_raw, user_id))
            conn.commit()
            conn.close()
            await status_msg.edit_text(f"✅ Город *{city_input}* сохранён.\n🗓️ Часовой пояс: {timezone_ru}")
        else:
            await status_msg.edit_text("❌ Не удалось определить город. Попробуйте написать его на русском или английском языке более точно.")
        await state.clear()

    @dp.message(Command("mycity"))
    async def mycity_command(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT city FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            await message.answer(f"🌍 Ваш город: {row[0]}. Чтобы изменить, используйте /setcity.")
        else:
            await message.answer("🌍 Город не указан. Укажите его через /setcity или в настройках профиля.")

    @dp.message(Command("setbirth"))
    async def setbirth_command(message: types.Message, state: FSMContext):
        await message.answer("Используйте настройки профиля (кнопка «НАСТРОЙКИ») для указания времени и места рождения.")

    @dp.callback_query(F.data == "buy_subscription")
    async def buy_subscription(callback: types.CallbackQuery):
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Подписка на бота «Аркадий Викторович»",
            description="Месяц полного доступа: матрица судьбы, безлимитные вопросы, прогнозы, гороскопы и психологические практики.",
            payload="subscription_month",
            provider_token=PAYMENTS_TOKEN,
            currency="XTR",
            prices=[LabeledPrice(label="Месяц", amount=249)],
            start_parameter="subscription"
        )
        await callback.answer()

    @dp.callback_query(F.data == "gift_subscription")
    async def gift_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("Введите @username друга, которому хотите подарить подписку (без @):")
        await state.set_state(UserStates.waiting_gift_username)
        await callback.answer()

    @dp.message(UserStates.waiting_gift_username)
    async def gift_process(message: types.Message, state: FSMContext):
        username = message.text.strip().lstrip('@')
        try:
            chat = await message.bot.get_chat(f"@{username}")
            gifted_user_id = chat.id
        except Exception:
            await message.answer(f"❌ Не удалось найти пользователя @{username}. Проверьте правильность написания.")
            await state.clear()
            return
        await message.bot.send_invoice(
            chat_id=message.from_user.id,
            title=f"Подарочная подписка для @{username}",
            description=f"Вы дарите месяц подписки пользователю @{username}",
            payload=f"gift_{gifted_user_id}",
            provider_token=PAYMENTS_TOKEN,
            currency="XTR",
            prices=[LabeledPrice(label="Месяц в подарок", amount=249)],
            start_parameter="gift"
        )
        await state.clear()

    @dp.callback_query(F.data == "renew_subscription")
    async def renew_subscription(callback: types.CallbackQuery):
        await buy_subscription(callback)

    @dp.callback_query(F.data == "add_to_group")
    async def add_to_group_info(callback: types.CallbackQuery):
        bot_username = (await bot.get_me()).username
        invite_link = f"https://t.me/{bot_username}?startgroup=start"
        text = (
            "👥 *Как добавить бота в групповой чат или канал:*\n\n"
            "1. Нажмите на ссылку ниже, чтобы добавить бота в чат:\n"
            f"👉 [Добавить бота в группу]({invite_link})\n\n"
            "2. Дайте боту права администратора (для публикации сообщений).\n"
            "3. Напишите в чате команду `/start_bot`, чтобы активировать бота.\n"
            "4. Настройте тип контента командой `/set_chat_type <тип>`:\n"
            "   • `daily_motivation` – ежедневная мотивация\n"
            "   • `horoscope` – гороскоп на день\n"
            "   • `advice` – психологический совет\n"
            "5. Бот будет публиковать выбранный контент каждый день в 9:00.\n\n"
            "Любой участник чата может запросить свой гороскоп или матрицу, написав боту в личку.\n"
            "Подробнее – в профиле бота."
        )
        await callback.message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
        await callback.answer()

    @dp.callback_query(F.data == "help")
    async def show_help(callback: types.CallbackQuery):
        text = (
            "❓ *Помощь по боту «Аркадий Викторович»*\n\n"
            "🌟 *Основные команды:*\n"
            "• /start – запустить бота\n"
            "• /menu – главное меню\n"
            "• /mynumber – узнать ваше число судьбы\n"
            "• /setcity – указать город\n"
            "• /setbirth – указать время и место рождения\n"
            "• /cancel – отменить текущее действие\n\n"
            "🧠 *Разделы:*\n"
            "• 🔮 МОЯ МАТРИЦА – полная матрица судьбы (по подписке)\n"
            "• 🔢 МОЁ ЧИСЛО – характеристика числа судьбы\n"
            "• ❤️ СОВМЕСТИМОСТЬ – совместимость с партнёром\n"
            "• 🎁 КАРТА ДНЯ – прогноз на день\n"
            "• 💬 ЗАДАТЬ ВОПРОС – вопросы по нумерологии/психологии\n"
            "• 🧠 ПСИХОЛОГИЯ – тесты, дневник настроения\n"
            "• 🌟 АСТРОЛОГИЯ – натальная карта, транзиты, соляр\n"
            "• 👤 МОЙ ПРОФИЛЬ – управление подпиской, рефералы, настройки\n\n"
            "💎 *Подписка (249 ₽/мес):*\n"
            "• Полная матрица судьбы\n"
            "• Безлимитные вопросы\n"
            "• Ежедневная карта дня\n"
            "• Гороскоп на месяц\n"
            "• Еженедельные мотивирующие фразы\n\n"
            "📌 *Для групп:*\n"
            "Добавьте бота в чат и активируйте командой /start_bot.\n"
            "Настройте тип контента: /set_chat_type daily_motivation (мотивация), horoscope (гороскоп), advice (совет).\n\n"
            "👥 *Поддержка:* @Aristocrat102\n"
            "Версия бота: 2.1.0"
        )
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=menu_button)
        await callback.answer()

    @dp.pre_checkout_query()
    async def pre_checkout(query: PreCheckoutQuery):
        await query.answer(ok=True)

    @dp.message(F.successful_payment)
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