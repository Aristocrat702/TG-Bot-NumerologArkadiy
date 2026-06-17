from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram import Bot

# Главное меню (Reply)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔮 МОЯ МАТРИЦА"), KeyboardButton(text="🔢 МОЁ ЧИСЛО")],
        [KeyboardButton(text="❤️ СОВМЕСТИМОСТЬ"), KeyboardButton(text="🎁 КАРТА ДНЯ")],
        [KeyboardButton(text="💬 ЗАДАТЬ ВОПРОС"), KeyboardButton(text="🧠 ПСИХОЛОГИЯ")],
        [KeyboardButton(text="🌟 АСТРОЛОГИЯ"), KeyboardButton(text="👤 МОЙ ПРОФИЛЬ")]
    ],
    resize_keyboard=True
)

# Подменю психологии (Inline)
psycho_submenu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🧠 ПСИХОТЕСТ", callback_data="psycho_test")],
    [InlineKeyboardButton(text="😊 ДНЕВНИК НАСТРОЕНИЯ", callback_data="mood_diary")],
    [InlineKeyboardButton(text="🎨 СТИЛЬ И УДАЧА", callback_data="style_test")],
    [InlineKeyboardButton(text="📘 МОИ РЕЗУЛЬТАТЫ ТЕСТА", callback_data="my_psycho_result")],
    [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="psycho_back")]
])

# Подменю астрологии (Inline)
astro_submenu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🌌 Натальная карта", callback_data="astro_natal")],
    [InlineKeyboardButton(text="🔄 Транзиты", callback_data="astro_transits")],
    [InlineKeyboardButton(text="☀️ Соляр", callback_data="astro_solar")],
    [InlineKeyboardButton(text="♊ Совместимость по знакам", callback_data="astro_compatibility")],
    [InlineKeyboardButton(text="📅 Гороскоп на день", callback_data="horoscope_daily")],
    [InlineKeyboardButton(text="📆 Гороскоп на месяц", callback_data="horoscope_monthly")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
])

# Меню профиля (Inline) – без кнопки «ОТМЕНИТЬ ПОДПИСКУ»
profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ СМЕНИТЬ ИМЯ", callback_data="change_name")],
    [InlineKeyboardButton(text="🎁 БЕСПЛАТНЫЕ ДНИ", callback_data="referral_info"),
     InlineKeyboardButton(text="🏆 ДОСТИЖЕНИЯ", callback_data="achievements")],
    [InlineKeyboardButton(text="⭐ КУПИТЬ ПОДПИСКУ", callback_data="buy_subscription"),
     InlineKeyboardButton(text="🎁 ПОДАРИТЬ", callback_data="gift_subscription")],
    [InlineKeyboardButton(text="⚙️ НАСТРОЙКИ", callback_data="settings")],
    [InlineKeyboardButton(text="📜 ИСТОРИЯ ЗАПРОСОВ", callback_data="history")],
    [InlineKeyboardButton(text="🎟️ ВВЕСТИ ПРОМОКОД", callback_data="enter_promo")],
    [InlineKeyboardButton(text="👥 ПРИГЛАСИТЬ В ГРУППУ", callback_data="add_to_group")],
    [InlineKeyboardButton(text="❓ ПОМОЩЬ", callback_data="help")],
    [InlineKeyboardButton(text="✖️ ЗАКРЫТЬ", callback_data="close")]
])

# Быстрые темы для числа судьбы (Inline)
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

# Универсальная кнопка «Главное меню» (Inline)
menu_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
])

# Меню челленджа (Inline) – ДОБАВЛЕНО
challenge_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔥 Начать челлендж 7 дней", callback_data="start_challenge")],
    [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="challenge_progress")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
])

# Админ-меню (Reply) – скрыто от пользователей
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 СТАТИСТИКА"), KeyboardButton(text="👥 СПИСОК ЮЗЕРОВ")],
        [KeyboardButton(text="✉️ РАССЫЛКА"), KeyboardButton(text="💰 ВЫДАТЬ ПОДПИСКУ")],
        [KeyboardButton(text="🎫 ПРОМОКОДЫ"), KeyboardButton(text="🔧 ПРОМПТ")],
        [KeyboardButton(text="📤 ЭКСПОРТ БАЗЫ"), KeyboardButton(text="🚫 БЛЭК-ЛИСТ")],
        [KeyboardButton(text="💬 ОТВЕТИТЬ"), KeyboardButton(text="💰 ЦЕНА ПОДПИСКИ")],
        [KeyboardButton(text="🏆 ЛИДЕРБОРД"), KeyboardButton(text="📋 ЛОГИ")],
        [KeyboardButton(text="👤 ИНФО ПОЛЬЗОВАТЕЛЯ"), KeyboardButton(text="👥 УПРАВЛЕНИЕ ГРУППАМИ")],
        [KeyboardButton(text="⬅️ ВЫЙТИ ИЗ АДМИНКИ")]
    ],
    resize_keyboard=True
)

# Функция для установки команд бота (вызывается при старте)
async def set_main_menu(bot: Bot):
    # Убираем все команды из меню, кроме /start (и /admin скрыто)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        # /admin не показываем
    ])