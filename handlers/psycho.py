import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu, psycho_submenu
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import update_last_active, save_psycho_result, get_psycho_result, log_mood, get_week_moods, add_xp

class PsychoStates(StatesGroup):
    waiting_psycho_question = State()
    waiting_mood_value = State()
    waiting_mood_comment = State()

# Вопросы для психологического теста (с вариантами ответов)
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

def register_psycho_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "🧠 ПСИХОЛОГИЯ")
    async def psychology_menu(message: types.Message):
        await message.answer("🧠 *Психологический раздел*\n\nВыберите, что вас интересует:", parse_mode="Markdown", reply_markup=psycho_submenu)

    @dp.callback_query(F.data == "psycho_test")
    async def start_psycho_test(callback: types.CallbackQuery, state: FSMContext):
        await state.update_data(step=0, answers=[])
        q = PSYCHO_QUESTIONS[0]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"psycho_ans_{i}") for i, opt in enumerate(q["options"])]
        ])
        await callback.message.answer(f"🧠 *Психологический тест*\n\nВопрос 1 из {len(PSYCHO_QUESTIONS)}:\n\n{q['text']}", reply_markup=kb, parse_mode="Markdown")
        await state.set_state(PsychoStates.waiting_psycho_question)
        await callback.answer()

    @dp.callback_query(PsychoStates.waiting_psycho_question, F.data.startswith("psycho_ans_"))
    async def process_psycho_answer(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        step = data.get("step", 0)
        answers = data.get("answers", [])
        ans_index = int(callback.data.split("_")[-1])
        answers.append(ans_index)
        step += 1
        if step < len(PSYCHO_QUESTIONS):
            await state.update_data(step=step, answers=answers)
            q = PSYCHO_QUESTIONS[step]
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=opt, callback_data=f"psycho_ans_{i}") for i, opt in enumerate(q["options"])]
            ])
            await callback.message.answer(f"Вопрос {step+1} из {len(PSYCHO_QUESTIONS)}:\n\n{q['text']}", reply_markup=kb)
        else:
            # Все ответы собраны – отправляем в YandexGPT
            user_id = callback.from_user.id
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            destiny = row[0] if row else "неизвестно"
            name = row[1] if row else "пользователь"
            prompt = (
                f"Пользователь {name} с числом судьбы {destiny} ответил на вопросы психологического теста: {answers}. "
                f"Вопросы: {[q['text'] for q in PSYCHO_QUESTIONS]}. "
                "Дай развёрнутую характеристику личности (5-7 предложений), укажи сильные стороны, слабости и дай практический совет. "
                "Будь прямолинеен, но не груб. Используй стиль Аркадия Викторовича."
            )
            status_msg = await callback.message.answer("🧠 Анализирую ваши ответы...")
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            # Сохраняем результат
            save_psycho_result(user_id, response)
            add_xp(user_id, "test_passed")
            await callback.message.answer(f"🧠 *Результат теста*\n\n{response}", parse_mode="Markdown", reply_markup=main_menu)
            await state.clear()
        await callback.answer()

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

    @dp.callback_query(PsychoStates.waiting_mood_value, F.data.startswith("mood_"))
    async def mood_log_value(callback: types.CallbackQuery, state: FSMContext):
        mood = int(callback.data.split("_")[1])
        await state.update_data(mood=mood)
        await callback.message.answer("Напишите короткий комментарий (необязательно, можно пропустить, отправив '-'):")
        await state.set_state(PsychoStates.waiting_mood_comment)
        await callback.answer()

    @dp.message(PsychoStates.waiting_mood_comment)
    async def mood_log_comment(message: types.Message, state: FSMContext):
        data = await state.get_data()
        mood = data.get("mood")
        comment = message.text.strip()
        if comment == "-":
            comment = ""
        user_id = message.from_user.id
        log_mood(user_id, mood, comment)
        add_xp(user_id, "mood_log_7_days")  # ежедневная запись даёт опыт, но с проверкой на 7 дней – отдельно
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
        # Анализ через YandexGPT
        prompt = f"Настроение пользователя за последнюю неделю: {[(date, mood, comment) for date, mood, comment in moods]}. Дай короткий психологический анализ и совет (2-3 предложения)."
        response = await get_yandex_gpt_response(prompt, user_id)
        text += f"\n🧠 *Анализ:*\n{response}"
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=main_menu)
        await callback.answer()

    @dp.callback_query(F.data == "psycho_back")
    async def psycho_back(callback: types.CallbackQuery):
        await callback.message.answer("🧠 Психологический раздел:", reply_markup=psycho_submenu)
        await callback.answer()