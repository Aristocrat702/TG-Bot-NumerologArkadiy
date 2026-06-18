import datetime
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
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
    "💬 КОНСУЛЬТАЦИЯ", "🧠 ПСИХОЛОГИЯ", "🌟 АСТРОЛОГИЯ",
    "💎 ЭКСКЛЮЗИВ", "🧠 СЕКСОЛОГИЯ", "🌙 ТОЛКОВАНИЕ СНОВ", "👤 МОЙ ПРОФИЛЬ"
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
        await message.answer("Используйте /startarkadiy для активации бота в группе.")
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
                    await message.answer(
                        f"📖 <b>{title}</b>\n\n{content}",
                        parse_mode="HTML",
                        reply_markup=main_menu
                    )
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

    # Если пользователь уже зарегистрирован
    if row and row[0] and row[1]:
        user_version = row[2] if row[2] else "0.0.0"
        if user_version != BOT_VERSION:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET bot_version = ? WHERE user_id = ?", (BOT_VERSION, user_id))
            conn.commit()
            conn.close()
            await message.answer(
                f"🔔 <b>Обновление до версии {BOT_VERSION}!</b>\n\n"
                "• Улучшенные платные функции с практическими инструкциями\n"
                "• Новый раздел «Толкование снов»\n"
                "• Обновлённые промпты с HTML-форматированием\n"
                "• Мотивационные уведомления без рекламы\n\n"
                "Нажмите кнопку ниже, чтобы продолжить.",
                parse_mode="HTML",
                reply_markup=main_menu
            )
        else:
            name = row[0]
            gender = row[3] if row[3] else "unknown"
            if gender == "male":
                greeting = f"🔮 <b>С возвращением, уважаемый {name}!</b>"
            elif gender == "female":
                greeting = f"🔮 <b>С возвращением, дорогая {name}!</b>"
            else:
                greeting = f"🔮 <b>С возвращением, {name}!</b>"
            await message.answer(greeting, parse_mode="HTML", reply_markup=main_menu)
        await state.clear()
        return

    # ===== НОВОЕ ПРИВЕТСТВИЕ ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ =====
    first_name = message.from_user.first_name
    welcome_text = (
        "🌟 <b>Добро пожаловать в «Аркадий Викторович»!</b>\n\n"
        "👋 Я — Аркадий, твой личный цифровой наставник.\n"
        "Не просто бот, а место, где числа, звёзды и психология встречаются, чтобы помочь тебе разобраться в себе.\n\n"
        "🔮 <b>Что ты здесь найдёшь?</b>\n\n"
        "🧠 <b>Бесплатно:</b>\n"
        "• Своё число судьбы и его силу\n"
        "• Карту дня с прогнозом и советом\n"
        "• Совместимость с партнёром\n"
        "• Гороскоп на сегодня\n"
        "• Психотесты, дневник настроения, самодиагностику\n"
        "• Консультацию (5 вопросов в день)\n"
        "• Интересные статьи по психологии и сексологии\n\n"
        "💎 <b>По подписке (всего 249 ₽/мес):</b>\n"
        "• Полная матрица судьбы — 22 аркана, твой жизненный код\n"
        "• Денежный код — стратегия увеличения дохода\n"
        "• Полная натальная карта — все планеты и дома\n"
        "• Соляр — прогноз на год\n"
        "• Гороскоп на месяц с деталями\n"
        "• Безлимитные консультации\n"
        "• Психологические практики и аудио-медитации (скоро)\n\n"
        "🔥 Здесь ты не просто получаешь ответы — ты начинаешь понимать себя.\n\n"
        "Готов узнать своё число судьбы?"
    )

    # Кнопка "Начать"
    start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Узнать своё число", callback_data="start_onboarding")]
    ])

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=start_keyboard,
        disable_web_page_preview=True
    )
    # Устанавливаем состояние ожидания имени (будет вызвано после нажатия кнопки)
    await state.set_state(UserStates.waiting_full_name)

@router.callback_query(F.data == "start_onboarding")
async def start_onboarding(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Отлично! Давай познакомимся. Как тебя зовут?",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(UserStates.waiting_full_name)
    await callback.answer()

@router.message(UserStates.waiting_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя должно быть не менее 2 символов.", reply_markup=ReplyKeyboardRemove())
        return

    if name in MAIN_MENU_BUTTONS:
        await message.answer(
            "Пожалуйста, введите ваше настоящее имя, а не кнопку меню.",
            reply_markup=ReplyKeyboardRemove()
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
        f"Отлично, {name}! {address.capitalize()}, теперь укажите вашу дату рождения в формате <b>ДД.ММ.ГГГГ</b> (например, 15.06.1985).\n\n"
        "Это нужно для расчёта вашего числа судьбы.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(UserStates.waiting_birth_date_from_poll)

@router.message(UserStates.waiting_birth_date_from_poll)
async def process_birth_date_from_poll(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if text in MAIN_MENU_BUTTONS:
        await message.answer(
            "Пожалуйста, введите дату рождения в формате ДД.ММ.ГГГГ.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    try:
        day, month, year = map(int, text.split('.'))
        birth_date = f"{day:02d}.{month:02d}.{year:04d}"
        today = datetime.date.today()
        birth = datetime.date(year, month, day)
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        if age < 18:
            await message.answer("Работаю только с совершеннолетними.", reply_markup=ReplyKeyboardRemove())
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
        
        # Поздравление с регистрацией
        await message.answer(
            f"🔢 <b>Ваше число судьбы: {destiny}</b>\n\n"
            f"Спасибо, {name}! Теперь вы можете использовать главное меню, {address}.\n\n"
            "Нажмите кнопку ниже, чтобы начать.",
            parse_mode="HTML",
            reply_markup=main_menu
        )
        grant_achievement(user_id, "first_calculation")
        await state.clear()
    except Exception:
        await message.answer(
            "Неверный формат. Введите дату в формате ДД.ММ.ГГГГ.",
            reply_markup=ReplyKeyboardRemove()
        )