import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import main_menu, psycho_submenu
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    update_last_active,
    save_psycho_result,
    get_psycho_result,
    log_mood,
    get_week_moods,
    add_xp,
    get_zodiac_sign,
    save_mood,
    get_user_subscription_status,
    get_user_gender
)
from utils.notifications import get_subscription_button

router = Router()

class PsychoStates(StatesGroup):
    waiting_psycho_question = State()
    waiting_mood_value = State()
    waiting_mood_comment = State()
    waiting_stress_answer = State()
    waiting_personality_answer = State()

# ==================== ВОПРОСЫ ДЛЯ ТЕСТОВ ====================
PSYCHO_QUESTIONS = [
    {
        "text": "Как вы обычно реагируете на стресс?",
        "options": ["Спокойно, анализирую", "Нервничаю, но беру себя в руки", "Паникую", "Замыкаюсь в себе"]
    },
    {
        "text": "Что вас мотивирует больше всего?",
        "options": ["Деньги и статус", "Признание и похвала", "Саморазвитие", "Гармония в отношениях"]
    },
    {
        "text": "Как вы принимаете важные решения?",
        "options": ["Логически взвешиваю", "Прислушиваюсь к интуиции", "Советуюсь с близкими", "Действую импульсивно"]
    },
    {
        "text": "Что вас чаще всего раздражает в других?",
        "options": ["Ложь", "Некомпетентность", "Эгоизм", "Медлительность"]
    },
    {
        "text": "Опишите своё отношение к критике",
        "options": ["Воспринимаю конструктивно", "Обижаюсь, но обдумываю", "Игнорирую", "Агрессивно реагирую"]
    }
]

STRESS_QUESTIONS = [
    "Как часто вы чувствуете напряжение в течение дня?",
    "Сложно ли вам расслабиться после работы?",
    "Часто ли вы испытываете беспокойство без видимой причины?",
    "Как часто вы чувствуете усталость даже после сна?",
    "Сложно ли вам сосредоточиться на задачах?",
    "Как часто вы чувствуете раздражение на окружающих?",
    "Бывает ли у вас бессонница из-за переживаний?",
    "Чувствуете ли вы, что не справляетесь с нагрузкой?",
    "Как часто вы испытываете физический дискомфорт из-за стресса (головные боли, давление)?",
    "Как часто вы чувствуете эмоциональное истощение?"
]
STRESS_OPTIONS = ["Никогда / Почти никогда", "Иногда", "Часто", "Почти всегда"]

PERSONALITY_QUESTIONS = [
    "Я предпочитаю работать в команде, а не в одиночку.",
    "Я часто переживаю о том, что обо мне думают другие.",
    "Я люблю порядок и планирование.",
    "Мне легко знакомиться с новыми людьми.",
    "Я часто чувствую тревогу перед важными событиями.",
    "Я предпочитаю импровизировать, а не следовать плану.",
    "Мне важно помогать другим людям.",
    "Я легко адаптируюсь к изменениям.",
    "Я часто задумываюсь о смысле жизни и своих целях.",
    "Мне сложно выражать свои эмоции.",
    "Я предпочитаю стабильность и предсказуемость.",
    "Я часто нахожусь в творческом поиске."
]
PERSONALITY_OPTIONS = ["Полностью не согласен", "Скорее не согласен", "Нейтрально", "Скорее согласен", "Полностью согласен"]

