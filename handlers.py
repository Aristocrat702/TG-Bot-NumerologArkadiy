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

def register_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if is_blacklisted(user_id):
            await message.answer("ы заблокированы.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, reg_date, last_active) VALUES (?, ?, ?)",
                       (user_id, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        await message.answer(
            "🔮 ркадий икторович приветствует вас!\n\n"
            "ажмите С Я, чтобы начать.\n"
            "одписка даёт полную матрицу и безлимитные вопросы.",
            reply_markup=main_menu,
            parse_mode=None
        )
        await state.clear()

    @dp.message(F.text == "📅 С Я")
    async def ask_birth_date(message: types.Message, state: FSMContext):
        await message.answer("ведите дату рождения в формате .. (например, 15.06.1985)")
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
                await message.answer("аботаю только с совершеннолетними.")
                await state.clear()
                return
            destiny = calculate_destiny_number(birth_date)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET birth_date = ?, destiny_number = ?, last_active = ? WHERE user_id = ?",
                           (birth_date, destiny, datetime.datetime.now().isoformat(), user_id))
            conn.commit()
            conn.close()
            prompt = f"исло судьбы {destiny}. ай краткую характеристику (2-3 предложения), назови слабость и дай совет."
            response = await get_yandex_gpt_response(prompt, user_id)
            await message.answer(f"🔢 аше число судьбы: {destiny}\n\n{response}", parse_mode=None)
            await state.clear()
        except Exception:
            await message.answer("еверный формат. ведите ..")

    @dp.message(F.text == "🔮 Я Т")
    async def matrix_prompt(message: types.Message):
        user_id = message.from_user.id
        if not get_user_subscription_status(user_id):
            await message.answer("олная матрица судьбы доступна только по подписке. формите подписку в профиле.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала укажите дату рождения через кнопку С Я.")
            return
        birth = row[0]
        destiny = row[1]
        prompt = f"Составь полную матрицу судьбы для числа {destiny}. ай развёрнутую характеристику (10-15 предложений) по арканам."
        response = await get_yandex_gpt_response(prompt, user_id)
        await message.answer(f"🔮 *атрица судьбы*\n\n{response}", parse_mode="Markdown")

    @dp.message(F.text == "❤️ ССТСТЬ")
    async def ask_partner_birth(message: types.Message, state: FSMContext):
        await message.answer("ведите дату рождения партнёра в формате ..")
        await state.set_state(UserStates.waiting_partner_birth_date)
        await state.update_data(my_birth=message.from_user.id)

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
                await message.answer("Сначала укажите свою дату рождения через кнопку С Я.")
                await state.clear()
                return
            my_destiny = row[0]
            prompt = f"исло судьбы пользователя {my_destiny}, число партнёра {partner_destiny}. пиши совместимость (5-7 предложений) с советами."
            response = await get_yandex_gpt_response(prompt, user_id)
            await message.answer(f"❤️ *Совместимость*\n\n{response}", parse_mode="Markdown")
            await state.clear()
        except Exception:
            await message.answer("еверный формат даты. ведите ..")

    @dp.message(F.text == "🎁 Т Я")
    async def daily_card(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        destiny = row[0] if row else "?"
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. ай короткий прогноз (3-5 предложений)."
        response = await get_yandex_gpt_response(prompt, user_id)
        await message.answer(f"🎁 *арта дня*\n\n{response}", parse_mode="Markdown")

    @dp.message(F.text == "💬 ТЬ С")
    async def ask_question(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if not get_user_subscription_status(user_id):
            await message.answer("адавать вопросы могут только подписчики. формите подписку в профиле.")
            return
        await message.answer("апишите ваш вопрос (по нумерологии или психологии). Я отвечу максимально честно.")
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
        prompt = f"еловек с числом судьбы {destiny} спрашивает: {question}. тветь как психолог и нумеролог, прямо, без сюсюканий."
        response = await get_yandex_gpt_response(prompt, user_id)
        await message.answer(response, parse_mode=None)
        await state.clear()

    @dp.message(F.text == "👤  Ь")
    async def show_profile(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, birth_date, destiny_number, subscription_active, subscription_end FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            await message.answer("ажмите /start")
            return
        name = row[0] or "—"
        birth = row[1] or "—"
        destiny = row[2] or "?"
        sub_status = "ктивна" if row[3] else "еактивна"
        sub_end = row[4] if row[4] else "—"
        text = (f"┌─────────────────────┐\n"
                f"│ 👤 мя: {name}\n"
                f"│ 🎂 ата: {birth}\n"
                f"│ 🔢 исло: {destiny}\n"
                f"│ 💳 одписка: {sub_status}\n"
                f"│ 📅 о: {sub_end}\n"
                f"└─────────────────────┘")
        await message.answer(text, reply_markup=profile_menu)

    @dp.callback_query(F.data == "enter_promo")
    async def promo_callback(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("ведите промокод:")
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
            await message.answer("еверный код.")
            await state.clear()
            return
        action_days = promo[0]
        max_uses = promo[1]
        used_count = promo[2]
        expires_at = promo[3]
        if expires_at and expires_at < datetime.datetime.now().isoformat():
            await message.answer("од просрочен.")
            await state.clear()
            return
        if max_uses > 0 and used_count >= max_uses:
            await message.answer("од уже использован.")
            await state.clear()
            return
        cursor.execute("SELECT 1 FROM promocode_activations WHERE user_id=? AND code=?", (user_id, code))
        if cursor.fetchone():
            await message.answer("ы уже активировали этот код.")
            await state.clear()
            return
        add_subscription_days(user_id, action_days)
        cursor.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code=?", (code,))
        cursor.execute("INSERT INTO promocode_activations (user_id, code, activated_at, result_text) VALUES (?, ?, ?, ?)",
                       (user_id, code, datetime.datetime.now().isoformat(), f"+{action_days} дней"))
        conn.commit()
        conn.close()
        await message.answer(f"🎉 оздравляем! ы активировали промокод +{action_days} дней подписки.")
        await state.clear()

    @dp.callback_query(F.data == "close")
    async def close_profile(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query()
    async def other_callbacks(callback: types.CallbackQuery):
        await callback.answer(" разработке", show_alert=True)
