import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu, profile_menu, quick_topics_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    is_blacklisted, calculate_destiny_number, add_subscription_days,
    get_user_subscription_status, generate_referral_link, add_referral_bonus,
    get_referral_stats, get_free_questions_remaining, increment_free_query,
    save_dialog_history
)

class UserStates(StatesGroup):
    waiting_birth_date = State()
    waiting_partner_birth_date = State()
    waiting_question = State()
    waiting_promocode = State()
    waiting_full_name = State()
    waiting_birth_date_from_poll = State()

def register_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    # -------------------- СТАРТ И ОПРОС --------------------
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if is_blacklisted(user_id):
            await message.answer("Вы заблокированы.")
            return

        # Обработка реферальной ссылки: ?start=ref_123456789
        args = message.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            referrer_id = int(args[1][4:])
            if referrer_id != user_id:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
                conn.commit()
                conn.close()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, birth_date FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0] and row[1]:
            await message.answer(
                f"🔮 С возвращением, {row[0]}! Аркадий Викторович ждёт ваших вопросов.",
                reply_markup=main_menu,
                parse_mode=None
            )
            await state.clear()
            return

        first_name = message.from_user.first_name
        await message.answer(
            f"✨ {first_name}, я — Аркадий Викторович, практикующий нумеролог и психолог с 20-летним стажем.\n\n"
            "Давайте познакомимся. Как вас зовут? (Напишите имя)",
            reply_markup=None
        )
        await state.set_state(UserStates.waiting_full_name)

    @dp.message(UserStates.waiting_full_name)
    async def process_full_name(message: types.Message, state: FSMContext):
        name = message.text.strip()
        if len(name) < 2:
            await message.answer("Пожалуйста, напишите настоящее имя (не менее 2 символов).")
            return
        await state.update_data(name=name)
        await message.answer(
            f"Отлично, {name}! Теперь укажите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1985).\n\n"
            "Это нужно для расчёта числа судьбы.",
            parse_mode=None
        )
        await state.set_state(UserStates.waiting_birth_date_from_poll)

    @dp.message(UserStates.waiting_birth_date_from_poll)
    async def process_birth_date_from_poll(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        text = message.text.strip()
        try:
            day, month, year = map(int, text.split('.'))
            birth_date = f"{day:02d}.{month:02d}.{year:04d}"
            today = datetime.date.today()
            birth = datetime.date(year, month, day)
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            if age < 18:
                await message.answer("Работаю только с совершеннолетними. Попробуйте другую дату.")
                return
            destiny = calculate_destiny_number(birth_date)
            data = await state.get_data()
            name = data.get("name", "друг")
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, name, birth_date, destiny_number, reg_date, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                name=excluded.name, birth_date=excluded.birth_date,
                destiny_number=excluded.destiny_number, last_active=excluded.last_active
            """, (user_id, name, birth_date, destiny, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
            conn.commit()
            conn.close()
            await message.answer(
                f"🔢 Ваше число судьбы: {destiny}\n\n"
                f"Спасибо, {name}! Нажмите на любую кнопку ниже, чтобы получить ответ по интересующей теме.\n"
                "А в главном меню вас ждёт полная матрица, совместимость и другие возможности.",
                reply_markup=quick_topics_menu,
                parse_mode=None
            )
            await state.clear()
        except Exception:
            await message.answer("Неверный формат. Введите дату в формате ДД.ММ.ГГГГ")

    # -------------------- КНОПКА «ЧИСЛО РОЖДЕНИЯ» (альтернативный ввод) --------------------
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
                                 reply_markup=quick_topics_menu, parse_mode=None)
            await state.clear()
        except Exception:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ")

    # -------------------- БЫСТРЫЕ ТЕМЫ --------------------
    @dp.callback_query(F.data.startswith("quick_topic_"))
    async def handle_quick_topic(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        user_id = callback.from_user.id
        topic = callback.data.split("_")[-1]  # money, love, health, career, family, creativity

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала укажите дату рождения через кнопку ЧИСЛО РОЖДЕНИЯ.", reply_markup=menu_button)
            return

        destiny = row[0]
        name = row[1] or "друг"

        topics_map = {
            "money": "деньгах, финансах, карьере",
            "love": "любви, отношениях, совместимости",
            "health": "здоровье, энергии, самочувствии",
            "career": "карьере, профессиональном росте, призвании",
            "family": "семье, домашнем очаге, отношениях с родными",
            "creativity": "творчестве, самовыражении, хобби"
        }
        query = topics_map.get(topic, "интересующей теме")
        prompt = f"Человек с числом судьбы {destiny} по имени {name} спрашивает о {query}. Дай развёрнутый ответ (5-7 предложений) с конкретными советами."
        response = await get_yandex_gpt_response(prompt, user_id)
        await callback.message.answer(f"✨ *{topic.capitalize()}*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)

    # -------------------- ОСНОВНЫЕ КНОПКИ МЕНЮ --------------------
    @dp.message(F.text == "🔮 МОЯ МАТРИЦА")
    async def matrix_prompt(message: types.Message):
        user_id = message.from_user.id
        if not get_user_subscription_status(user_id):
            await message.answer("Полная матрица судьбы доступна только по подписке. Оформите подписку в профиле.", reply_markup=menu_button)
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала укажите дату рождения через кнопку ЧИСЛО РОЖДЕНИЯ.", reply_markup=menu_button)
            return
        destiny = row[0]
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
        if get_user_subscription_status(user_id):
            await message.answer("Напишите ваш вопрос (по нумерологии или психологии). Я отвечу максимально честно.")
            await state.set_state(UserStates.waiting_question)
            return

        remaining = get_free_questions_remaining(user_id)
        if remaining > 0:
            await message.answer(f"У вас осталось *{remaining}* бесплатных вопросов на сегодня. Напишите вопрос, я дам короткий ответ. А в подписке – полная информация и развёрнутые консультации.\n\nВаш вопрос:", parse_mode="Markdown")
            await state.set_state(UserStates.waiting_question)
        else:
            await message.answer("Вы исчерпали лимит бесплатных вопросов на сегодня. Оформите подписку в профиле – и получите безлимитные консультации, полную матрицу и прогнозы.", reply_markup=menu_button)

    @dp.message(UserStates.waiting_question)
    async def process_question(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        question = message.text
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        destiny = row[0] if row else "?"
        name = row[1] if row else "друг"

        is_subscriber = get_user_subscription_status(user_id)
        if is_subscriber:
            prompt = f"Человек с числом судьбы {destiny} по имени {name} спрашивает: {question}. Ответь развёрнуто, как психолог и нумеролог, с советами."
            response = await get_yandex_gpt_response(prompt, user_id)
            await message.answer(response, parse_mode=None, reply_markup=menu_button)
            await state.clear()
            return

        # Бесплатный режим: короткий ответ + намёк на подписку
        remaining = get_free_questions_remaining(user_id)
        if remaining <= 0:
            await message.answer("Лимит бесплатных вопросов на сегодня исчерпан. Оформите подписку в профиле.", reply_markup=menu_button)
            await state.clear()
            return

        # Отвечаем кратко
        prompt = f"Человек с числом судьбы {destiny} спрашивает: {question}. Дай очень короткий ответ (1-2 предложения), интригующий, но не раскрывай всех деталей. В конце добавь фразу: «Полный разбор и советы – по подписке»."
        short_response = await get_yandex_gpt_response(prompt, user_id)
        increment_free_query(user_id)
        await message.answer(f"🔮 {short_response}\n\nУ вас осталось *{remaining-1}* бесплатных вопросов на сегодня. Хотите безлимит? Оформите подписку в профиле.", parse_mode="Markdown", reply_markup=menu_button)
        await state.clear()

    # -------------------- ПРОФИЛЬ И РЕФЕРАЛЬНАЯ СИСТЕМА --------------------
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

    # -------------------- ПРОМОКОДЫ --------------------
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

    # -------------------- ОБЩИЕ CALLBACK --------------------
    @dp.callback_query(F.data == "close")
    async def close_profile(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "back_to_menu")
    async def back_to_menu_callback(callback: types.CallbackQuery):
        await callback.message.answer("Главное меню", reply_markup=main_menu)
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query()
    async def other_callbacks(callback: types.CallbackQuery):
        await callback.answer("В разработке", show_alert=True)

    @dp.message(Command("menu"))
    async def menu_command(message: types.Message):
        await message.answer("Главное меню", reply_markup=main_menu)