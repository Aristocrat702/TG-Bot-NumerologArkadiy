from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import get_connection
import datetime
import logging

router = Router()

@router.message(Command("startarkadiy"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def start_bot_in_group(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status not in ("administrator", "creator"):
            await message.answer("❌ Только администратор группы может активировать бота.")
            return
    except Exception as e:
        logging.error(f"Ошибка проверки прав: {e}")
        await message.answer("❌ Не удалось проверить ваши права.")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM group_chats WHERE chat_id=?", (chat_id,))
    if cursor.fetchone():
        await message.answer("Бот уже активирован в этом чате.")
    else:
        cursor.execute("INSERT INTO group_chats (chat_id, is_active, created_at, frequency) VALUES (?, 1, ?, 2)", 
                       (chat_id, datetime.datetime.now().isoformat()))
        conn.commit()
        await message.answer("✅ Бот активирован! Я буду присылать полезные мысли в этот чат.")
    conn.close()

@router.message(Command("stoparkadiy"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def stop_bot_in_group(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Проверяем права администратора
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status not in ("administrator", "creator"):
            await message.answer("❌ Только администратор группы может отключить бота.")
            return
    except Exception as e:
        logging.error(f"Ошибка проверки прав: {e}")
        await message.answer("❌ Не удалось проверить ваши права.")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE group_chats SET is_active = 0 WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
    await message.answer("Бот отключён в этом чате. Чтобы активировать снова, используйте /startarkadiy.")

# Игнорируем все остальные сообщения в группах
@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def ignore_group_messages(message: types.Message):
    pass