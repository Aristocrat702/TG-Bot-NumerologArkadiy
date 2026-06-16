from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import get_connection
import datetime
import random
import asyncio
import logging

def init_group_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_chats (
            chat_id INTEGER PRIMARY KEY,
            type TEXT DEFAULT 'thoughts',
            frequency INTEGER DEFAULT 3,
            is_active BOOLEAN DEFAULT 0,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            sent_at TEXT,
            content_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_group_db()

# Список мыслей Аркадия (для групп)
THOUGHTS = [
    "Числа не врут, но и вы не обманывайте себя. Слушайте душу.",
    "Ваше число судьбы – это компас. Следуйте ему без страха.",
    "Ошибки – это тоже цифры, которые ведут к правильному ответу.",
    "Не бойтесь начинать с нуля. Ноль – это начало нового цикла.",
    "Каждое утро вы перезагружаете свою личную статистику. Используйте это.",
    "Гармония приходит, когда внутреннее число совпадает с внешним действием.",
    "Счастье – это не случайность, а сумма правильных решений.",
    "Ваш путь уникален, как отпечаток пальца. Не сравнивайте.",
    "Смелость – это когда ваш страх умножают на веру в себя.",
    "Маленькие победы складываются в большую судьбу.",
    "Доверяйте числам, но не забывайте слушать сердце.",
    "Каждый день – новая возможность переписать свою историю.",
    "Ваша энергия притягивает то, о чём вы думаете.",
    "Не бойтесь ошибаться – ошибки ведут к мудрости.",
    "Ваше число сегодня: удача на вашей стороне."
]

def register_groups_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("start_bot"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def start_bot_in_group(message: types.Message):
        chat_id = message.chat.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM group_chats WHERE chat_id=?", (chat_id,))
        if cursor.fetchone():
            await message.answer("Бот уже активирован. Для настройки используйте /set_group_frequency (число) и /set_group_type (thoughts | horoscope | advice).")
        else:
            cursor.execute("INSERT INTO group_chats (chat_id, type, frequency, is_active, created_at) VALUES (?, 'thoughts', 3, 1, ?)", (chat_id, datetime.datetime.now().isoformat()))
            conn.commit()
            await message.answer("✅ Бот активирован! Я буду присылать мысли в этот чат 3 раза в день.\n\n"
                                 "Настройте:\n"
                                 "• /set_group_frequency <число> – количество сообщений в день (1-10)\n"
                                 "• /set_group_type thoughts | horoscope | advice – тип контента\n"
                                 "• /stop_bot – отключить бота в этом чате")
        conn.close()

    @dp.message(Command("set_group_frequency"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def set_frequency(message: types.Message):
        chat_id = message.chat.id
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Укажите число (1-10): /set_group_frequency 3")
            return
        try:
            freq = int(args[1].strip())
            if freq < 1 or freq > 10:
                raise ValueError
        except:
            await message.answer("Введите число от 1 до 10.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE group_chats SET frequency = ? WHERE chat_id = ?", (freq, chat_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Частота обновлена: {freq} сообщений в день.")

    @dp.message(Command("set_group_type"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def set_group_type(message: types.Message):
        chat_id = message.chat.id
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Укажите тип: thoughts, horoscope или advice")
            return
        type_str = args[1].strip()
        if type_str not in ["thoughts", "horoscope", "advice"]:
            await message.answer("Доступные типы: thoughts, horoscope, advice")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE group_chats SET type = ? WHERE chat_id = ?", (type_str, chat_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Тип контента изменён на {type_str}.")

    @dp.message(Command("stop_bot"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def stop_bot_in_group(message: types.Message):
        chat_id = message.chat.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE group_chats SET is_active = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        await message.answer("Бот отключён в этом чате. Чтобы активировать снова, используйте /start_bot.")

    @dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.text)
    async def group_text_handler(message: types.Message):
        # В группах бот не отвечает на текстовые запросы, только на команды.
        # Это предотвращает захламление чата.
        pass