# ==================== ОБРАБОТЧИКИ ====================
@router.message(F.text == "🧠 ПСИХОЛОГИЯ")
async def psychology_menu(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Эта функция доступна только в личном чате.")
        return
    await message.answer(
        "🧠 <b>Психологический раздел</b>\n\n"
        "Выберите, что вас интересует:\n"
        "• Психотест – 5 вопросов, результат с рекомендациями.\n"
        "• Дневник настроения – запись и анализ за неделю.\n"
        "• Самодиагностика стресса – 10 вопросов, уровень стресса и советы.\n"
        "• Тип личности – 12 вопросов, полное описание вашего типа.",
        parse_mode="HTML",
        reply_markup=psycho_submenu
    )

# ---------- ПСИХОТЕСТ (5 вопросов) ----------
@router.callback_query(F.data == "psycho_test")
async def start_psycho_test(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await state.update_data(psycho_step=0, psycho_answers=[])
    q = PSYCHO_QUESTIONS[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"psycho_ans_{i}")] for i, opt in enumerate(q["options"])
    ])
    await callback.message.answer(
        f"🧠 <b>Психологический тест</b>\n\nВопрос 1 из {len(PSYCHO_QUESTIONS)}:\n\n{q['text']}",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(PsychoStates.waiting_psycho_question)
    await callback.answer()

@router.callback_query(PsychoStates.waiting_psycho_question, F.data.startswith("psycho_ans_"))
async def process_psycho_answer(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    data = await state.get_data()
    step = data.get("psycho_step", 0)
    answers = data.get("psycho_answers", [])
    ans_index = int(callback.data.split("_")[-1])
    answers.append(ans_index)
    step += 1
    if step < len(PSYCHO_QUESTIONS):
        await state.update_data(psycho_step=step, psycho_answers=answers)
        q = PSYCHO_QUESTIONS[step]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"psycho_ans_{i}")] for i, opt in enumerate(q["options"])
        ])
        await callback.message.answer(
            f"Вопрос {step+1} из {len(PSYCHO_QUESTIONS)}:\n\n{q['text']}",
            reply_markup=kb
        )
    else:
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)
        gender = get_user_gender(user_id)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        destiny = row[0] if row else "неизвестно"
        name = row[1] if row else "пользователь"
        status_msg = await callback.message.answer("🧠 Анализирую ваши ответы...")
        if is_subscriber:
            prompt = (
                f"Пользователь {name} с числом судьбы {destiny} ответил на вопросы психологического теста: {answers}. "
                f"Вопросы: {[q['text'] for q in PSYCHO_QUESTIONS]}. "
                "Дай развёрнутую характеристику личности (7-9 предложений), укажи сильные стороны, слабости, дай практический совет. "
                "Будь прямолинеен, но не груб. Используй стиль Аркадия Викторовича. "
                "Используй HTML-форматирование для структурирования ответа."
            )
            response = await get_yandex_gpt_response(prompt, user_id, function_name="psycho_test", gender=gender)
            reply_markup = main_menu
        else:
            prompt = (
                f"Пользователь {name} с числом судьбы {destiny} ответил на вопросы психологического теста: {answers}. "
                f"Вопросы: {[q['text'] for q in PSYCHO_QUESTIONS]}. "
                "Дай характеристику личности (4-5 предложений): укажи 2 сильные стороны, 1 слабость, 1 совет. "
                "В конце добавь фразу: «Хотите получить полный анализ личности с практическими рекомендациями? Оформите подписку». "
                "Используй HTML-форматирование."
            )
            response = await get_yandex_gpt_response(prompt, user_id, function_name="psycho_test", gender=gender)
            reply_markup = get_subscription_button()
        await status_msg.delete()
        save_psycho_result(user_id, response)
        add_xp(user_id, "test_passed")
        await callback.message.answer(
            f"🧠 <b>Результат теста</b>\n\n{response}",
            parse_mode="HTML",
            reply_markup=reply_markup or main_menu
        )
        await state.clear()
    await callback.answer()

