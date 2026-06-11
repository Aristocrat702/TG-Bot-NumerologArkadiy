import datetime
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import (
    main_menu, profile_menu, quick_topics_menu, share_button,
    menu_button, challenge_menu, psycho_submenu
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
    save_cached_response, delete_user_cache, log_mood, get_week_moods,
    set_bot_config, save_psycho_result, get_psycho_result, update_last_active
)

class UserStates(StatesGroup):
    waiting_birth_date = State()
    waiting_partner_birth_date = State()
    waiting_question = State()
    waiting_promocode = State()
    waiting_full_name = State()
    waiting_birth_date_from_poll = State()
    waiting_challenge_day = State()
    waiting_psycho_question = State()
    waiting_mood_value = State()
    waiting_mood_comment = State()
    waiting_new_name = State()
    waiting_new_birth = State()

# Временное хранение последнего ответа для кнопки «Поделиться»
last_answer = {}
# Временное хранение ответов на психотест
psycho_test_data = {}

def register_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    # ---------- СТАРТ И ОПРОС ----------
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        update_last_active(user_id)
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
                f"Спасибо, {name}! Теперь вы можете использовать главное меню.",
                reply_markup=main_menu,
                parse_mode=None
            )
            grant_achievement(user_id, "first_calculation")
            await state.clear()
        except Exception:
            await message.answer("Неверный формат. Введите дату в формате ДД.ММ.ГГГГ")

    # ---------- КНОПКА «МОЁ ЧИСЛО» (без повторного запроса даты) ----------
    @dp.message(F.text == "🔢 МОЁ ЧИСЛО")
    async def show_my_number(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала введите дату рождения через команду /start или дождитесь опроса.")
            return
        birth_date, destiny, name = row
        cached = get_cached_response(user_id, f"birth_{destiny}")
        if cached:
            response = cached
        else:
            status_msg = await message.answer("🧐 Аркадий Викторович изучает ваш гороскоп...")
            prompt = f"Число судьбы {destiny}. Дай краткую характеристику (2-3 предложения), назови слабость и дай совет."
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            save_cached_response(user_id, f"birth_{destiny}", response)
        await message.answer(f"🔢 Ваше число судьбы: {destiny}\n\n{response}",
                             reply_markup=quick_topics_menu, parse_mode=None)
        update_last_active(user_id)

    # ---------- ПСИХОЛОГИЯ (подменю) ----------
    @dp.message(F.text == "🧠 ПСИХОЛОГИЯ")
    async def psychology_menu(message: types.Message):
        await message.answer("🧠 *Психологический раздел*\n\nВыберите, что вас интересует:", parse_mode="Markdown", reply_markup=psycho_submenu)

    @dp.callback_query(F.data == "psycho_test")
    async def start_psycho_test(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer(
            "🧠 *Психотест*\n\nЯ задам 5 вопросов. Отвечайте честно и коротко.\n\n"
            "Вопрос 1: Как вы обычно реагируете на стресс? (коротко)",
            parse_mode="Markdown"
        )
        questions = [
            "Как вы обычно реагируете на стресс? (коротко)",
            "Что вас мотивирует больше всего?",
            "Как вы принимаете важные решения?",
            "Что вас чаще всего раздражает в других?",
            "Опишите своё отношение к критике."
        ]
        await state.update_data(questions=questions, answers=[], step=0)
        await state.set_state(UserStates.waiting_psycho_question)
        await callback.answer()

    @dp.message(UserStates.waiting_psycho_question)
    async def process_psycho_question(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        data = await state.get_data()
        step = data.get("step", 0)
        answers = data.get("answers", [])
        answers.append(message.text.strip())
        step += 1
        questions = data.get("questions", [])
        if step < len(questions):
            await state.update_data(step=step, answers=answers)
            await message.answer(f"Вопрос {step+1}: {questions[step]}")
        else:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            destiny = row[0] if row else "неизвестно"
            name = row[1] if row else "пользователь"
            prompt = (
                f"Пользователь {name} с числом судьбы {destiny} ответил на вопросы психологического теста: {answers}. "
                "Дай развёрнутую характеристику личности (5-7 предложений), укажи сильные стороны, слабости и дай практический совет. "
                "Будь прямолинеен, но не груб. Используй стиль Аркадия Викторовича."
            )
            status_msg = await message.answer("🧠 Анализирую ваши ответы...")
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            # Сохраняем результат в БД
            save_psycho_result(user_id, response)
            await message.answer(f"🧠 *Результат теста*\n\n{response}", parse_mode="Markdown", reply_markup=main_menu)
            await state.clear()

    @dp.callback_query(F.data == "my_psycho_result")
    async def show_my_psycho_result(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        result, created_at = get_psycho_result(user_id)
        if result:
            await callback.message.answer(f"📘 *Ваш последний результат психотеста* (от {created_at[:10]}):\n\n{result}", parse_mode="Markdown")
        else:
            await callback.message.answer("Вы ещё не проходили психотест. Нажмите «ПСИХОТЕСТ», чтобы пройти.")
        await callback.answer()

    @dp.callback_query(F.data == "mood_diary")
    async def mood_diary_menu(callback: types.CallbackQuery):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Записать настроение", callback_data="mood_log")],
            [InlineKeyboardButton(text="📊 Мой график", callback_data="mood_graph")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="psycho_back")]
        ])
        await callback.message.answer("😊 *Дневник настроения*\n\nЗаписывайте своё настроение и смотрите динамику.", parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data == "mood_log")
    async def mood_log_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("Оцените ваше настроение по шкале от 1 до 5 (1 – ужасно, 5 – отлично):")
        await state.set_state(UserStates.waiting_mood_value)
        await callback.answer()

    @dp.message(UserStates.waiting_mood_value)
    async def mood_log_value(message: types.Message, state: FSMContext):
        try:
            mood = int(message.text.strip())
            if mood < 1 or mood > 5:
                raise ValueError
            await state.update_data(mood=mood)
            await message.answer("Напишите короткий комментарий (необязательно, можно пропустить, отправив '-'):")
            await state.set_state(UserStates.waiting_mood_comment)
        except:
            await message.answer("Пожалуйста, введите число от 1 до 5.")

    @dp.message(UserStates.waiting_mood_comment)
    async def mood_log_comment(message: types.Message, state: FSMContext):
        data = await state.get_data()
        mood = data.get("mood")
        comment = message.text.strip()
        if comment == "-":
            comment = ""
        user_id = message.from_user.id
        log_mood(user_id, mood, comment)
        await message.answer("✅ Ваше настроение сохранено. Спасибо!", reply_markup=main_menu)
        await state.clear()

    @dp.callback_query(F.data == "mood_graph")
    async def mood_graph(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        moods = get_week_moods(user_id)
        if not moods:
            await callback.message.answer("Нет данных за последнюю неделю. Записывайте настроение, чтобы увидеть график.")
            await callback.answer()
            return
        text = "📊 *Ваше настроение за последние 7 дней:*\n\n"
        for date, mood, comment in moods:
            emoji = "😞" if mood <= 2 else "😐" if mood == 3 else "😊"
            text += f"📅 {date}: {emoji} {mood}/5"
            if comment:
                text += f" – {comment}"
            text += "\n"
        prompt = f"Настроение пользователя за последнюю неделю: {[(date, mood, comment) for date, mood, comment in moods]}. Дай короткий психологический анализ и совет (2-3 предложения)."
        response = await get_yandex_gpt_response(prompt, user_id)
        text += f"\n🧠 *Анализ:*\n{response}"
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=main_menu)
        await callback.answer()

    @dp.callback_query(F.data == "psycho_back")
    async def psycho_back(callback: types.CallbackQuery):
        await callback.message.answer("🧠 Психологический раздел:", reply_markup=psycho_submenu)
        await callback.answer()

    # ---------- БЫСТРЫЕ ТЕМЫ ----------
    @dp.callback_query(F.data.startswith("quick_topic_"))
    async def handle_quick_topic(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        user_id = callback.from_user.id
        topic = callback.data.split("_")[-1]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала укажите дату рождения через кнопку «Моё число» или /start.", reply_markup=menu_button)
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
            "psychology": "психологических аспектах, эмоциях, привычках"
        }
        query = topics_map.get(topic, "интересующей теме")
        prompt = f"Человек с числом судьбы {destiny} по имени {name} спрашивает о {query}. Дай развёрнутый ответ (5-7 предложений) с конкретными советами."
        status_msg = await callback.message.answer("🧐 Аркадий Викторович размышляет...")
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        last_answer[user_id] = response
        await callback.message.answer(f"✨ *{topic.capitalize()}*\n\n{response}", parse_mode="Markdown", reply_markup=share_button)

    # ---------- МОЯ МАТРИЦА ----------
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
            await message.answer("Сначала укажите дату рождения через кнопку «Моё число» или /start.", reply_markup=menu_button)
            return
        destiny = row[0]
        cache_key = f"matrix_{destiny}"
        cached = get_cached_response(user_id, cache_key)
        if cached:
            response = cached
        else:
            status_msg = await message.answer("📜 Аркадий Викторович составляет вашу матрицу... Это может занять до 10 секунд.")
            prompt = f"Составь полную матрицу судьбы для числа {destiny}. Дай развёрнутую характеристику (10-15 предложений) по арканам."
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            save_cached_response(user_id, cache_key, response)
        last_answer[user_id] = response
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
                await message.answer("Сначала укажите свою дату рождения через кнопку «Моё число» или /start.", reply_markup=menu_button)
                await state.clear()
                return
            my_destiny = row[0]
            status_msg = await message.answer("🔍 Анализирую совместимость...")
            prompt = f"Число судьбы пользователя {my_destiny}, число партнёра {partner_destiny}. Опиши совместимость (5-7 предложений) с советами."
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            last_answer[user_id] = response
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
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай короткий прогноз (3-5 предложений) с практическим действием. Также добавь одну психологическую практику."
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        last_answer[user_id] = response
        await message.answer(f"🎁 *Карта дня*\n\n{response}", parse_mode="Markdown", reply_markup=share_button)

    # ---------- ЗАДАТЬ ВОПРОС ----------
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
            last_answer[user_id] = response
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

    # ---------- ПРОФИЛЬ ----------
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
        remaining = get_free_questions_remaining(user_id)
        text = (f"┌─────────────────────┐\n"
                f"│ 👤 Имя: {name}\n"
                f"│ 🎂 Дата: {birth}\n"
                f"│ 🔢 Число: {destiny}\n"
                f"│ 💳 Подписка: {sub_status}\n"
                f"│ 📅 До: {sub_end}\n"
                f"│ 🎁 Бесплатных вопросов: {remaining}/5\n"
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
        await callback.message.answer("Введите новую дату рождения в формате ДД.ММ.ГГГГ:")
        await state.set_state(UserStates.waiting_new_birth)
        await callback.answer()

    @dp.message(UserStates.waiting_new_birth)
    async def change_birth_save(message: types.Message, state: FSMContext):
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
                return
            destiny = calculate_destiny_number(birth_date)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET birth_date = ?, destiny_number = ? WHERE user_id = ?", (birth_date, destiny, user_id))
            conn.commit()
            conn.close()
            delete_user_cache(user_id)
            update_last_active(user_id)
            await message.answer(f"Дата рождения изменена. Ваше новое число судьбы: {destiny}")
            # Сразу показываем характеристику
            cached = get_cached_response(user_id, f"birth_{destiny}")
            if cached:
                response = cached
            else:
                status_msg = await message.answer("🧐 Аркадий Викторович изучает ваш новый гороскоп...")
                prompt = f"Число судьбы {destiny}. Дай краткую характеристику (2-3 предложения), назови слабость и дай совет."
                response = await get_yandex_gpt_response(prompt, user_id)
                await status_msg.delete()
                save_cached_response(user_id, f"birth_{destiny}", response)
            await message.answer(f"🔢 Ваше число судьбы: {destiny}\n\n{response}", reply_markup=quick_topics_menu, parse_mode=None)
        except:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ")
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
            "• Сменить имя или дату рождения – кнопки в профиле",
            parse_mode="Markdown", reply_markup=menu_button
        )
        await callback.answer()

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
        add_subscription_days(user_id, action_days, check_referral=True, admin_id=0)
        cursor.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code=?", (code,))
        cursor.execute("INSERT INTO promocode_activations (user_id, code, activated_at, result_text) VALUES (?, ?, ?, ?)",
                       (user_id, code, datetime.datetime.now().isoformat(), f"+{action_days} дней"))
        conn.commit()
        conn.close()
        await message.answer(f"🎉 Поздравляем! Вы активировали промокод +{action_days} дней подписки.", reply_markup=menu_button)
        await state.clear()

    # ---------- ЧЕЛЛЕНДЖ ----------
    @dp.callback_query(F.data == "start_challenge")
    async def start_challenge_callback(callback: types.CallbackQuery):
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
    async def complete_challenge_day_callback(callback: types.CallbackQuery):
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
    async def show_challenge_progress(callback: types.CallbackQuery):
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

    # ---------- ОБЩИЕ CALLBACK ----------
    @dp.callback_query(F.data == "close")
    async def close_profile(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "back_to_menu")
    async def back_to_menu_callback(callback: types.CallbackQuery):
        await callback.message.answer("Главное меню", reply_markup=main_menu)
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "share_result")
    async def share_result(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        last = last_answer.get(user_id, "результат вашего обращения")
        text = f"🔮 Мой нумерологический разбор от Аркадия Викторовича:\n\n«{last[:200]}»\n\nУзнайте свою судьбу -> https://t.me/NumerologArkadiy_bot"
        await callback.message.answer(text, reply_markup=menu_button)
        await callback.answer()

    @dp.callback_query(F.data == "gift")
    async def gift_subscription(callback: types.CallbackQuery):
        await callback.message.answer("Функция «Подарить подписку» в разработке. Скоро появится.")
        await callback.answer()

    @dp.callback_query()
    async def other_callbacks(callback: types.CallbackQuery):
        await callback.answer("В разработке", show_alert=True)

    @dp.message(Command("menu"))
    async def menu_command(message: types.Message):
        await message.answer("Главное меню", reply_markup=main_menu)

    @dp.message(Command("mynumber"))
    async def mynumber_command(message: types.Message):
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
        await message.answer(f"Ваше число судьбы: *{destiny}*. Хотите подробнее? Нажмите «Моё число» в меню.", parse_mode="Markdown")

    @dp.message(Command("cancel"))
    async def cancel_handler(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu)

    @dp.message(Command("unsubscribe_daily"))
    async def unsubscribe_daily(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET send_daily = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await message.answer("Вы отписались от ежедневной карты дня.")

    @dp.message(Command("subscribe_daily"))
    async def subscribe_daily(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET send_daily = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await message.answer("Вы подписались на ежедневную карту дня. Она будет приходить в 12:00.")