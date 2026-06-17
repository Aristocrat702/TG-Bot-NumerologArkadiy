import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType
from keyboards import main_menu, menu_button
from database import get_connection, get_user, create_user, update_user
from yandex_gpt import get_yandex_gpt_response
from utils import (
    is_blacklisted, calculate_destiny_number, grant_achievement,
    save_cached_response, get_cached_response, update_last_active,
    get_bot_config, get_birth_number, get_zodiac_sign
)
from settings import BOT_VERSION

router = Router()

class UserStates(StatesGroup):
    waiting_full_name = State()
    waiting_birth_date_from_poll = State()
    waiting_city = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    update_last_active(user_id)
    if is_blacklisted(user_id):
        await message.answer("Вы заблокированы.")
        return

    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Бот активирован. Используйте /startarkadiy для включения и /stoparkadiy для отключения.")
        await state.clear()
        return

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = int(args[1][4:])
        if referrer_id != user_id:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
            conn.commit()
            conn.close()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, birth_date, bot_version FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row and row[0] and row[1]:
        user_version = row[2] if row[2] else "0.0.0"
        if user_version != bot_version:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET bot_version = ? WHERE user_id = ?", (bot_version, user_id))
            conn.commit()
            conn.close()
            await message.answer(
                f"🔔 Дорогие друзья, у нас вышло обновление версии {bot_version}!\n\n"
                "Теперь доступно:\n"
                "• Психологический тест (кнопки, сохранение результатов)\n"
                "• Дневник настроения с анализом\n"
                "• Помощь психолога (обсуждение ситуаций)\n"
                "• Уровни и опыт\n"
                "• Совместимость с брендами, цветами, знаками зодиака\n"
                "• И многое другое!\n\n"
                "Нажмите /menu, чтобы продолжить.",
                reply_markup=main_menu
            )
        else:
            await message.answer(
                f"🔮 С возвращением, {row[0]}! Аркадий Викторович ждёт ваших вопросов.",
                reply_markup=main_menu
            )
        await state.clear()
        return

    first_name = message.from_user.first_name
    await message.answer(
        f"✨ {first_name}, я — Аркадий Викторович, практикующий нумеролог и психолог с 20-летним стажем.\n\n"
        "Давайте познакомимся. Как вас зовут? (Напишите имя)",
        reply_markup=None
    )
    await state.set_state(UserStates.waiting_full_name)

@router.message(UserStates.waiting_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, напишите настоящее имя (не менее 2 символов).")
        return
    await state.update_data(name=name)
    await message.answer(
        f"Отлично, {name}! Теперь укажите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1985).\n\n"
        "Это нужно для расчёта числа судьбы.",
        parse_mode=None
    )
    await state.set_state(UserStates.waiting_birth_date_from_poll)

@router.message(UserStates.waiting_birth_date_from_poll)
async def process_birth_date_from_poll(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    try:
        day, month, year = map(int, text.split('.'))
        birth_date = f"{day:02d}.{month:02d}.{year:04d}"
        today = datetime.date.today()
        birth = datetime.date(year, month, day)
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        if age < 18:
            await message.answer("Работаю только с совершеннолетними. Попробуйте другую дату.")
            return
        destiny = calculate_destiny_number(birth_date)
        data = await state.get_data()
        name = data.get("name", "друг")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, name, birth_date, destiny_number, reg_date, last_active, bot_version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            name=excluded.name, birth_date=excluded.birth_date,
            destiny_number=excluded.destiny_number, last_active=excluded.last_active,
            bot_version=excluded.bot_version
        """, (user_id, name, birth_date, destiny, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat(), BOT_VERSION))
        conn.commit()
        conn.close()
        await message.answer(
            f"🔢 Ваше число судьбы: {destiny}\n\n"
            f"Спасибо, {name}! Теперь вы можете использовать главное меню.",
            reply_markup=main_menu,
            parse_mode=None
        )
        grant_achievement(user_id, "first_calculation")
        await state.clear()
    except Exception:
        await message.answer("Неверный формат. Введите дату в формате ДД.ММ.ГГГГ")