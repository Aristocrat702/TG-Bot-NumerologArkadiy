from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import get_connection, save_group_message, get_group_collection_status
import datetime
import logging

router = Router()

@router.message(Command("startarkadiy"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def start_bot_in_group(message: types.Message):
    chat_id = message.chat.id
    logging.info(f"Команда /startarkadiy в группе {chat_id} от {message.from_user.id}")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM group_chats WHERE chat_id=?", (chat_id,))
    if cursor.fetchone():
        await message.answer("✅ Бот уже активирован")
    else:
        cursor.execute("INSERT INTO group_chats (chat_id, is_active, created_at, frequency, collect_messages) VALUES (?, 1, ?, 2, 0)", 
                       (chat_id, datetime.datetime.now().isoformat()))
        conn.commit()
        await message.answer("✅ Бот активирован")
    conn.close()

@router.message(Command("stoparkadiy"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def stop_bot_in_group(message: types.Message):
    chat_id = message.chat.id
    logging.info(f"Команда /stoparkadiy в группе {chat_id} от {message.from_user.id}")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE group_chats SET is_active = 0 WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
    await message.answer("❌ Бот отключён")

# ===== ОБРАБОТКА ВСЕХ СООБЩЕНИЙ В ГРУППАХ (СОХРАНЕНИЕ, ЕСЛИ ВКЛЮЧЕНО) =====
@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_message(message: types.Message):
    """Сохраняет сообщение в БД, если для группы включён сбор."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text or message.caption or ""
    is_from_bot = message.from_user.is_bot

    if get_group_collection_status(chat_id):
        save_group_message(chat_id, user_id, text, is_from_bot)
    # Ничего не отвечаем