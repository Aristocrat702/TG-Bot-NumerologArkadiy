import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu, profile_menu, psycho_submenu, share_button, quick_topics_menu, menu_button, main_menu, share_button, quick_topics_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    get_user_subscription_status, get_free_questions_remaining, increment_free_query,
    get_cached_response, save_cached_response, add_xp, update_last_active,
    calculate_destiny_number
)

class MainStates(StatesGroup):
    waiting_birth_date = State()
    waiting_partner_birth_date = State()
    waiting_question = State()

# Временное хранение последнего ответа для кнопки «Поделиться»
last_answer = {}

def register_main_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "🔢 МОЁ ЧИСЛО")
    async def show_my_number(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала введите дату рождения через /start или дождитесь опроса.")
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
        add_xp(user_id, "daily_visit")  # ежедневный вход (можно проверять)
        await message.answer(f"🔢 Ваше число судьбы: {destiny}\n\n{response}",
                             reply_markup=quick_topics_menu, parse_mode=None)

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

    @dp.message(F.text == "❤️ СОВМЕСТИМОСТЬ")
    async def ask_partner_birth(message: types.Message, state: FSMContext):
        await message.answer("Введите дату рождения партнёра в формате ДД.ММ.ГГГГ")
        await state.set_state(MainStates.waiting_partner_birth_date)

    @dp.message(MainStates.waiting_partner_birth_date)
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

    @dp.message(F.text == "💬 ЗАДАТЬ ВОПРОС")
    async def ask_question(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if get_user_subscription_status(user_id):
            await message.answer("Напишите ваш вопрос (по нумерологии или психологии). Я отвечу максимально честно.")
            await state.set_state(MainStates.waiting_question)
            return

        remaining = get_free_questions_remaining(user_id)
        if remaining > 0:
            await message.answer(f"У вас осталось *{remaining}* бесплатных вопросов на сегодня. Напишите вопрос, я дам короткий ответ. А в подписке – полная информация и развёрнутые консультации.\n\nВаш вопрос:", parse_mode="Markdown")
            await state.set_state(MainStates.waiting_question)
        else:
            await message.answer("Вы исчерпали лимит бесплатных вопросов на сегодня. Оформите подписку в профиле – и получите безлимитные консультации, полную матрицу и прогнозы.", reply_markup=menu_button)

    @dp.message(MainStates.waiting_question)
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
            add_xp(user_id, "ask_question")
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