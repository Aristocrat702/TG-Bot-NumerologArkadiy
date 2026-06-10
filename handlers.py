import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import main_menu, profile_menu
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    is_blacklisted, calculate_destiny_number, add_subscription_days,
    get_user_subscription_status, save_dialog_history
)

class UserStates(StatesGroup):
    waiting_birth_date = State()
    waiting_partner_birth_date = State()
    waiting_question = State()
    waiting_promocode = State()

# Создаём Inline-кнопку для возврата в меню
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
menu_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
])

def register_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if is_blacklisted(user_id):
            await message.answer("Вы заблокированы.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, reg_date, last_active) VALUES (?, ?, ?)",
                       (user_id, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        await message.answer(
            "🔮 Аркадий Викторович приветствует вас!\n\n"
            "Нажмите ЧИСЛО РОЖДЕНИЯ, чтобы начать.\n"
            "Подписка даёт полную матрицу и безлимитные вопросы.",
            reply_markup=main_menu,
            parse_mode=None
        )
        await state.clear()

    @dp.message(F.text == "📅 ЧИСЛО РОЖДЕНИЯ")
    async def ask_birth_date(message: types.Message, state: FSMContext):
        await message.answer("Введите дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1985)")
        await state.set_state(UserStates.waiting_birth_date)

    @dp.message(UserStates.waiting_birth_date)
    async def process_birth_date(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        text = message.text.strip()
        try:
            day, month, year = map(int, text.split('.'))
            birth_date = f"{day:02d}.{month:02d}.{year:04d}"
            today = datetime.date.today()
            birth = datetime.date(year, month, day)
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            if age < 18:
                await message.answer("Работаю только с совершеннолетними.")
                await state.clear()
                return
            destiny = calculate_destiny_number(birth_date)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET birth_date = ?, destiny_number = ?, last_active = ? WHERE user_id = ?",
                           (birth_date, destiny, datetime.datetime.now().isoformat(), user_id))
            conn.commit()
            conn.close()
            prompt = f"Число судьбы {destiny}. Дай краткую характеристику (2-3 предложения), назови слабость и дай совет."
            response = await get_yandex_gpt_response(prompt, user_id)
            await message.answer(f"🔢 Ваше число судьбы: {destiny}\n\n{response}", 
                                 reply_markup=menu_button, parse_mode=None)
            await state.clear()
        except Exception:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ")

    @dp.message(F.text == "🔮 МОЯ МАТРИЦА")
    async def matrix_prompt(message: types.Message):
        user_id = message.from_user.id
        if not get_user_subscription_status(user_id):
            await message.answer("Полная матрица судьбы доступна только по подписке. Оформите подписку в профиле.", 
                                 reply_markup=menu_button)
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала укажите дату рождения через кнопку ЧИСЛО РОЖДЕНИЯ.", reply_markup=menu_button)
            return
        destiny = row[1]
        prompt = f"Составь полную матрицу судьбы для числа {destiny}. Дай развёрнутую характеристику (10-15 предложений) по арканам."
        response = await get_yandex_gpt_response(prompt, user_id)
        await message.answer(f"🔮 *Матрица судьбы*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)

    @dp.message(F.text == "❤️ СОВМЕСТИМОСТЬ")
    async def ask_partner_birth(message: types.Message, state: FSMContext):
        await message.answer("Введите дату рождения партнёра в формате ДД.ММ.ГГГГ")
        await state.set_state(UserStates.waiting_partner_birth_date)

    @dp.message(UserStates.waiting_partner_birth_date)
    async def process_compatibility(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        partner_text = message.text.strip()
        try:
            day, month, year = map(int, partner_text.split('.'))
            partner_birth = f"{day:02d}.{month:02d}.{year:04d}"
            partner_destiny = calculate_destiny_number(partner_birth)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            if not row or not row[0]:
                await message.answer("Сначала укажите свою дату рождения через кнопку ЧИСЛО РОЖДЕНИЯ.", reply_markup=menu_button)
                await state.clear()
                return
            my_destiny = row[0]
            prompt = f"Число судьбы пользователя {my_destiny}, число партнёра {partner_destiny}. Опиши совместимость (5-7 предложений) с советами."
            response = await get_yandex_gpt_response(prompt, user_id)
            await message.answer(f"❤️ *Совместимость*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
            await state.clear()
        except Exception:
            await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ", reply_markup=menu_button)

    @dp.message(F.text == "🎁 КАРТА ДНЯ")
    async def daily_card(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        destiny = row[0] if row else "?"
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай короткий прогноз (3-5 предложений)."
        response = await get_yandex_gpt_response(prompt, user_id)
        await message.answer(f"🎁 *Карта дня*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)

    @dp.message(F.text == "💬 ЗАДАТЬ ВОПРОС")
    async def ask_question(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if not get_user_subscription_status(user_id):
            await message.answer("Задавать вопросы могут только подписчики. Оформите подписку в профиле.", reply_markup=menu_button)
            return
        await message.answer("Напишите ваш вопрос (по нумерологии или психологии). Я отвечу максимально честно.")
        await state.set_state(UserStates.waiting_question)

    @dp.message(UserStates.waiting_question)
    async def process_question(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        question = message.text
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, birth_date FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        destiny = row[0] if row else "?"
        prompt = f"Человек с числом судьбы {destiny} спрашивает: {question}. Ответь как психолог и нумеролог, прямо, без сюсюканий."
        response = await get_yandex_gpt_response(prompt, user_id)
        await message.answer(response, parse_mode=None, reply_markup=menu_button)
        await state.clear()

    @dp.message(F.text == "👤 МОЙ ПРОФИЛЬ")
    async def show_profile(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, birth_date, destiny_number, subscription_active, subscription_end FROM users WHERE user_id=?", (user_id,))
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
        text = (f"┌─────────────────────┐\n"
                f"│ 👤 Имя: {name}\n"
                f"│ 🎂 Дата: {birth}\n"
                f"│ 🔢 Число: {destiny}\n"
                f"│ 💳 Подписка: {sub_status}\n"
                f"│ 📅 До: {sub_end}\n"
                f"└─────────────────────┘")
        await message.answer(text, reply_markup=profile_menu)

    @dp.callback_query(F.data == "enter_promo")
    async def promo_callback(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("Введите промокод:")
        await state.set_state(UserStates.waiting_promocode)
        await callback.answer()

    @dp.message(UserStates.waiting_promocode)
    async def process_promocode(message: types.Message, state: FSMContext):
        code = message.text.strip()
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT action_value, max_uses, used_count, expires_at FROM promocodes WHERE code=?", (code,))
        promo = cursor.fetchone()
        if not promo:
            await message.answer("Неверный код.", reply_markup=menu_button)
            await state.clear()
            return
        action_days = promo[0]
        max_uses = promo[1]
        used_count = promo[2]
        expires_at = promo[3]
        if expires_at and expires_at < datetime.datetime.now().isoformat():
            await message.answer("Код просрочен.", reply_markup=menu_button)
            await state.clear()
            return
        if max_uses > 0 and used_count >= max_uses:
            await message.answer("Код уже использован.", reply_markup=menu_button)
            await state.clear()
            return
        cursor.execute("SELECT 1 FROM promocode_activations WHERE user_id=? AND code=?", (user_id, code))
        if cursor.fetchone():
            await message.answer("Вы уже активировали этот код.", reply_markup=menu_button)
            await state.clear()
            return
        add_subscription_days(user_id, action_days)
        cursor.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code=?", (code,))
        cursor.execute("INSERT INTO promocode_activations (user_id, code, activated_at, result_text) VALUES (?, ?, ?, ?)",
                       (user_id, code, datetime.datetime.now().isoformat(), f"+{action_days} дней"))
        conn.commit()
        conn.close()
        await message.answer(f"🎉 Поздравляем! Вы активировали промокод +{action_days} дней подписки.", reply_markup=menu_button)
        await state.clear()

    @dp.callback_query(F.data == "close")
    async def close_profile(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "back_to_menu")
    async def back_to_menu(callback: types.CallbackQuery):
        await callback.message.answer("Главное меню", reply_markup=main_menu)
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query()
    async def other_callbacks(callback: types.CallbackQuery):
        await callback.answer("В разработке", show_alert=True)

    # Команда /menu
    @dp.message(Command("menu"))
    async def menu_command(message: types.Message):
        await message.answer("Главное меню", reply_markup=main_menu)