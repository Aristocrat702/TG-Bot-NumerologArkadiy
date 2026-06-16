from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import get_connection
import datetime
import logging

# Таблицы для групп и логов
def init_group_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_chats (
            chat_id INTEGER PRIMARY KEY,
            is_active BOOLEAN DEFAULT 0,
            created_at TEXT,
            frequency INTEGER DEFAULT 2
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            sent_at TEXT,
            message_hash TEXT,
            content_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_group_db()

def register_groups_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):
    # Удаляем все обработчики команд в группах – бот не реагирует на команды
    # Оставляем только активацию и деактивацию через уникальные команды (скрытые)
    @dp.message(Command("startarkadiy"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def start_bot_in_group(message: types.Message):
        chat_id = message.chat.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM group_chats WHERE chat_id=?", (chat_id,))
        if cursor.fetchone():
            await message.answer("Бот уже активирован в этом чате.")
        else:
            cursor.execute("INSERT INTO group_chats (chat_id, is_active, created_at, frequency) VALUES (?, 1, ?, 2)", (chat_id, datetime.datetime.now().isoformat()))
            conn.commit()
            await message.answer("✅ Бот активирован! Я буду присылать полезные мысли в этот чат.")
        conn.close()

    @dp.message(Command("stoparkadiy"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def stop_bot_in_group(message: types.Message):
        chat_id = message.chat.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE group_chats SET is_active = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        await message.answer("Бот отключён в этом чате. Чтобы активировать снова, используйте /startarkadiy.")

    # Все остальные сообщения в группах игнорируются – бот не отвечает на текстовые запросы
    # Это пустой обработчик, который ничего не делает
    @dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def ignore_group_messages(message: types.Message):
        pass