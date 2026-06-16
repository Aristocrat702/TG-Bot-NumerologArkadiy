from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import get_connection
import datetime
import logging

def init_group_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_chats (
            chat_id INTEGER PRIMARY KEY,
            type TEXT DEFAULT 'thoughts',
            frequency INTEGER DEFAULT 2,
            is_active BOOLEAN DEFAULT 0,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            sent_at TEXT,
            content_type TEXT,
            message_hash TEXT,
            message_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_group_db()

def register_groups_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("startarkadiy"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def start_bot_in_group(message: types.Message):
        chat_id = message.chat.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM group_chats WHERE chat_id=?", (chat_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE group_chats SET is_active = 1 WHERE chat_id = ?", (chat_id,))
            conn.commit()
            await message.answer("✅ Бот активирован в этом чате. Я буду присылать полезные мысли и поддержку.")
        else:
            cursor.execute("INSERT INTO group_chats (chat_id, type, is_active, created_at) VALUES (?, 'thoughts', 1, ?)", (chat_id, datetime.datetime.now().isoformat()))
            conn.commit()
            await message.answer("✅ Бот активирован! Я буду присылать полезные мысли и поддержку.\n\n"
                                 "Чтобы отключить бота, напишите /stoparkadiy.")
        conn.close()

    @dp.message(Command("stoparkadiy"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def stop_bot_in_group(message: types.Message):
        chat_id = message.chat.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE group_chats SET is_active = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        await message.answer("❌ Бот отключён в этом чате. Чтобы активировать снова, используйте /startarkadiy.")

    # В группах бот НЕ реагирует на другие команды и текстовые сообщения
    # (они игнорируются, чтобы не захламлять чат)