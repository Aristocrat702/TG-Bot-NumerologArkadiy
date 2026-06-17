from aiogram import types, F
from database import get_connection
from keyboards import admin_menu

def register_stats_handlers(dp, bot, admin_ids):
    from utils import is_admin

    @dp.message(F.text == "📊 СТАТИСТИКА")
    async def admin_stats(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_active=1")
        active = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM group_chats WHERE is_active=1")
        active_groups = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM group_chats")
        total_groups = cursor.fetchone()[0]
        conn.close()
        await message.answer(f"📊 *Статистика*\n\n👥 Пользователей: {total}\n💎 Активных подписок: {active}\n👥 Групп (всего): {total_groups}\n✅ Активных групп: {active_groups}", parse_mode="Markdown")

    @dp.message(F.text == "👥 СПИСОК ЮЗЕРОВ")
    async def list_users(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, subscription_active FROM users LIMIT 20")
        rows = cursor.fetchall()
        text = "Последние 20:\n"
        for r in rows:
            text += f"ID: {r[0]}, Имя: {r[1]}, Подписка: {'да' if r[2] else 'нет'}\n"
        await message.answer(text)
        conn.close()