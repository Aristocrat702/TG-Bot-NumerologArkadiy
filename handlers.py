import datetime
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from keyboards import (
    main_menu, profile_menu, quick_topics_menu, share_button,
    menu_button, challenge_menu
)
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    is_blacklisted, calculate_destiny_number, add_subscription_days,
    get_user_subscription_status, generate_referral_link, add_referral_bonus,
    get_referral_stats, get_free_questions_remaining, increment_free_query,
    save_dialog_history, get_dialog_history, grant_achievement,
    get_achievements, start_challenge, complete_challenge_day,
    get_challenge_progress, get_bot_config, get_cached_response,
    save_cached_response, log_mood, get_week_moods
)

class UserStates(StatesGroup):
    waiting_birth_date = State()
    waiting_partner_birth_date = State()
    waiting_question = State()
    waiting_promocode = State()
    waiting_full_name = State()
    waiting_birth_date_from_poll = State()
    waiting_challenge_day = State()
    # Психологический тест
    waiting_psycho_test_q1 = State()
    waiting_psycho_test_q2 = State()
    waiting_psycho_test_q3 = State()
    # Дневник эмоций
    waiting_mood = State()

# Временное хранилище для ответов теста
psycho_answers = {}

def register_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    # ---------- СТАРТ И ОПРОС ----------
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if is_blacklisted(user_id):
            await message.answer("Вы заблокированы.")
            return

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
            grant_achievement(user_id, "first_calculation")
            await state.clear()
        except Exception:
            await message.answer("Неверный формат. Введите дату в формате ДД.ММ.ГГГГ")

    # ---------- КНОПКА «ЧИСЛО РОЖДЕНИЯ» (с кэшем) ----------
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

            # Кэш
            cache_key = f"birth_{destiny}"
            cached = get_cached_response(user_id, cache_key)
            if cached:
                response = cached
            else:
                status_msg = await message.answer("🧐 Аркадий Викторович изучает ваш гороскоп...")
                prompt = f"Число судьбы {destiny}. Дай краткую характеристику (2-3 предложения), назови слабость и дай совет."
                response = await get_yandex_gpt_response(prompt, user_id)
                await status_msg.delete()
                save_cached_response(user_id, cache_key, response)

            await message.answer(f"🔢 Ваше число судьбы: {destiny}\n\n{response}",
                                 reply_markup=quick_topics_menu, parse_mode=None)
            await state.clear()
        except Exception:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ")

    # ---------- БЫСТРЫЕ ТЕМЫ ----------
    @dp.callback_query(F.data.startswith("quick_topic_"))
    async def handle_quick_topic(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        user_id = callback.from_user.id
        topic = callback.data.split("_")[-1]

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
            "creativity": "творчестве, самовыражении, хобби",
            "psychology": "психологии, внутренних состояниях, личностном росте"
        }
        query = topics_map.get(topic, "интересующей теме")
        prompt = f"Человек с числом судьбы {destiny} по имени {name} спрашивает о {query}. Дай развёрнутый ответ (5-7 предложений) с конкретными советами."
        status_msg = await callback.message.answer("🧐 Аркадий Викторович размышляет...")
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        await callback.message.answer(f"✨ *{topic.capitalize()}*\n\n{response}", parse_mode="Markdown", reply_markup=share_button)

    # ---------- МОЯ МАТРИЦА (с кэшем) ----------
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
        cache_key = f"matrix_{destiny}"
        cached = get_cached_response(user_id, cache_key)
        if cached:
            response = cached
            await message.answer(f"🔮 *Матрица судьбы*\n\n{response}", parse_mode="Markdown", reply_markup=share_button)
            return
        status_msg = await message.answer("📜 Аркадий Викторович составляет вашу матрицу... Это может занять до 10 секунд.")
        prompt = f"Составь полную матрицу судьбы для числа {destiny}. Дай развёрнутую характеристику (10-15 предложений) по арканам."
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        save_cached_response(user_id, cache_key, response)
        await message.answer(f"🔮 *Матрица судьбы*\n\n{response}", parse_mode="Markdown", reply_markup=share_button)

    # ---------- СОВМЕСТИМОСТЬ ----------
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
            status_msg = await message.answer("🔍 Анализирую совместимость...")
            prompt = f"Число судьбы пользователя {my_destiny}, число партнёра {partner_destiny}. Опиши совместимость (5-7 предложений) с советами."
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            await message.answer(f"❤️ *Совместимость*\n\n{response}", parse_mode="Markdown", reply_markup=share_button)
            await state.clear()
        except Exception:
            await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ", reply_markup=menu_button)

    # ---------- КАРТА ДНЯ ----------
    @dp.message(F.text == "🎁 КАРТА ДНЯ")
    async def daily_card(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        destiny = row[0] if row else "?"
        status_msg = await message.answer("🌙 Аркадий Викторович заглядывает в будущее...")
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай короткий прогноз (3-5 предложений)."
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        await message.answer(f"🎁 *Карта дня*\n\n{response}", parse_mode="Markdown", reply_markup=share_button)

    # ---------- ЗАДАТЬ ВОПРОС (с лимитами) ----------
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
        status_msg = await message.answer("🧐 Изучаю вопрос...")
        if is_subscriber:
            prompt = f"Человек с числом судьбы {destiny} по имени {name} спрашивает: {question}. Ответь развёрнуто, как психолог и нумеролог, с советами."
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            await message.answer(response, parse_mode=None, reply_markup=share_button)
            await state.clear()
            return

        remaining = get_free_questions_remaining(user_id)
        if remaining <= 0:
            await status_msg.delete()
            await message.answer("Лимит бесплатных вопросов на сегодня исчерпан. Оформите подписку в профиле.", reply_markup=menu_button)
            await state.clear()
            return

        prompt = f"Человек с числом судьбы {destiny} спрашивает: {question}. Дай очень короткий ответ (1-2 предложения), интригующий, но не раскрывай всех деталей. В конце добавь фразу: «Полный разбор и советы – по подписке»."
        short_response = await get_yandex_gpt_response(prompt, user_id)
        increment_free_query(user_id)
        await status_msg.delete()
        await message.answer(f"🔮 {short_response}\n\nУ вас осталось *{remaining-1}* бесплатных вопросов на сегодня. Хотите безлимит? Оформите подписку в профиле.", parse_mode="Markdown", reply_markup=menu_button)
        await state.clear()

    # ---------- ПРОФИЛЬ И РЕФЕРАЛКА ----------
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
    async def referral_info(callback: CallbackQuery):
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

    # ---------- ДОСТИЖЕНИЯ ----------
    @dp.callback_query(F.data == "achievements")
    async def show_achievements(callback: CallbackQuery):
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

    # ---------- ПСИХОЛОГИЧЕСКИЙ ТЕСТ ----------
    @dp.callback_query(F.data == "psycho_test")
    async def start_psycho_test(callback: CallbackQuery, state: FSMContext):
        await callback.message.answer("Психологический тест: Как вы чаще всего реагируете на стресс?\n1) Паникую и теряюсь\n2) Анализирую и ищу решение\n3) Отвлекаюсь на другие дела")
        await state.set_state(UserStates.waiting_psycho_test_q1)
        await callback.answer()

    @dp.message(UserStates.waiting_psycho_test_q1)
    async def psycho_test_q2(message: types.Message, state: FSMContext):
        answer = message.text.strip()
        await state.update_data(q1=answer)
        await message.answer("Вопрос 2: Как вы относитесь к своим ошибкам?\n1) Сильно переживаю\n2) Анализирую и делаю выводы\n3) Быстро забываю")
        await state.set_state(UserStates.waiting_psycho_test_q2)

    @dp.message(UserStates.waiting_psycho_test_q2)
    async def psycho_test_q3(message: types.Message, state: FSMContext):
        answer = message.text.strip()
        await state.update_data(q2=answer)
        await message.answer("Вопрос 3: Что для вас важнее в отношениях?\n1) Безопасность и стабильность\n2) Понимание и поддержка\n3) Свобода и независимость")
        await state.set_state(UserStates.waiting_psycho_test_q3)

    @dp.message(UserStates.waiting_psycho_test_q3)
    async def psycho_test_result(message: types.Message, state: FSMContext):
        data = await state.get_data()
        q1 = data.get("q1")
        q2 = data.get("q2")
        q3 = message.text.strip()
        # Простая интерпретация (можно расширить)
        result = "Вы склонны к тревожности, но обладаете аналитическим складом ума. Рекомендую практиковать осознанность."
        await message.answer(f"🧠 *Результат теста*\n\n{result}\n\nЭто предварительная оценка. Полный психологический разбор – по подписке.", parse_mode="Markdown", reply_markup=menu_button)
        await state.clear()

    # ---------- ДНЕВНИК НАСТРОЕНИЯ ----------
    @dp.callback_query(F.data == "mood_diary")
    async def mood_diary_start(callback: CallbackQuery, state: FSMContext):
        await callback.message.answer("Оцените своё настроение сегодня (от 1 до 5, где 1 – ужасно, 5 – отлично):")
        await state.set_state(UserStates.waiting_mood)
        await callback.answer()

    @dp.message(UserStates.waiting_mood)
    async def save_mood(message: types.Message, state: FSMContext):
        try:
            mood = int(message.text.strip())
            if mood < 1 or mood > 5:
                raise ValueError
            log_mood(message.from_user.id, mood)
            await message.answer("😊 Настроение сохранено! Через неделю я покажу график вашего эмоционального фона.")
        except:
            await message.answer("Пожалуйста, введите число от 1 до 5.")
            return
        await state.clear()

    @dp.callback_query(F.data == "mood_stats")
    async def show_mood_stats(callback: CallbackQuery):
        user_id = callback.from_user.id
        moods = get_week_moods(user_id)
        if not moods:
            await callback.message.answer("Нет данных о настроении за последнюю неделю. Начните вести дневник через кнопку «Дневник настроения».")
        else:
            text = "📊 Ваше настроение за неделю:\n"
            for date, mood in moods:
                text += f"{date[:10]}: {'😊' * mood}{'😐' * (5-mood)} ({mood}/5)\n"
            await callback.message.answer(text)
        await callback.answer()

    # ---------- ЧЕЛЛЕНДЖ 7 ДНЕЙ ----------
    @dp.callback_query(F.data == "start_challenge")
    async def start_challenge_callback(callback: CallbackQuery):
        user_id = callback.from_user.id
        progress = get_challenge_progress(user_id)
        if progress and any(not comp for _, comp in progress):
            await callback.message.answer("У вас уже есть активный челлендж. Выполняйте задания каждый день.", reply_markup=challenge_menu)
            await callback.answer()
            return
        start_challenge(user_id)
        await callback.message.answer(
            "🔥 Вы начали челлендж «7 дней до силы»!\n"
            "Каждый день я буду давать небольшое задание. Выполняйте его и нажимайте «Выполнил».\n"
            "За успешное прохождение всех 7 дней вы получите +3 дня подписки.\n\n"
            "Задание дня 1: Скажите «нет» человеку, который вас напрягает (мысленно или вслух).\n"
            "Как выполните – нажмите кнопку ниже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Выполнил день 1", callback_data="challenge_day_1")]
            ])
        )
        await callback.answer()

    @dp.callback_query(F.data.startswith("challenge_day_"))
    async def complete_challenge_day_callback(callback: CallbackQuery):
        user_id = callback.from_user.id
        day = int(callback.data.split("_")[-1])
        completed = complete_challenge_day(user_id, day)
        if completed:
            await callback.message.answer("🎉 Поздравляю! Вы прошли весь челлендж и получили +3 дня подписки. Продолжайте изучать нумерологию!")
        else:
            next_day = day + 1
            tasks = {
                2: "Сделайте спонтанный поступок (поменяйте маршрут, купите необычный продукт).",
                3: "Напишите себе письмо «Что я изменю через месяц».",
                4: "Сделайте зарядку 5 минут.",
                5: "Поблагодарите себя за что-то вслух.",
                6: "Отдайте ненужную вещь.",
                7: "Запланируйте конкретную цель на неделю."
            }
            if next_day <= 7:
                task_text = tasks.get(next_day, "Продолжайте челлендж!")
                await callback.message.answer(f"✅ День {day} выполнен!\n\nЗадание дня {next_day}: {task_text}\n\nНажмите «Выполнил», когда сделаете.",
                                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                                   [InlineKeyboardButton(text=f"✅ Выполнил день {next_day}", callback_data=f"challenge_day_{next_day}")]
                                               ]))
        await callback.answer()

    @dp.callback_query(F.data == "challenge_progress")
    async def show_challenge_progress(callback: CallbackQuery):
        user_id = callback.from_user.id
        progress = get_challenge_progress(user_id)
        if not progress:
            await callback.message.answer("Вы ещё не начинали челлендж. Нажмите «Начать челлендж 7 дней» в профиле.", reply_markup=menu_button)
        else:
            text = "📊 Прогресс челленджа:\n"
            for day, completed in progress:
                status = "✅" if completed else "❌"
                text += f"День {day}: {status}\n"
            await callback.message.answer(text, reply_markup=challenge_menu)
        await callback.answer()

    # ---------- ПРОМОКОДЫ ----------
    @dp.callback_query(F.data == "enter_promo")
    async def promo_callback(callback: CallbackQuery, state: FSMContext):
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
        add_subscription_days(user_id, action_days, check_referral=True)
        cursor.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code=?", (code,))
        cursor.execute("INSERT INTO promocode_activations (user_id, code, activated_at, result_text) VALUES (?, ?, ?, ?)",
                       (user_id, code, datetime.datetime.now().isoformat(), f"+{action_days} дней"))
        conn.commit()
        conn.close()
        await message.answer(f"🎉 Поздравляем! Вы активировали промокод +{action_days} дней подписки.", reply_markup=menu_button)
        await state.clear()

    # ---------- ИСТОРИЯ ЗАПРОСОВ ----------
    @dp.callback_query(F.data == "history")
    async def show_history(callback: CallbackQuery):
        user_id = callback.from_user.id
        history = get_dialog_history(user_id, 10)
        if not history:
            text = "История запросов пуста."
        else:
            text = "📜 Последние запросы:\n"
            for role, msg in history[:5]:
                if role == "user":
                    text += f"👤 Вы: {msg[:50]}...\n"
                else:
                    text += f"🤖 Аркадий: {msg[:50]}...\n"
        await callback.message.answer(text, reply_markup=menu_button)
        await callback.answer()

    # ---------- ОБЩИЕ CALLBACK ----------
    @dp.callback_query(F.data == "close")
    async def close_profile(callback: CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "back_to_menu")
    async def back_to_menu_callback(callback: CallbackQuery):
        await callback.message.answer("Главное меню", reply_markup=main_menu)
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "share_result")
    async def share_result(callback: CallbackQuery):
        text = "🔮 Мой нумерологический разбор от Аркадия Викторовича был очень интересным! Присоединяйтесь -> https://t.me/NumerologArkadiy_bot"
        await callback.message.answer(text)
        await callback.answer()

    @dp.callback_query(F.data == "back_to_profile")
    async def back_to_profile(callback: CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query()
    async def other_callbacks(callback: CallbackQuery):
        await callback.answer("В разработке", show_alert=True)

    @dp.message(Command("menu"))
    async def menu_command(message: types.Message):
        await message.answer("Главное меню", reply_markup=main_menu)