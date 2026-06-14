from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram import Bot

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔮 МОЯ МАТРИЦА"), KeyboardButton(text="🔢 МОЁ ЧИСЛО")],
        [KeyboardButton(text="❤️ СОВМЕСТИМОСТЬ"), KeyboardButton(text="🎁 КАРТА ДНЯ")],
        [KeyboardButton(text="💬 ЗАДАТЬ ВОПРОС"), KeyboardButton(text="🧠 ПСИХОЛОГИЯ")],
        [KeyboardButton(text="🌟 ГОРОСКОП"), KeyboardButton(text="👤 МОЙ ПРОФИЛЬ")]
    ],
    resize_keyboard=True
)

# Подменю психологии
psycho_submenu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🧠 ПСИХОТЕСТ", callback_data="psycho_test")],
    [InlineKeyboardButton(text="😊 ДНЕВНИК НАСТРОЕНИЯ", callback_data="mood_diary")],
    [InlineKeyboardButton(text="🎨 СТИЛЬ И УДАЧА", callback_data="style_test")],
    [InlineKeyboardButton(text="📘 МОИ РЕЗУЛЬТАТЫ ТЕСТА", callback_data="my_psycho_result")],
    [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="psycho_back")]
])

# Меню профиля (без кнопки смены даты)
profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ СМЕНИТЬ ИМЯ", callback_data="change_name")],
    [InlineKeyboardButton(text="🎁 БЕСПЛАТНЫЕ ДНИ", callback_data="referral_info"),
     InlineKeyboardButton(text="🏆 ДОСТИЖЕНИЯ", callback_data="achievements")],
    [InlineKeyboardButton(text="⏰ УМНЫЙ БУДИЛЬНИК", callback_data="alarm_menu")],
    [InlineKeyboardButton(text="⭐ КУПИТЬ ПОДПИСКУ", callback_data="buy_subscription"),
     InlineKeyboardButton(text="🎁 ПОДАРИТЬ ПОДПИСКУ", callback_data="gift_subscription")],
    [InlineKeyboardButton(text="⚙️ НАСТРОЙКИ", callback_data="settings"),
     InlineKeyboardButton(text="❌ ОТМЕНИТЬ ПОДПИСКУ", callback_data="cancel_sub")],
    [InlineKeyboardButton(text="📜 ИСТОРИЯ ЗАПРОСОВ", callback_data="history")],
    [InlineKeyboardButton(text="🎟️ ВВЕСТИ ПРОМОКОД", callback_data="enter_promo")],
    [InlineKeyboardButton(text="✖️ ЗАКРЫТЬ", callback_data="close")]
])

# Меню быстрых тем
quick_topics_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💰 Деньги", callback_data="quick_topic_money"),
     InlineKeyboardButton(text="❤️ Любовь", callback_data="quick_topic_love")],
    [InlineKeyboardButton(text="⚕️ Здоровье", callback_data="quick_topic_health"),
     InlineKeyboardButton(text="💼 Карьера", callback_data="quick_topic_career")],
    [InlineKeyboardButton(text="👨‍👩‍👧 Семья", callback_data="quick_topic_family"),
     InlineKeyboardButton(text="🎨 Творчество", callback_data="quick_topic_creativity")],
    [InlineKeyboardButton(text="🧠 Психология", callback_data="quick_topic_psychology")],
    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
])

# Кнопка «Поделиться»
share_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📤 Поделиться результатом", callback_data="share_result")],
    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
])

menu_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
])

# Меню челленджа
challenge_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔥 Начать челлендж 7 дней", callback_data="start_challenge")],
    [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="challenge_progress")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
])

# Админ-меню
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 СТАТИСТИКА"), KeyboardButton(text="👥 СПИСОК ЮЗЕРОВ")],
        [KeyboardButton(text="✉️ РАССЫЛКА"), KeyboardButton(text="💰 ВЫДАТЬ ПОДПИСКУ")],
        [KeyboardButton(text="🎫 ПРОМОКОДЫ"), KeyboardButton(text="🔧 ПРОМПТ")],
        [KeyboardButton(text="📤 ЭКСПОРТ БАЗЫ"), KeyboardButton(text="🚫 БЛЭК-ЛИСТ")],
        [KeyboardButton(text="💬 ОТВЕТИТЬ"), KeyboardButton(text="💰 ЦЕНА ПОДПИСКИ")],
        [KeyboardButton(text="🏆 ЛИДЕРБОРД"), KeyboardButton(text="📋 ЛОГИ")],
        [KeyboardButton(text="👤 ИНФО ПОЛЬЗОВАТЕЛЯ"), KeyboardButton(text="⬅️ ВЫЙТИ ИЗ АДМИНКИ")]
    ],
    resize_keyboard=True
)

async def set_main_menu(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Админ-панель (только для админа)"),
        BotCommand(command="menu", description="Показать главное меню"),
        BotCommand(command="cancel", description="Отменить текущее действие"),
        BotCommand(command="mynumber", description="Показать ваше число судьбы"),
        BotCommand(command="setcity", description="Указать ваш город")
    ])