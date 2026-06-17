from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_connection
from keyboards import admin_menu
from utils import is_admin

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
        await callback.message.edit_text(f"✅ Глобальная частота установлена: {freq} сообщения в час для всех групп.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]]))
        await callback.answer()

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
            await callback.message.edit_text("Нет активных групп.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]]))
            await callback.answer()
            return
        text = "📋 *Список групп:*\n\n"
        for row in rows:
            chat_id, is_active, freq, created_at = row
            status = "✅ Активна" if is_active else "❌ Неактивна"
            text += f"Чат: {chat_id}\nСтатус: {status}\nЧастота: {freq} сообщ/час\nДата: {created_at[:10]}\n\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]
        ])
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data == "admin_groups_back")
    async def groups_back(callback: types.CallbackQuery):
        await groups_management_menu(callback.message)
        await callback.answer()