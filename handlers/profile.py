import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import profile_menu, main_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    generate_referral_link, get_referral_stats, get_free_questions_remaining,
    get_achievements, add_subscription_days, update_last_active,
    get_user_subscription_status, calculate_level,
    get_city_coords, get_timezone_by_coords
)
from settings import LEVELS

class UserStates(StatesGroup):
    waiting_new_name = State()
    waiting_new_birth = State()
    waiting_phone = State()
    waiting_city = State()          # новое состояние для ввода города

def register_profile_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "👤 МОЙ ПРОФИЛЬ")
    async def show_profile(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, birth_date, destiny_number, subscription_active, subscription_end, phone, city, timezone FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            await message.answer("Нажмите /start", reply_markup=menu_button)
            return
        name = row[0] or "—"
        birth = row[1] or "—"
        destiny = row[2] or "?"
        sub_status = "Активна" if row[3] else "Неактивна"
        sub_end = row[4] if row[4] else "—"
        phone = row[5] if row[5] else "—"
        city = row[6] if row[6] else "—"
        remaining = get_free_questions_remaining(user_id)
        level, xp, next_xp = calculate_level(user_id)
        level_name = LEVELS.get(level, {}).get("name", "Новичок")
        text = (f"┌─────────────────────┐\n"
                f"│ 👤 Имя: {name}\n"
                f"│ 🎂 Дата: {birth}\n"
                f"│ 🔢 Число: {destiny}\n"
                f"│ 💳 Подписка: {sub_status}\n"
                f"│ 📅 До: {sub_end}\n"
                f"│ 🎁 Бесплатных вопросов: {remaining}/5\n"
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

    @dp.callback_query(F.data == "change_birth")
    async def change_birth_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("Введите новую дату рождения в формате ДД.ММ.ГГГГ. Внимание: дату можно изменить только через администратора. Для этого напишите @Aristocrat102.")
        # Защита от абуза: дата не меняется, только через админа
        await callback.answer()

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
            "• Добавить номер телефона (для восстановления подписки)\n"
            "• Указать город (для прогноза погоды) – /setcity\n\n"
            "Нажмите кнопку ниже, чтобы добавить номер телефона или указать город.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Добавить номер телефона", callback_data="add_phone")],
                [InlineKeyboardButton(text="🌍 Указать город", callback_data="add_city")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
        )
        await callback.answer()

    @dp.callback_query(F.data == "add_phone")
    async def add_phone_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer(
            "Отправьте ваш номер телефона, нажав на кнопку ниже. Он нужен для восстановления подписки и важных уведомлений. "
            "Номер не передаётся третьим лицам.",
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
        await message.answer("Спасибо! Номер телефона сохранён.", reply_markup=main_menu)
        await state.clear()

    @dp.callback_query(F.data == "add_city")
    async def add_city_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer(
            "Напишите название вашего города (например, Москва или Moscow). Это нужно для точного прогноза погоды в карте дня и будильнике.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="settings")]
            ])
        )
        await state.set_state(UserStates.waiting_city)
        await callback.answer()

    @dp.message(UserStates.waiting_city)
    async def process_city(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        city = message.text.strip()
        if len(city) < 2:
            await message.answer("Пожалуйста, введите корректное название города (не менее 2 символов).")
            return

        status_msg = await message.answer("🌍 Определяю местоположение и часовой пояс...")
        lat, lon = await get_city_coords(city)
        if lat and lon:
            timezone = await get_timezone_by_coords(lat, lon)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET city = ?, timezone = ? WHERE user_id = ?", (city, timezone, user_id))
            conn.commit()
            conn.close()
            await status_msg.edit_text(f"✅ Город {city} сохранён. Ваш часовой пояс: {timezone}")
        else:
            await status_msg.edit_text("❌ Не удалось определить город. Попробуйте написать его на русском или английском языке более точно (например, 'Санкт-Петербург').")
        await state.clear()

    @dp.callback_query(F.data == "cancel_sub")
    async def cancel_subscription(callback: types.CallbackQuery):
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
        city = args[1].strip()
        status_msg = await message.answer("🌍 Определяю местоположение...")
        lat, lon = await get_city_coords(city)
        if lat and lon:
            timezone = await get_timezone_by_coords(lat, lon)
            user_id = message.from_user.id
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET city = ?, timezone = ? WHERE user_id = ?", (city, timezone, user_id))
            conn.commit()
            conn.close()
            await status_msg.edit_text(f"✅ Город сохранён: {city}\nЧасовой пояс: {timezone}")
        else:
            await status_msg.edit_text("❌ Не удалось определить город. Попробуйте написать его на русском или английском языке.")
        await state.clear()