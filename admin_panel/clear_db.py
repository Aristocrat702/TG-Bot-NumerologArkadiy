from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import admin_menu
from database import get_connection
from utils import is_admin, admin_log

def register_clear_db_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "🗑️ ОЧИСТКА БД")
    async def clear_db_start(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, очистить", callback_data="clear_db_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="clear_db_cancel")]
        ])
        await message.answer(
            "⚠️ *Вы уверены, что хотите очистить базу данных?*\n\n"
            "Будут удалены:\n"
            "• Все пользователи\n"
            "• История визитов\n"
            "• Диалоги\n"
            "• Сообщения из групп\n"
            "• Записи настроения\n"
            "• Результаты тестов\n"
            "• Прогресс челленджей\n"
            "• Достижения\n"
            "• Активации промокодов\n"
            "• Логи отправленных сообщений в группы\n\n"
            "Будут сохранены:\n"
            "• Настройки бота\n"
            "• Промпты\n"
            "• Промокоды\n"
            "• Чёрный список\n"
            "• Статьи (сексология и психология)\n\n"
            "Подтвердите действие:",
            parse_mode="Markdown",
            reply_markup=kb
        )

    @dp.callback_query(F.data == "clear_db_confirm")
    async def clear_db_confirm(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        
        tables_to_clear = [
            "users",
            "user_visits",
            "dialog_history",
            "group_messages",
            "mood_log",
            "psycho_results",
            "challenges",
            "achievements",
            "promocode_activations",
            "group_sent_log"
        ]
        
        conn = get_connection()
        cursor = conn.cursor()
        for table in tables_to_clear:
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()
        
        admin_log(callback.from_user.id, "clear_db", "База данных очищена")
        await callback.message.edit_text("✅ База данных успешно очищена. Все пользовательские данные удалены.")
        await callback.message.answer("Возврат в админ-панель", reply_markup=admin_menu)
        await callback.answer()

    @dp.callback_query(F.data == "clear_db_cancel")
    async def clear_db_cancel(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        await callback.message.edit_text("❌ Очистка отменена.")
        await callback.message.answer("Возврат в админ-панель", reply_markup=admin_menu)
        await callback.answer()