from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_connection
from keyboards import admin_menu
from utils import is_admin, admin_log

class GroupSettingsStates(StatesGroup):
    waiting_frequency = State()

def register_groups_management_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "👥 УПРАВЛЕНИЕ ГРУППАМИ")
    async def groups_management_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 ГЛОБАЛЬНАЯ ЧАСТОТА", callback_data="admin_global_frequency")],
            [InlineKeyboardButton(text="📋 СПИСОК ВСЕХ ГРУПП", callback_data="admin_list_all_groups")],
            [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_back")]
        ])
        await message.answer("👥 *Управление группами*\n\nВыберите действие:", parse_mode="Markdown", reply_markup=kb)

    @dp.callback_query(F.data == "admin_list_all_groups")
    async def list_all_groups(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, is_active, frequency, created_at FROM group_chats ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await callback.message.edit_text("📭 Нет активных групп.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]]))
            await callback.answer()
            return

        for row in rows:
            chat_id, is_active, freq, created_at = row
            try:
                chat = await bot.get_chat(chat_id)
                chat_name = chat.title or chat.first_name or str(chat_id)
                chat_username = chat.username
                invite_link = chat.invite_link
            except Exception:
                chat_name = f"Чат {chat_id}"
                chat_username = None
                invite_link = None

            status = "✅ Активна" if is_active else "❌ Неактивна"
            text = f"📌 *{chat_name}*\n"
            text += f"ID: `{chat_id}`\n"
            text += f"Статус: {status}\n"
            text += f"Частота: {freq} сообщ/час\n"
            text += f"📅 Дата: {created_at[:10]}\n"

            link = None
            if chat_username:
                link = f"https://t.me/{chat_username}"
            elif invite_link:
                link = invite_link
            else:
                try:
                    new_link = await bot.create_chat_invite_link(chat_id, member_limit=1)
                    link = new_link.invite_link
                except:
                    try:
                        chat_obj = await bot.get_chat(chat_id)
                        if chat_obj.type in ("supergroup", "group"):
                            link = f"https://t.me/c/{str(chat_id)[4:]}"
                    except:
                        link = None

            kb_buttons = []
            if link:
                kb_buttons.append([InlineKeyboardButton(text="🔗 Перейти в чат", url=link)])
            else:
                kb_buttons.append([InlineKeyboardButton(text="📋 Скопировать ID", callback_data=f"copy_id_{chat_id}")])
            kb_buttons.append([InlineKeyboardButton(text=f"📊 Частота ({freq})", callback_data=f"group_freq_{chat_id}")])
            kb_buttons.append([InlineKeyboardButton(text="🔄 Переключить статус", callback_data=f"group_toggle_{chat_id}")])
            kb_buttons.append([InlineKeyboardButton(text="🗑 Удалить из списка", callback_data=f"group_delete_{chat_id}")])
            kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

            await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)

        # Кнопка возврата в меню групп
        await callback.message.answer("🔙 Вернуться в меню групп", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]]))

    @dp.callback_query(F.data == "admin_groups_back")
    async def groups_back(callback: types.CallbackQuery):
        """Возврат в меню управления группами."""
        await callback.message.delete()
        # Повторно вызываем меню (используем callback.message как контейнер)
        # Лучше отправить новое сообщение с меню
        await callback.message.answer("👥 *Управление группами*\n\nВыберите действие:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 ГЛОБАЛЬНАЯ ЧАСТОТА", callback_data="admin_global_frequency")],
            [InlineKeyboardButton(text="📋 СПИСОК ВСЕХ ГРУПП", callback_data="admin_list_all_groups")],
            [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_back")]
        ]))
        await callback.answer()

    @dp.callback_query(F.data.startswith("copy_id_"))
    async def copy_chat_id(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        chat_id = callback.data.split("_")[-1]
        await callback.message.answer(f"📋 ID чата: `{chat_id}`\nСкопируйте его вручную.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("group_freq_"))
    async def change_group_frequency(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        chat_id = int(callback.data.split("_")[-1])
        await state.update_data(group_chat_id=chat_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1", callback_data="group_set_freq_1"),
             InlineKeyboardButton(text="2", callback_data="group_set_freq_2"),
             InlineKeyboardButton(text="3", callback_data="group_set_freq_3"),
             InlineKeyboardButton(text="4", callback_data="group_set_freq_4")],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_cancel_action")]
        ])
        await callback.message.answer(f"Выберите новую частоту для группы {chat_id} (сообщений в час):", reply_markup=kb)
        await state.set_state(GroupSettingsStates.waiting_frequency)
        await callback.answer()

    @dp.callback_query(F.data.startswith("group_set_freq_"), GroupSettingsStates.waiting_frequency)
    async def set_group_frequency(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        freq = int(callback.data.split("_")[-1])
        data = await state.get_data()
        chat_id = data.get("group_chat_id")
        if not chat_id:
            await callback.message.answer("Ошибка: не указан чат.")
            await state.clear()
            await callback.answer()
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE group_chats SET frequency = ? WHERE chat_id = ?", (freq, chat_id))
        conn.commit()
        conn.close()
        admin_log(callback.from_user.id, "change_group_frequency", f"chat_id={chat_id}, new_freq={freq}")
        await callback.message.answer(f"✅ Частота для группы {chat_id} изменена на {freq} сообщ/час.")
        await state.clear()
        await callback.answer()

    @dp.callback_query(F.data.startswith("group_toggle_"))
    async def toggle_group_status(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        chat_id = int(callback.data.split("_")[-1])
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM group_chats WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if not row:
            await callback.message.answer("Группа не найдена.")
            conn.close()
            await callback.answer()
            return
        new_status = 0 if row[0] else 1
        cursor.execute("UPDATE group_chats SET is_active = ? WHERE chat_id = ?", (new_status, chat_id))
        conn.commit()
        conn.close()
        status_text = "активирована" if new_status else "деактивирована"
        admin_log(callback.from_user.id, "toggle_group_status", f"chat_id={chat_id}, new_status={new_status}")
        await callback.message.answer(f"✅ Группа {chat_id} {status_text}.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("group_delete_"))
    async def delete_group_from_list(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        chat_id = int(callback.data.split("_")[-1])
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM group_chats WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        admin_log(callback.from_user.id, "delete_group", f"chat_id={chat_id}")
        await callback.message.answer(f"🗑 Группа {chat_id} удалена из списка.")
        await callback.answer()

    @dp.callback_query(F.data == "admin_global_frequency")
    async def set_global_frequency(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 сообщение в час", callback_data="admin_set_global_freq_1")],
            [InlineKeyboardButton(text="2 сообщения в час", callback_data="admin_set_global_freq_2")],
            [InlineKeyboardButton(text="3 сообщения в час", callback_data="admin_set_global_freq_3")],
            [InlineKeyboardButton(text="4 сообщения в час", callback_data="admin_set_global_freq_4")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]
        ])
        await callback.message.edit_text("🌐 *Глобальная частота*\n\nВыберите количество сообщений в час для всех групп (по умолчанию 2):", parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_set_global_freq_"))
    async def set_global_frequency_value(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        freq = int(callback.data.split("_")[-1])
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE group_chats SET frequency = ?", (freq,))
        conn.commit()
        conn.close()
        admin_log(callback.from_user.id, "set_global_frequency", f"new_freq={freq}")
        await callback.message.edit_text(f"✅ Глобальная частота установлена: {freq} сообщения в час для всех групп.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]]))
        await callback.answer()

    @dp.callback_query(F.data == "admin_back")
    async def admin_back(callback: types.CallbackQuery):
        """Возврат в админ-панель (обработчик из promocodes, но используется и здесь)."""
        await callback.message.delete()
        await callback.message.answer("Админ-панель", reply_markup=admin_menu)
        await callback.answer()