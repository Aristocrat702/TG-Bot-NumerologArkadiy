from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import admin_menu, cancel_button
from database import (
    get_connection,
    get_group_collection_status,
    toggle_group_message_collection,
    get_group_messages,
    export_group_messages_csv
)
from utils import is_admin, admin_log

class GroupMessagesStates(StatesGroup):
    waiting_chat_id = State()
    waiting_limit = State()
    waiting_days = State()

def register_group_messages_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "📥 СБОР СООБЩЕНИЙ")
    async def collection_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, is_active, collect_messages FROM group_chats")
        groups = cursor.fetchall()
        conn.close()
        if not groups:
            await message.answer("Нет групп. Добавьте бота в группу и активируйте его.")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for chat_id, is_active, collect in groups:
            status = "✅ Вкл" if collect else "❌ Выкл"
            try:
                chat = await bot.get_chat(chat_id)
                name = chat.title or chat.first_name or str(chat_id)
            except:
                name = f"Чат {chat_id}"
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"{name} ({status})",
                    callback_data=f"group_collect_{chat_id}_{0 if collect else 1}"
                )
            ])
        kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
        await message.answer("📥 *Сбор сообщений в группах*\n\nНажмите на группу, чтобы включить/выключить сбор.", parse_mode="Markdown", reply_markup=kb)

    @dp.callback_query(F.data.startswith("group_collect_"))
    async def toggle_collect(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        parts = callback.data.split("_")
        chat_id = int(parts[2])
        new_status = bool(int(parts[3]))
        toggle_group_message_collection(chat_id, new_status)
        admin_log(callback.from_user.id, "toggle_collect", f"chat_id={chat_id}, status={new_status}")
        await callback.message.answer(f"✅ Сбор сообщений для группы {chat_id} {'включён' if new_status else 'выключён'}.")
        await callback.answer()

    @dp.message(F.text == "📤 ВЫГРУЗИТЬ СООБЩЕНИЯ")
    async def export_menu(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM group_chats WHERE collect_messages = 1")
        groups = cursor.fetchall()
        conn.close()
        if not groups:
            await message.answer("Нет групп со включённым сбором сообщений.")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Группа {chat_id}", callback_data=f"export_group_{chat_id}")] for chat_id, in groups
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]])
        await message.answer("Выберите группу для выгрузки:", reply_markup=kb)
        await state.set_state(GroupMessagesStates.waiting_chat_id)

    @dp.callback_query(F.data.startswith("export_group_"), GroupMessagesStates.waiting_chat_id)
    async def export_group_selected(callback: types.CallbackQuery, state: FSMContext):
        chat_id = int(callback.data.split("_")[-1])
        await state.update_data(chat_id=chat_id)
        await callback.message.answer("Введите количество сообщений (например, 100) или 0 для всех:", reply_markup=cancel_button())
        await state.set_state(GroupMessagesStates.waiting_limit)
        await callback.answer()

    @dp.message(GroupMessagesStates.waiting_limit)
    async def export_limit(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            limit = int(message.text.strip())
            if limit < 0:
                raise ValueError
            await state.update_data(limit=limit)
            await message.answer("Введите количество дней (например, 7) или 0 для всех времён:", reply_markup=cancel_button())
            await state.set_state(GroupMessagesStates.waiting_days)
        except:
            await message.answer("Ошибка. Введите целое положительное число.")

    @dp.message(GroupMessagesStates.waiting_days)
    async def export_days(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            days = int(message.text.strip())
            if days < 0:
                raise ValueError
            data = await state.get_data()
            chat_id = data.get("chat_id")
            limit = data.get("limit", 100)
            csv_data = export_group_messages_csv(chat_id, limit, days if days > 0 else None)
            await message.answer_document(
                types.BufferedInputFile(csv_data.encode('utf-8'), filename=f"group_{chat_id}_messages.csv"),
                caption=f"📊 Сообщения из группы {chat_id} (последние {limit}, за {days if days > 0 else 'все'} дней)"
            )
        except:
            await message.answer("Ошибка. Введите целое число дней (0 - все).")
        await state.clear()