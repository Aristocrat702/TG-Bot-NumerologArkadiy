# Упрощённый handlers/main.py (матрица без YandexGPT)
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu, share_button, quick_topics_menu, menu_button
from database import get_connection
from utils import get_user_subscription_status

class MainStates(StatesGroup):
    waiting_partner_birth_date = State()
    waiting_question = State()

last_answer = {}

def register_main_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "🔢 МОЁ ЧИСЛО")
    async def show_my_number(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала введите дату рождения через /start.")
            return
        destiny = row[0]
        await message.answer(f"🔢 Ваше число судьбы: {destiny}\n\nЭто число говорит о том, что вы... (здесь должна быть характеристика, но API временно не работает). Для получения полной матрицы оформите подписку.", reply_markup=quick_topics_menu)

    @dp.message(F.text == "🔮 МОЯ МАТРИЦА")
    async def matrix_prompt(message: types.Message):
        user_id = message.from_user.id
        if not get_user_subscription_status(user_id):
            await message.answer("Полная матрица судьбы доступна только по подписке. Оформите подписку в профиле.", reply_markup=menu_button)
            return
        # Заглушка
        response = "🔮 *Ваша матрица судьбы*\n\n1. Аркан Характер: Вы лидер.\n2. Аркан Деньги: Успех придет через творчество.\n3. Аркан Любовь: Вам нужен партнер-единомышленник.\n4. Аркан Здоровье: Следите за спиной.\n5. Кармические задачи: Научиться делегировать.\n\nЭто тестовый вывод. Полноценная матрица появится после настройки ИИ."
        pdf_share_menu = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Скачать PDF", callback_data="download_pdf")],
            [InlineKeyboardButton(text="📤 Поделиться результатом", callback_data="share_result")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ])
        await message.answer(f"🔮 *Матрица судьбы*\n\n{response}", parse_mode="Markdown", reply_markup=pdf_share_menu)

    @dp.callback_query(F.data == "download_pdf")
    async def download_pdf(callback: types.CallbackQuery):
        await callback.message.answer("PDF-отчёт временно недоступен. Ведутся технические работы.")
        await callback.answer()

    @dp.message(F.text == "❤️ СОВМЕСТИМОСТЬ")
    async def ask_partner_birth(message: types.Message, state: FSMContext):
        await message.answer("Введите дату рождения партнёра в формате ДД.ММ.ГГГГ")
        await state.set_state(MainStates.waiting_partner_birth_date)

    @dp.message(MainStates.waiting_partner_birth_date)
    async def process_compatibility(message: types.Message, state: FSMContext):
        await message.answer("Совместимость временно недоступна. Попробуйте позже.")
        await state.clear()

    @dp.message(F.text == "🎁 КАРТА ДНЯ")
    async def daily_card(message: types.Message):
        await message.answer("🎁 *Карта дня*\n\nСегодняшний прогноз: будьте внимательны к деталям. Хороший день для анализа.", parse_mode="Markdown")

    @dp.message(F.text == "💬 ЗАДАТЬ ВОПРОС")
    async def ask_question(message: types.Message, state: FSMContext):
        await message.answer("Функция вопросов временно недоступна. Ведутся работы по улучшению бота.")

    @dp.message(Command("mynumber"))
    async def mynumber_command(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT destiny_number FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await message.answer("Сначала введите дату рождения через /start.")
            return
        destiny = row[0]
        await message.answer(f"Ваше число судьбы: *{destiny}*.", parse_mode="Markdown")

    # Остальные обработчики (для совместимости с существующими кнопками)
    @dp.callback_query(F.data == "share_result")
    async def share_result(callback: types.CallbackQuery):
        await callback.message.answer("Функция шаринга временно недоступна.")
        await callback.answer()

    @dp.callback_query(F.data == "back_to_menu")
    async def back_to_menu_callback(callback: types.CallbackQuery):
        await callback.message.answer("Главное меню", reply_markup=main_menu)
        await callback.message.delete()
        await callback.answer()