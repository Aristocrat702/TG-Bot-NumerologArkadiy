from aiogram import types, F
from aiogram.filters import Command
from utils import is_admin, add_to_blacklist, remove_from_blacklist

def register_blacklist_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "🚫 БЛЭК-ЛИСТ")
    async def blacklist_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, reason FROM blacklist")
        rows = cursor.fetchall()
        conn.close()
        text = "Чёрный список:\n"
        if not rows:
            text += "пуст"
        else:
            for r in rows:
                text += f"ID: {r[0]}, причина: {r[1]}\n"
        await message.answer(text + "\n\n➕ Добавить: /add_blacklist USER_ID [причина]\n🗑 Удалить: /remove_blacklist USER_ID")

    @dp.message(Command("add_blacklist"))
    async def add_blacklist(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.answer("Использование: /add_blacklist USER_ID [причина]")
            return
        user_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else ""
        add_to_blacklist(user_id, reason)
        await message.answer(f"Пользователь {user_id} добавлен в чёрный список.")
        try:
            await bot.send_message(user_id, "🚫 Вы были заблокированы администратором. Если считаете это ошибкой, свяжитесь с @Aristocrat102")
        except:
            pass

    @dp.message(Command("remove_blacklist"))
    async def remove_blacklist(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /remove_blacklist USER_ID")
            return
        user_id = int(parts[1])
        remove_from_blacklist(user_id)
        await message.answer(f"Пользователь {user_id} удалён из чёрного списка.")