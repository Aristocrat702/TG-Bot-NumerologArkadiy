import datetime
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType
from keyboards import main_menu
from database import get_connection, update_user_gender
from yandex_gpt import get_yandex_gpt_response
from utils import (
    is_blacklisted, calculate_destiny_number, grant_achievement,
    save_cached_response, get_cached_response, update_last_active,
    get_bot_config
)
from utils.misc import log_user_visit_wrapper
from utils.gender import detect_gender_by_name
from settings import BOT_VERSION

router = Router()

MAIN_MENU_BUTTONS = [
    "🔢 МОЁ ЧИСЛО", "🎁 КАРТА ДНЯ", "❤️ СОВМЕСТИМОСТЬ",
    "💬 ЗАДАТЬ ВОПРОС", "🧠 ПСИХОЛОГИЯ", "🌟 АСТРОЛОГИЯ",
    "💎 ЭКСКЛЮЗИВ", "🧠 СЕКСОЛОГИЯ", "👤 МОЙ ПРОФИЛЬ"
]

class UserStates(StatesGroup):
    waiting_full_name = State()
    waiting_birth_date_from_poll = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    update_last_active(user_id)
    if is_blacklisted(user_id):
        await message.answer("Вы заблокированы.")
        return

    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    log_user_visit_wrapper(user_id, source="start")

    args = message.text.split()
    logging.info(f"START args: {args}")

    # ===== DEEP LINK ДЛЯ СТАТЕЙ =====
    if len(args) > 1 and args[1].startswith("article_"):
        parts = args[1].split("_")
        if len(parts) >= 3:
            category = parts[1]
            try:
                article_id = int(parts[2])
            except ValueError:
                article_id = None
            if article_id:
                conn = get_connection()
                cursor = conn.cursor()
                if category == "sexology":
                    cursor.execute("SELECT title, content FROM sexology_articles WHERE id = ? AND status = 'published'", (article_id,))
                elif category == "psychology":
                    cursor.execute("SELECT title, content FROM psychology_articles WHERE id = ? AND status = 'published'", (article_id,))
                else:
                    await message.answer("Неверная категория статьи.", reply_markup=main_menu)
                    return
                row = cursor.fetchone()
                conn.close()
                if row:
                    title, content = row
                    # ИСПРАВЛЕНО: добавлено меню
                    await message.answer(f"📖 *{title}*\n\n{content}", parse_mode="Markdown", reply_markup=main_menu)
                    return
                else:
                    await message.answer("Статья не найдена или ещё не опубликована.", reply_markup=main_menu)
                    return
            else:
                await message.answer("Неверная ссылка на статью.", reply_markup=main_menu)
                return
        else:
            await message.answer("Неверная ссылка на статью.", reply_markup=main_menu)
            return

    # ===== РЕФЕРАЛ =====
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
    cursor.execute("SELECT name, birth_date, bot_version, gender FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row and row[0] and row[1]:
        user_version = row[2] if row[2] else "0.0.0"
        if user_version != BOT_VERSION:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET bot_version = ? WHERE user_id = ?", (BOT_VERSION, user_id))
            conn.commit()
            conn.close()
            await message.answer(
                f"🔔 Обновление до версии {BOT_VERSION}!\n"
                "• Психологический тест\n"
                "• Дневник настроения\n"
                "• Уровни и опыт\n"
                "• Совместимость по знакам\n"
                "Нажмите /menu, чтобы продолжить.",
                reply_markup=main_menu
            )
        else:
            name = row[0]
            gender = row[3] if row[3] else "unknown"
            if gender == "male":
                greeting = f"🔮 С возвращением, уважаемый {name}!"
            elif gender == "female":
                greeting = f"🔮 С возвращением, дорогая {name}!"
            else:
                greeting = f"🔮 С возвращением, {name}!"
            await message.answer(greeting, reply_markup=main_menu)
        await state.clear()
        return

    first_name = message.from_user.first_name
    await message.answer(
        f"✨ Добро пожаловать, {first_name}!\n\n"
        "Я — Аркадий Викторович, ваш личный нумеролог, психолог, астролог и сексолог с 20-летним стажем.\n\n"
        "Здесь вы сможете:\n"
        "🔢 Узнать своё число судьбы и получить персонализированную характеристику\n"
        "🎁 Получить карту дня с прогнозом и практическими советами\n"
        "❤️ Проверить совместимость с партнёром\n"
        "🧠 Пройти психологические тесты и вести дневник настроения\n"
        "🌟 Получить гороскоп на день и эксклюзивные прогнозы по подписке\n"
        "💸 Рассчитать денежный код и стратегию увеличения дохода (по подписке)\n"
        "🧠 Задать вопросы по сексологии и читать полезные статьи\n\n"
        "💎 Подписка (всего 249 ₽/мес) открывает все эксклюзивные функции.\n\n"
        "Для начала давайте познакомимся. Как вас зовут?",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(UserStates.waiting_full_name)

@router.message(UserStates.waiting_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя должно быть не менее 2 символов.", reply_markup=types.ReplyKeyboardRemove())
        return

    if name in MAIN_MENU_BUTTONS:
        await message.answer(
            "Пожалуйста, введите ваше настоящее имя, а не кнопку меню.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    gender = await detect_gender_by_name(name)
    await state.update_data(name=name, gender=gender)
    
    if gender == "male":
        address = "дорогой"
    elif gender == "female":
        address = "дорогая"
    else:
        address = "друг мой"
    
    await message.answer(
        f"Отлично, {name}! {address.capitalize()}, теперь укажите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 15.06.1985).\n\n"
        "Это нужно для расчёта вашего числа судьбы.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(UserStates.waiting_birth_date_from_poll)

@router.message(UserStates.waiting_birth_date_from_poll)
async def process_birth_date_from_poll(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if text in MAIN_MENU_BUTTONS:
        await message.answer(
            "Пожалуйста, введите дату рождения в формате ДД.ММ.ГГГГ.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    try:
        day, month, year = map(int, text.split('.'))
        birth_date = f"{day:02d}.{month:02d}.{year:04d}"
        today = datetime.date.today()
        birth = datetime.date(year, month, day)
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        if age < 18:
            await message.answer("Работаю только с совершеннолетними.", reply_markup=types.ReplyKeyboardRemove())
            return
        destiny = calculate_destiny_number(birth_date)
        data = await state.get_data()
        name = data.get("name", "друг")
        gender = data.get("gender", "unknown")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, name, birth_date, destiny_number, reg_date, last_active, bot_version, gender)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            name=excluded.name, birth_date=excluded.birth_date,
            destiny_number=excluded.destiny_number, last_active=excluded.last_active,
            bot_version=excluded.bot_version, gender=excluded.gender
        """, (user_id, name, birth_date, destiny, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat(), BOT_VERSION, gender))
        conn.commit()
        conn.close()
        
        if gender == "male":
            address = "уважаемый"
        elif gender == "female":
            address = "уважаемая"
        else:
            address = "друг мой"
        
        await message.answer(
            f"🔢 Ваше число судьбы: {destiny}\n\n"
            f"Спасибо, {name}! Теперь вы можете использовать главное меню, {address}.",
            reply_markup=main_menu
        )
        grant_achievement(user_id, "first_calculation")
        await state.clear()
    except Exception:
        await message.answer(
            "Неверный формат. Введите дату в формате ДД.ММ.ГГГГ.",
            reply_markup=types.ReplyKeyboardRemove()
        )