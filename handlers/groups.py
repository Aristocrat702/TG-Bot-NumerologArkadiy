from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_zodiac_sign
import datetime
import re
import asyncio
import logging

# ---------- РАБОТА С БАЗОЙ ДАННЫХ ДЛЯ ГРУПП ----------
def init_group_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_chats (
            chat_id INTEGER PRIMARY KEY,
            type TEXT DEFAULT 'daily_motivation',
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_user_requests (
            user_id INTEGER,
            chat_id INTEGER,
            request_date TEXT,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id, request_date)
        )
    ''')
    conn.commit()
    conn.close()

# Инициализация при загрузке
init_group_db()

async def can_make_request(user_id: int, chat_id: int) -> bool:
    """Проверяет, может ли пользователь сделать запрос в группе (лимит 5 в день)."""
    today = datetime.date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count FROM group_user_requests WHERE user_id=? AND chat_id=? AND request_date=?", (user_id, chat_id, today))
    row = cursor.fetchone()
    if not row:
        # Создаём запись с нулевым счётчиком
        cursor.execute("INSERT INTO group_user_requests (user_id, chat_id, request_date, count) VALUES (?, ?, ?, 0)", (user_id, chat_id, today))
        conn.commit()
        conn.close()
        return True
    count = row[0]
    conn.close()
    return count < 5

async def increment_request(user_id: int, chat_id: int) -> int:
    """Увеличивает счётчик запросов и возвращает новое значение."""
    today = datetime.date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE group_user_requests SET count = count + 1 WHERE user_id=? AND chat_id=? AND request_date=?", (user_id, chat_id, today))
    if cursor.rowcount == 0:
        cursor.execute("INSERT INTO group_user_requests (user_id, chat_id, request_date, count) VALUES (?, ?, ?, 1)", (user_id, chat_id, today))
    conn.commit()
    cursor.execute("SELECT count FROM group_user_requests WHERE user_id=? AND chat_id=? AND request_date=?", (user_id, chat_id, today))
    new_count = cursor.fetchone()[0]
    conn.close()
    return new_count

def register_groups_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("start_bot"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def start_bot_in_group(message: types.Message):
        chat_id = message.chat.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM group_chats WHERE chat_id=?", (chat_id,))
        if cursor.fetchone():
            await message.answer("Бот уже активирован в этом чате. Для настройки используйте /set_chat_type.")
        else:
            cursor.execute("INSERT INTO group_chats (chat_id, type, is_active) VALUES (?, 'daily_motivation', 1)", (chat_id,))
            conn.commit()
            await message.answer("✅ Бот активирован! Выберите тип контента командой /set_chat_type:\n"
                                 "• /set_chat_type daily_motivation – мотивация\n"
                                 "• /set_chat_type horoscope – гороскоп на день\n"
                                 "• /set_chat_type advice – психологический совет")
        conn.close()

    @dp.message(Command("set_chat_type"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def set_chat_type(message: types.Message):
        chat_id = message.chat.id
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Укажите тип контента: daily_motivation, horoscope или advice")
            return
        type_str = args[1].strip()
        if type_str not in ["daily_motivation", "horoscope", "advice"]:
            await message.answer("Недопустимый тип. Доступные: daily_motivation, horoscope, advice")
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

    # ---------- ОБРАБОТКА ТЕКСТОВЫХ ЗАПРОСОВ В ГРУППАХ (без команды) ----------
    @dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.text)
    async def group_text_handler(message: types.Message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        text = message.text.lower()
        # Проверяем, активен ли бот в этом чате
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM group_chats WHERE chat_id=?", (chat_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            return  # бот не активирован

        # Проверяем лимит
        if not await can_make_request(user_id, chat_id):
            await message.reply("📌 Сегодня вы исчерпали лимит запросов в этой группе. Напишите мне в личку @NumerologArkadiy_bot для неограниченных консультаций.", parse_mode="Markdown")
            return

        # Определяем тему запроса
        response = None
        if re.search(r'\b(гороскоп|horoscope)\b', text):
            today = datetime.date.today()
            prompt = f"Составь краткий астрологический прогноз на сегодня ({today.strftime('%d.%m.%Y')}) для всех знаков зодиака. Дай 1-2 предложения для каждого знака."
            resp = await get_yandex_gpt_response(prompt, 0)
            if "Ошибка" in resp or len(resp) < 20:
                resp = "Сегодня благоприятный день для начинаний. Обратите внимание на свои цели."
            response = f"🌟 *Общий гороскоп на сегодня:*\n\n{resp}"
        elif re.search(r'\b(матрица|матрицу|matrix)\b', text):
            response = "🔮 *Матрица судьбы* – это уникальный расчёт по вашей дате рождения. Чтобы получить её, напишите мне в личку @NumerologArkadiy_bot и нажмите «МОЯ МАТРИЦА»."
        elif re.search(r'\b(число|числа|судьба|судьбы|mynumber)\b', text):
            response = "🔢 *Число судьбы* – ключ к пониманию вашего характера. Узнайте его, написав мне в личку @NumerologArkadiy_bot и нажав «МОЁ ЧИСЛО»."
        elif re.search(r'(аркадий|arkadiy|бот)', text):
            response = "👋 Я — Аркадий Викторович. Я помогаю с нумерологией, психологией и астрологией. Напишите мне в личку @NumerologArkadiy_bot, и я расскажу о вас всё по числам и звёздам!"

        if response:
            # Добавляем призыв в конце
            call_to_action = "\n\n📌 *Хотите узнать больше о себе?* Переходите в личный бот @NumerologArkadiy_bot – там я дам полную матрицу, гороскоп на месяц и отвечу на любые вопросы."
            await message.reply(response + call_to_action, parse_mode="Markdown")
            # Увеличиваем счётчик
            count = await increment_request(user_id, chat_id)
            # Если осталось мало запросов, напоминаем
            remaining = 5 - count
            if remaining <= 2:
                await message.reply(f"💡 У вас осталось {remaining} запроса на сегодня в этой группе. Используйте их с умом, а для полного доступа переходите в личный бот.", parse_mode="Markdown")

    # ---------- КОМАНДЫ ДЛЯ ГРУПП (с тем же лимитом и призывом) ----------
    @dp.message(Command("horoscope"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def group_horoscope_command(message: types.Message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not await can_make_request(user_id, chat_id):
            await message.reply("📌 Сегодня вы исчерпали лимит запросов в этой группе. Напишите мне в личку @NumerologArkadiy_bot.", parse_mode="Markdown")
            return
        today = datetime.date.today()
        prompt = f"Составь краткий астрологический прогноз на сегодня ({today.strftime('%d.%m.%Y')}) для всех знаков зодиака. Дай 1-2 предложения для каждого знака."
        resp = await get_yandex_gpt_response(prompt, 0)
        if "Ошибка" in resp or len(resp) < 20:
            resp = "Сегодня благоприятный день для начинаний. Обратите внимание на свои цели."
        response = f"🌟 *Общий гороскоп на сегодня:*\n\n{resp}"
        call_to_action = "\n\n📌 *Хотите узнать больше о себе?* Переходите в личный бот @NumerologArkadiy_bot – там я дам полную матрицу, гороскоп на месяц и отвечу на любые вопросы."
        await message.answer(response + call_to_action, parse_mode="Markdown")
        count = await increment_request(user_id, chat_id)
        remaining = 5 - count
        if remaining <= 2:
            await message.reply(f"💡 У вас осталось {remaining} запроса на сегодня в этой группе. Используйте их с умом.", parse_mode="Markdown")

    @dp.message(Command("matrix"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def group_matrix_command(message: types.Message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not await can_make_request(user_id, chat_id):
            await message.reply("📌 Сегодня вы исчерпали лимит запросов в этой группе. Напишите мне в личку @NumerologArkadiy_bot.", parse_mode="Markdown")
            return
        response = "🔮 *Матрица судьбы* – это уникальный расчёт по вашей дате рождения. Чтобы получить её, напишите мне в личку @NumerologArkadiy_bot и нажмите «МОЯ МАТРИЦА»."
        call_to_action = "\n\n📌 *Узнайте свою полную матрицу в личном боте!* @NumerologArkadiy_bot"
        await message.answer(response + call_to_action, parse_mode="Markdown")
        await increment_request(user_id, chat_id)

    @dp.message(Command("mynumber"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def group_mynumber_command(message: types.Message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not await can_make_request(user_id, chat_id):
            await message.reply("📌 Сегодня вы исчерпали лимит запросов в этой группе. Напишите мне в личку @NumerologArkadiy_bot.", parse_mode="Markdown")
            return
        response = "🔢 *Число судьбы* – ключ к пониманию вашего характера. Узнайте его, написав мне в личку @NumerologArkadiy_bot и нажав «МОЁ ЧИСЛО»."
        call_to_action = "\n\n📌 *Рассчитайте своё число судьбы в личном боте!* @NumerologArkadiy_bot"
        await message.answer(response + call_to_action, parse_mode="Markdown")
        await increment_request(user_id, chat_id)