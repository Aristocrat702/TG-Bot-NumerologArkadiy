from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_zodiac_sign
import datetime
import re

# Словарь для ограничения запросов в группах (user_id, chat_id) -> дата последнего запроса
group_requests = {}

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
            return  # бот не активирован в чате

        # Проверяем лимит запросов (1 раз в день на пользователя)
        key = (user_id, chat_id)
        today = datetime.date.today()
        if key in group_requests and group_requests[key] == today:
            return  # уже отвечали сегодня

        # Определяем, о чём спрашивают
        if re.search(r'\b(гороскоп|horoscope)\b', text):
            # Общий гороскоп на сегодня
            today = datetime.date.today()
            prompt = f"Составь краткий астрологический прогноз на сегодня ({today.strftime('%d.%m.%Y')}) для всех знаков зодиака. Дай 1-2 предложения для каждого знака."
            response = await get_yandex_gpt_response(prompt, 0)
            if "Ошибка" in response or len(response) < 20:
                response = "Сегодня благоприятный день для начинаний. Обратите внимание на свои цели."
            await message.reply(f"🌟 *Общий гороскоп на сегодня:*\n\n{response}\n\n📌 Для персонального прогноза напишите мне в личку @NumerologArkadiy_bot", parse_mode="Markdown")
            group_requests[key] = today
            return

        if re.search(r'\b(матрица|матрицу|matrix)\b', text):
            await message.reply("🔮 *Матрица судьбы* – это уникальный расчёт по вашей дате рождения. Чтобы получить её, напишите мне в личку @NumerologArkadiy_bot и нажмите «МОЯ МАТРИЦА».", parse_mode="Markdown")
            group_requests[key] = today
            return

        if re.search(r'\b(число|числа|судьба|судьбы|mynumber)\b', text):
            await message.reply("🔢 *Число судьбы* – ключ к пониманию вашего характера. Узнайте его, написав мне в личку @NumerologArkadiy_bot и нажав «МОЁ ЧИСЛО».", parse_mode="Markdown")
            group_requests[key] = today
            return

        # Если упоминают имя бота или «Аркадий» – можно дать общую подсказку
        if re.search(r'(аркадий|arkadiy|бот)', text):
            await message.reply("👋 Я — Аркадий Викторович. Я помогаю с нумерологией, психологией и астрологией. Напишите мне в личку @NumerologArkadiy_bot, и я расскажу о вас всё по числам и звёздам!", parse_mode="Markdown")
            group_requests[key] = today
            return

        # Если запрос не распознан – ничего не делаем

    # ---------- КОМАНДЫ ДЛЯ ГРУПП (оставляем для явного вызова) ----------
    @dp.message(Command("horoscope"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def group_horoscope_command(message: types.Message):
        # Дублируем логику, чтобы команда тоже работала
        today = datetime.date.today()
        prompt = f"Составь краткий астрологический прогноз на сегодня ({today.strftime('%d.%m.%Y')}) для всех знаков зодиака. Дай 1-2 предложения для каждого знака."
        response = await get_yandex_gpt_response(prompt, 0)
        if "Ошибка" in response or len(response) < 20:
            response = "Сегодня благоприятный день для начинаний. Обратите внимание на свои цели."
        await message.answer(f"🌟 *Общий гороскоп на сегодня:*\n\n{response}\n\n📌 Для персонального прогноза напишите мне в личку @NumerologArkadiy_bot", parse_mode="Markdown")

    @dp.message(Command("matrix"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def group_matrix_command(message: types.Message):
        await message.answer("🔮 *Матрица судьбы* – это уникальный расчёт по вашей дате рождения. Чтобы получить её, напишите мне в личку @NumerologArkadiy_bot и нажмите «МОЯ МАТРИЦА».", parse_mode="Markdown")

    @dp.message(Command("mynumber"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
    async def group_mynumber_command(message: types.Message):
        await message.answer("🔢 *Число судьбы* – ключ к пониманию вашего характера. Узнайте его, написав мне в личку @NumerologArkadiy_bot и нажав «МОЁ ЧИСЛО».", parse_mode="Markdown")