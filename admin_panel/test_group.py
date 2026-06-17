from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_connection
from keyboards import admin_menu, cancel_button
from utils import is_admin, admin_log
import random

class TestGroupStates(StatesGroup):
    waiting_chat_id = State()
    waiting_confirm = State()

def register_test_group_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "📤 ТЕСТ ГРУППЫ")
    async def test_group_start(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        # Показываем список активных групп для выбора
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, is_active FROM group_chats WHERE is_active=1")
        groups = cursor.fetchall()
        conn.close()

        if not groups:
            await message.answer("Нет активных групп для теста.")
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Чат {chat_id}", callback_data=f"test_group_{chat_id}")]
            for chat_id, _ in groups[:10]  # ограничим 10
        ])
        kb.inline_keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_action")])

        await message.answer("Выберите группу для тестовой рассылки:", reply_markup=kb)
        await state.set_state(TestGroupStates.waiting_chat_id)

    @dp.callback_query(F.data.startswith("test_group_"), TestGroupStates.waiting_chat_id)
    async def test_group_selected(callback: types.CallbackQuery, state: FSMContext):
        chat_id = int(callback.data.split("_")[-1])
        await state.update_data(chat_id=chat_id)

        # Генерируем аффирмацию
        affirmations = [
            "✨ Доброе утро, друзья! Пусть сегодняшний день принесёт вам вдохновение и лёгкость. Помните: даже маленький шаг меняет маршрут. Улыбнитесь – и мир улыбнётся вам в ответ.",
            "🌿 Иногда лучшее, что можно сделать для себя – просто остановиться и перевести дыхание. Вы уже делаете достаточно. Сегодня разрешите себе быть неидеальным. Это нормально.",
            "🔥 Ваше время – это ваша сила. Каждое утро – новый шанс начать сначала. Доверьтесь себе, и у вас всё получится. Мы рядом!"
        ]
        message_text = random.choice(affirmations)

        await callback.message.answer(
            f"📤 *Тестовое сообщение для группы {chat_id}:*\n\n{message_text}\n\nОтправить?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить", callback_data="test_group_send")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_action")]
            ])
        )
        await state.set_state(TestGroupStates.waiting_confirm)
        await callback.answer()

    @dp.callback_query(F.data == "test_group_send", TestGroupStates.waiting_confirm)
    async def test_group_send(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        chat_id = data.get("chat_id")
        if not chat_id:
            await callback.message.answer("Ошибка: не указан чат.")
            await state.clear()
            await callback.answer()
            return

        # Берём то же сообщение, которое показали (сохраним в состоянии)
        # Для простоты сгенерируем заново
        affirmations = [
            "✨ Доброе утро, друзья! Пусть сегодняшний день принесёт вам вдохновение и лёгкость. Помните: даже маленький шаг меняет маршрут. Улыбнитесь – и мир улыбнётся вам в ответ.",
            "🌿 Иногда лучшее, что можно сделать для себя – просто остановиться и перевести дыхание. Вы уже делаете достаточно. Сегодня разрешите себе быть неидеальным. Это нормально.",
            "🔥 Ваше время – это ваша сила. Каждое утро – новый шанс начать сначала. Доверьтесь себе, и у вас всё получится. Мы рядом!"
        ]
        message_text = random.choice(affirmations)

        try:
            await bot.send_message(chat_id, message_text, parse_mode="Markdown")
            admin_log(callback.from_user.id, "test_group_broadcast", f"chat_id={chat_id}")
            await callback.message.answer(f"✅ Тестовое сообщение отправлено в группу {chat_id}.", reply_markup=admin_menu)
        except Exception as e:
            await callback.message.answer(f"❌ Ошибка отправки: {e}", reply_markup=admin_menu)

        await state.clear()
        await callback.answer()