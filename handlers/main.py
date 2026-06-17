import datetime
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import main_menu, quick_topics_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import (
    get_user_subscription_status, get_free_questions_remaining, increment_free_query,
    get_cached_response, save_cached_response, add_xp, update_last_active,
    calculate_destiny_number, get_city_coords, get_weather_by_coords
)

class MainStates(StatesGroup):
    waiting_birth_date = State()
    waiting_partner_birth_date = State()
    waiting_question = State()

last_answer = {}
pending_matrix = {}

def register_main_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "🔢 МОЁ ЧИСЛО")
    async def show_my_number(message: types.Message):
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта функция доступна только в личном чате.")
            return
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала введите дату рождения через /start.")
            return
        destiny = row[1]
        cached = get_cached_response(user_id, f"birth_{destiny}")
        if cached:
            response = cached
        else:
            status_msg = await message.answer("🧐 Аркадий Викторович изучает ваш гороскоп...")
            prompt = f"Число судьбы {destiny}. Дай краткую характеристику (2-3 предложения), назови слабость и дай совет."
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
                save_cached_response(user_id, f"birth_{destiny}", response)
        add_xp(user_id, "daily_visit")
        # Отправляем клавиатуру только если не группа
        await message.answer(f"🔢 Ваше число судьбы: {destiny}\n\n{response}",
                             reply_markup=quick_topics_menu, parse_mode=None)

    async def process_matrix(user_id: int, destiny: int, name: str, bot: Bot, status_msg: types.Message, cache_key: str):
        prompt = f"Составь полную матрицу судьбы для числа {destiny}. Дай развёрнутую характеристику (10-15 предложений) по арканам."
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        if "Ошибка" not in response and "Нейросеть" not in response and "таймаут" not in response:
            save_cached_response(user_id, cache_key, response)
        pdf_share_menu = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Скачать PDF", callback_data="download_pdf")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ])
        await bot.send_message(user_id, f"🔮 *Матрица судьбы*\n\n{response}", parse_mode="Markdown", reply_markup=pdf_share_menu)
        pending_matrix.pop(user_id, None)

    @dp.message(F.text == "🔮 МОЯ МАТРИЦА")
    async def matrix_prompt(message: types.Message):
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта функция доступна только в личном чате.")
            return
        user_id = message.from_user.id
        if not get_user_subscription_status(user_id):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Купить подписку", callback_data="buy_subscription")],
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
            ])
            await message.answer("Полная матрица судьбы доступна только по подписке. Оформите подписку в профиле.", reply_markup=kb)
            return
        if user_id in pending_matrix:
            await message.answer("Матрица уже формируется, подождите немного. Как только будет готова – я пришлю.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала укажите дату рождения через кнопку «Моё число».", reply_markup=menu_button)
            return
        destiny = row[0]
        name = row[1] if row[1] else "пользователь"
        cache_key = f"matrix_{destiny}"
        cached = get_cached_response(user_id, cache_key)
        if cached:
            pdf_share_menu = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📄 Скачать PDF", callback_data="download_pdf")],
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
            ])
            await message.answer(f"🔮 *Матрица судьбы*\n\n{cached}", parse_mode="Markdown", reply_markup=pdf_share_menu)
            return
        status_msg = await message.answer("📜 Аркадий Викторович составляет вашу матрицу... Это может занять до 2 минут. Я пришлю результат отдельным сообщением.")
        pending_matrix[user_id] = status_msg
        asyncio.create_task(process_matrix(user_id, destiny, name, bot, status_msg, cache_key))

    @dp.callback_query(F.data == "download_pdf")
    async def download_pdf(callback: types.CallbackQuery):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Доступно только в личном чате.")
            await callback.answer()
            return
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала рассчитайте матрицу через кнопку «МОЯ МАТРИЦА».")
            await callback.answer()
            return
        destiny = row[0]
        name = row[1] if row[1] else "пользователь"
        cache_key = f"matrix_{destiny}"
        matrix_text = get_cached_response(user_id, cache_key)
        if not matrix_text:
            await callback.message.answer("Сначала рассчитайте матрицу через кнопку «МОЯ МАТРИЦА».")
            await callback.answer()
            return
        from utils import generate_pdf_matrix
        pdf_data = generate_pdf_matrix(user_id, name, destiny, matrix_text)
        if pdf_data:
            await callback.message.answer_document(
                types.BufferedInputFile(pdf_data, filename=f"matrix_{user_id}.pdf"),
                caption="📄 Ваша матрица судьбы в формате PDF"
            )
        else:
            await callback.message.answer("Ошибка генерации PDF. Попробуйте позже.")
        await callback.answer()

    @dp.message(F.text == "❤️ СОВМЕСТИМОСТЬ")
    async def ask_partner_birth(message: types.Message, state: FSMContext):
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта функция доступна только в личном чате.")
            return
        await message.answer("Введите дату рождения партнёра в формате ДД.ММ.ГГГГ")
        await state.set_state(MainStates.waiting_partner_birth_date)

    @dp.message(MainStates.waiting_partner_birth_date)
    async def process_compatibility(message: types.Message, state: FSMContext):
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта функция доступна только в личном чате.")
            await state.clear()
            return
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
                await message.answer("Сначала укажите свою дату рождения через кнопку «Моё число».", reply_markup=menu_button)
                await state.clear()
                return
            my_destiny = row[0]
            status_msg = await message.answer("🔍 Анализирую совместимость...")
            prompt = f"Число судьбы пользователя {my_destiny}, число партнёра {partner_destiny}. Опиши совместимость (5-7 предложений) с советами."
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            last_answer[user_id] = response
            # Отправляем без клавиатуры в группах (но здесь уже проверка есть)
            await message.answer(f"❤️ *Совместимость*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
            await state.clear()
        except Exception:
            await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ", reply_markup=menu_button)

    @dp.message(F.text == "🎁 КАРТА ДНЯ")
    async def daily_card(message: types.Message):
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта функция доступна только в личном чате.")
            return
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number, city FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        destiny = row[0] if row else "?"
        city = row[1] if row and row[1] else None
        
        weather_str = ""
        if city:
            lat, lon = await get_city_coords(city)
            if lat and lon:
                weather_str = await get_weather_by_coords(lat, lon)
                if weather_str and "Не удалось" not in weather_str and "Ошибка" not in weather_str:
                    weather_str = f"\n\n🌤️ *Погода в {city}:* {weather_str}"
                else:
                    weather_str = ""
        status_msg = await message.answer("🌙 Аркадий Викторович заглядывает в будущее...")
        prompt = f"Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай короткий прогноз (3-5 предложений) с практическим действием. Также добавь одну психологическую практику."
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        last_answer[user_id] = response
        await message.answer(f"🎁 *Карта дня*\n\n{response}{weather_str}", parse_mode="Markdown", reply_markup=menu_button)

    @dp.message(F.text == "💬 ЗАДАТЬ ВОПРОС")
    async def ask_question(message: types.Message, state: FSMContext):
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта функция доступна только в личном чате.")
            return
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
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта функция доступна только в личном чате.")
            await state.clear()
            return
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
            await message.answer(response, parse_mode=None, reply_markup=menu_button)
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
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта команда доступна только в личном чате.")
            return
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