# ---------- САМОДИАГНОСТИКА СТРЕССА ----------
@router.callback_query(F.data == "stress_test")
async def start_stress_test(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await state.update_data(stress_step=0, stress_answers=[])
    q = STRESS_QUESTIONS[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"stress_ans_{i}")] for i, opt in enumerate(STRESS_OPTIONS)
    ])
    await callback.message.answer(
        f"🧠 <b>Самодиагностика стресса</b>\n\nВопрос 1 из {len(STRESS_QUESTIONS)}:\n\n{q}",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(PsychoStates.waiting_stress_answer)
    await callback.answer()

@router.callback_query(PsychoStates.waiting_stress_answer, F.data.startswith("stress_ans_"))
async def process_stress_answer(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    data = await state.get_data()
    step = data.get("stress_step", 0)
    answers = data.get("stress_answers", [])
    ans_index = int(callback.data.split("_")[-1])
    answers.append(ans_index)  # 0-3
    step += 1
    if step < len(STRESS_QUESTIONS):
        await state.update_data(stress_step=step, stress_answers=answers)
        q = STRESS_QUESTIONS[step]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"stress_ans_{i}")] for i, opt in enumerate(STRESS_OPTIONS)
        ])
        await callback.message.answer(
            f"Вопрос {step+1} из {len(STRESS_QUESTIONS)}:\n\n{q}",
            reply_markup=kb
        )
    else:
        user_id = callback.from_user.id
        gender = get_user_gender(user_id)
        total_score = sum(answers)  # max 30 (0-3 каждый)
        # Интерпретация
        if total_score <= 10:
            level = "низкий"
            recommendation = "Ваш уровень стресса низкий. Продолжайте заботиться о себе и поддерживать баланс."
        elif total_score <= 20:
            level = "средний"
            recommendation = "У вас средний уровень стресса. Рекомендуется уделять больше времени отдыху и релаксации. Попробуйте дыхательные практики или короткие медитации."
        else:
            level = "высокий"
            recommendation = "У вас высокий уровень стресса. Важно найти способы снижения нагрузки: обратитесь к специалисту, начните практиковать осознанность, больше отдыхайте."
        # Дополнительный совет через YandexGPT
        status_msg = await callback.message.answer("🧠 Аркадий Викторович анализирует ваш уровень стресса...")
        prompt = f"Уровень стресса пользователя: {level} (сумма баллов {total_score}). Дай развёрнутый совет (5-7 предложений) с практическими рекомендациями по управлению стрессом. Будь тёплым и поддерживающим. Используй HTML-форматирование."
        response = await get_yandex_gpt_response(prompt, user_id, function_name="stress_analysis", gender=gender)
        await status_msg.delete()
        # Сохраняем результат
        result_text = f"<b>Уровень стресса:</b> {level} (баллы: {total_score})\n\n<b>Рекомендации:</b>\n{recommendation}\n\n{response}"
        save_psycho_result(user_id, result_text)
        await callback.message.answer(
            f"🧠 <b>Результат диагностики стресса</b>\n\n{result_text}",
            parse_mode="HTML",
            reply_markup=main_menu
        )
        await state.clear()
    await callback.answer()

# ---------- ТИП ЛИЧНОСТИ ----------
@router.callback_query(F.data == "personality_test")
async def start_personality_test(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await state.update_data(personality_step=0, personality_answers=[])
    q = PERSONALITY_QUESTIONS[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"person_ans_{i}")] for i, opt in enumerate(PERSONALITY_OPTIONS)
    ])
    await callback.message.answer(
        f"🧠 <b>Тип личности</b>\n\nВопрос 1 из {len(PERSONALITY_QUESTIONS)}:\n\n{q}\n\nОцените, насколько вы согласны с утверждением:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(PsychoStates.waiting_personality_answer)
    await callback.answer()

@router.callback_query(PsychoStates.waiting_personality_answer, F.data.startswith("person_ans_"))
async def process_personality_answer(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    data = await state.get_data()
    step = data.get("personality_step", 0)
    answers = data.get("personality_answers", [])
    ans_index = int(callback.data.split("_")[-1])  # 0-4
    answers.append(ans_index)
    step += 1
    if step < len(PERSONALITY_QUESTIONS):
        await state.update_data(personality_step=step, personality_answers=answers)
        q = PERSONALITY_QUESTIONS[step]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"person_ans_{i}")] for i, opt in enumerate(PERSONALITY_OPTIONS)
        ])
        await callback.message.answer(
            f"Вопрос {step+1} из {len(PERSONALITY_QUESTIONS)}:\n\n{q}",
            reply_markup=kb
        )
    else:
        user_id = callback.from_user.id
        gender = get_user_gender(user_id)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        name = row[0] if row else "пользователь"
        status_msg = await callback.message.answer("🧠 Аркадий Викторович анализирует ваш тип личности...")
        # Преобразуем ответы в текстовое описание для YandexGPT
        answers_text = ", ".join([f"вопрос {i+1}: {PERSONALITY_OPTIONS[a]}" for i, a in enumerate(answers)])
        prompt = (
            f"Пользователь {name} ответил на 12 вопросов по модели «Большая пятёрка». Ответы: {answers_text}. "
            "Составь развёрнутое описание типа личности (8-10 предложений): укажи ключевые черты, сильные стороны, зоны роста, "
            "рекомендации по саморазвитию и взаимодействию с людьми. "
            "Будь тёплым, профессиональным, используй стиль Аркадия Викторовича. "
            "Используй HTML-форматирование."
        )
        response = await get_yandex_gpt_response(prompt, user_id, function_name="personality_analysis", gender=gender)
        await status_msg.delete()
        save_psycho_result(user_id, response)
        await callback.message.answer(
            f"🧠 <b>Ваш тип личности</b>\n\n{response}",
            parse_mode="HTML",
            reply_markup=main_menu
        )
        await state.clear()
    await callback.answer()

