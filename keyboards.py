from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand
)
from aiogram import Bot

# ---------- Главное меню (Reply) ----------
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔮 МОЯ МАТРИЦА"), KeyboardButton(text="🔢 МОЁ ЧИСЛО")],
        [KeyboardButton(text="❤️ СОВМЕСТИМОСТЬ"), KeyboardButton(text="🎁 КАРТА ДНЯ")],
        [KeyboardButton(text="💬 ЗАДАТЬ ВОПРОС"), KeyboardButton(text="🧠 ПСИХОЛОГИЯ")],
        [KeyboardButton(text="🌟 АСТРОЛОГИЯ"), KeyboardButton(text="👤 МОЙ ПРОФИЛЬ")],
    ],
    resize_keyboard=True
)

# ---------- Подменю психологии ----------
psycho_submenu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧠 ПСИХОТЕСТ"), KeyboardButton(text="📓 ДНЕВНИК НАСТРОЕНИЯ")],
        [KeyboardButton(text="👔 СТИЛЬ И УДАЧА"), KeyboardButton(text="📊 МОИ РЕЗУЛЬТАТЫ ТЕСТА")],
        [KeyboardButton(text="⬅️ НАЗАД")],
    ],
    resize_keyboard=True
)

# ---------- Подменю астрологии ----------
astro_submenu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌌 НАТАЛЬНАЯ КАРТА"), KeyboardButton(text="🔄 ТРАНЗИТЫ")],
        [KeyboardButton(text="☀️ СОЛЯР"), KeyboardButton(text="♓ СОВМЕСТИМОСТЬ ПО ЗНАКАМ")],
        [KeyboardButton(text="📅 ГОРОСКОП НА ДЕНЬ"), KeyboardButton(text="📆 ГОРОСКОП НА МЕСЯЦ")],
        [KeyboardButton(text="⬅️ НАЗАД")],
    ],
    resize_keyboard=True
)

# ---------- Профиль (Reply) ----------
profile_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✏️ СМЕНИТЬ ИМЯ")],
        [KeyboardButton(text="🎁 БЕСПЛАТНЫЕ ДНИ"), KeyboardButton(text="🏆 ДОСТИЖЕНИЯ")],
        [KeyboardButton(text="⭐ КУПИТЬ ПОДПИСКУ"), KeyboardButton(text="🎁 ПОДАРИТЬ ПОДПИСКУ")],
        [KeyboardButton(text="⚙️ НАСТРОЙКИ"), KeyboardButton(text="📜 ИСТОРИЯ ЗАПРОСОВ")],
        [KeyboardButton(text="🎟️ ВВЕСТИ ПРОМОКОД"), KeyboardButton(text="👥 ПРИГЛАСИТЬ В ГРУППУ")],
        [KeyboardButton(text="❓ ПОМОЩЬ"), KeyboardButton(text="✖️ ЗАКРЫТЬ")],
    ],
    resize_keyboard=True
)

# ---------- Быстрые темы для числа ----------
quick_topics_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💰 Деньги", callback_data="topic_money")],
        [InlineKeyboardButton(text="❤️ Любовь", callback_data="topic_love")],
        [InlineKeyboardButton(text="💼 Карьера", callback_data="topic_career")],
        [InlineKeyboardButton(text="🧘 Здоровье", callback_data="topic_health")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ]
)

# ---------- Кнопка "Назад в меню" (инлайн) ----------
menu_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Главное меню", callback_data="back_to_menu")]
    ]
)

# ---------- Админ-меню (Reply) ----------
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 СТАТИСТИКА"), KeyboardButton(text="👥 СПИСОК ЮЗЕРОВ")],
        [KeyboardButton(text="✉️ РАССЫЛКА"), KeyboardButton(text="💰 ВЫДАТЬ ПОДПИСКУ")],
        [KeyboardButton(text="🎫 ПРОМОКОДЫ"), KeyboardButton(text="🔧 ПРОМПТ")],
        [KeyboardButton(text="📤 ЭКСПОРТ БАЗЫ"), KeyboardButton(text="🚫 БЛЭК-ЛИСТ")],
        [KeyboardButton(text="💬 ОТВЕТИТЬ"), KeyboardButton(text="💰 ЦЕНА ПОДПИСКИ")],
        [KeyboardButton(text="🏆 ЛИДЕРБОРД"), KeyboardButton(text="📋 ЛОГИ")],
        [KeyboardButton(text="👤 ИНФО ПОЛЬЗОВАТЕЛЯ"), KeyboardButton(text="⬅️ ВЫЙТИ ИЗ АДМИНКИ")],
    ],
    resize_keyboard=True
)

# ---------- Функция установки команд ----------
async def set_main_menu(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="help", description="Помощь"),
    ])