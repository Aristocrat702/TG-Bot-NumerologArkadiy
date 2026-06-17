from aiogram import types, F
from database import get_connection
from keyboards import admin_menu
from utils import is_admin

def register_logs_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "📋 ЛОГИ")
    async def show_logs(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT admin_id, action, details, created_at FROM admin_logs ORDER BY created_at DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            text = "Логи пусты."
        else:
            text = "📋 *Последние действия:*\n"
            for row in rows:
                admin_id, action, details, created_at = row
                date_str = created_at[:16] if created_at else "—"
                text += f"\n🕒 {date_str}\n"
                text += f"👤 Администратор: {admin_id}\n"
                text += f"📌 Действие: {action}\n"
                text += f"📝 Детали: {details}\n"
                text += "─" * 20 + "\n"
        await message.answer(text, parse_mode="Markdown")