# ---------- ДНЕВНИК НАСТРОЕНИЯ ----------
@router.callback_query(F.data == "mood_diary")
async def mood_diary_menu(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Записать настроение", callback_data="mood_log")],
        [InlineKeyboardButton(text="📊 Мой график", callback_data="mood_graph")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="psycho_back")]
    ])
    await callback.message.answer(
        "😊 <b>Дневник настроения</b>\n\nЗаписывайте своё настроение и смотрите динамику.",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data == "mood_log")
async def mood_log_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Ужасно", callback_data="mood_1"),
         InlineKeyboardButton(text="2️⃣ Плохо", callback_data="mood_2"),
         InlineKeyboardButton(text="3️⃣ Нормально", callback_data="mood_3"),
         InlineKeyboardButton(text="4️⃣ Хорошо", callback_data="mood_4"),
         InlineKeyboardButton(text="5️⃣ Отлично", callback_data="mood_5")]
    ])
    await callback.message.answer("Оцените ваше настроение сегодня:", reply_markup=kb)
    await state.set_state(PsychoStates.waiting_mood_value)
    await callback.answer()

@router.callback_query(PsychoStates.waiting_mood_value, F.data.startswith("mood_"))
async def mood_log_value(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    mood = int(callback.data.split("_")[1])
    await state.update_data(mood=mood)
    await callback.message.answer("Напишите короткий комментарий (необязательно, можно пропустить, отправив '-'):")
    await state.set_state(PsychoStates.waiting_mood_comment)
    await callback.answer()

@router.message(PsychoStates.waiting_mood_comment)
async def mood_log_comment(message: types.Message, state: FSMContext):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        await state.clear()
        return
    data = await state.get_data()
    mood = data.get("mood")
    comment = message.text.strip()
    if comment == "-":
        comment = ""
    user_id = message.from_user.id
    log_mood(user_id, mood, comment)
    add_xp(user_id, "mood_log_7_days")
    await message.answer("✅ Ваше настроение сохранено. Спасибо!", reply_markup=main_menu)
    await state.clear()

@router.callback_query(F.data == "mood_graph")
async def mood_graph(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    is_subscriber = get_user_subscription_status(user_id)
    gender = get_user_gender(user_id)
    moods = get_week_moods(user_id)
    if not moods:
        await callback.message.answer("Нет данных за последнюю неделю. Записывайте настроение, чтобы увидеть график.")
        await callback.answer()
        return
    text = "📊 <b>Ваше настроение за последние 7 дней:</b>\n\n"
    for date, mood, comment in moods:
        emoji = "😞" if mood <= 2 else "😐" if mood == 3 else "😊"
        text += f"📅 {date}: {emoji} {mood}/5"
        if comment:
            text += f" – {comment}"
        text += "\n"
    status_msg = await callback.message.answer("🧠 Анализирую динамику...")
    if is_subscriber:
        prompt = (
            f"Настроение пользователя за последнюю неделю: {[(date, mood, comment) for date, mood, comment in moods]}. "
            "Дай развёрнутый психологический анализ (5-6 предложений) и практический совет, как улучшить эмоциональное состояние. "
            "Используй HTML-форматирование."
        )
        response = await get_yandex_gpt_response(prompt, user_id, function_name="mood_analysis", gender=gender)
        reply_markup = main_menu
    else:
        prompt = (
            f"Настроение пользователя за последнюю неделю: {[(date, mood, comment) for date, mood, comment in moods]}. "
            "Дай короткий анализ (3-4 предложения) и один совет. В конце добавь фразу: «Полный анализ и практики по улучшению настроения – по подписке». "
            "Используй HTML-форматирование."
        )
        response = await get_yandex_gpt_response(prompt, user_id, function_name="mood_analysis", gender=gender)
        reply_markup = get_subscription_button()
    await status_msg.delete()
    text += f"\n🧠 <b>Анализ:</b>\n{response}"
    await callback.message.answer(text, parse_mode="HTML", reply_markup=reply_markup or main_menu)
    await callback.answer()

@router.callback_query(F.data == "my_psycho_result")
async def show_my_psycho_result(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    result, created_at = get_psycho_result(user_id)
    if result:
        await callback.message.answer(
            f"📘 <b>Ваш последний результат</b> (от {created_at[:10]}):\n\n{result}",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer("Вы ещё не проходили тесты. Пройдите их, чтобы получить результат.")
    await callback.answer()

@router.callback_query(F.data == "psycho_back")
async def psycho_back(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "🧠 Психологический раздел:",
        reply_markup=psycho_submenu
    )
    await callback.answer()