from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram import Bot

# ========== ГЛАВНОЕ МЕНЮ ==========
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔢 МОЁ ЧИСЛО"), KeyboardButton(text="🎁 КАРТА ДНЯ")],
        [KeyboardButton(text="❤️ СОВМЕСТИМОСТЬ"), KeyboardButton(text="💬 КОНСУЛЬТАЦИЯ")],
        [KeyboardButton(text="🧠 ПСИХОЛОГИЯ"), KeyboardButton(text="🌟 АСТРОЛОГИЯ")],
        [KeyboardButton(text="💎 ЭКСКЛЮЗИВ"), KeyboardButton(text="🧠 СЕКСОЛОГИЯ")],
        [KeyboardButton(text="🌙 ТОЛКОВАНИЕ СНОВ"), KeyboardButton(text="👤 МОЙ ПРОФИЛЬ")]
    ],
    resize_keyboard=True
)

# ========== ПОДМЕНЮ ПСИХОЛОГИИ ==========
psycho_submenu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🧠 ПСИХОТЕСТ", callback_data="psycho_test")],
    [InlineKeyboardButton(text="😊 ДНЕВНИК НАСТРОЕНИЯ", callback_data="mood_diary")],
    [InlineKeyboardButton(text="🧠 САМОДИАГНОСТИКА СТРЕССА", callback_data="stress_test")],
    [InlineKeyboardButton(text="🧠 ТИП ЛИЧНОСТИ", callback_data="personality_test")],
    [InlineKeyboardButton(text="📘 МОИ РЕЗУЛЬТАТЫ", callback_data="my_psycho_result")],
    [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="psycho_back")]
])

# ========== ПОДМЕНЮ АСТРОЛОГИИ ==========
astro_submenu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🌌 Натальная карта", callback_data="astro_natal")],
    [InlineKeyboardButton(text="🔄 Транзиты", callback_data="astro_transits")],
    [InlineKeyboardButton(text="☀️ Соляр", callback_data="astro_solar")],
    [InlineKeyboardButton(text="📅 Гороскоп на день", callback_data="horoscope_daily")],
    [InlineKeyboardButton(text="📆 Гороскоп на месяц", callback_data="horoscope_monthly")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
])

# ========== ПОДМЕНЮ ЭКСКЛЮЗИВ ==========
premium_submenu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔮 Полная матрица судьбы", callback_data="premium_matrix")],
    [InlineKeyboardButton(text="💸 Денежный код", callback_data="premium_money_code")],
    [InlineKeyboardButton(text="🌌 Полная натальная карта", callback_data="premium_natal")],
    [InlineKeyboardButton(text="☀️ Соляр", callback_data="premium_solar")],
    [InlineKeyboardButton(text="📆 Гороскоп на месяц", callback_data="premium_horoscope_monthly")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
])

# ========== ПОДМЕНЮ СЕКСОЛОГИИ (только статьи) ==========
sexology_submenu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📚 Статьи", callback_data="sexology_articles")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
])

# ========== ПРОФИЛЬ ==========
profile_main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚙️ НАСТРОЙКИ", callback_data="settings")],
    [InlineKeyboardButton(text="⭐ КУПИТЬ ПОДПИСКУ", callback_data="buy_subscription"),
     InlineKeyboardButton(text="🎁 ПОДАРИТЬ ПОДПИСКУ", callback_data="gift_subscription")],
    [InlineKeyboardButton(text="🎁 РЕФЕРАЛЫ", callback_data="referral_info"),
     InlineKeyboardButton(text="🏆 ДОСТИЖЕНИЯ", callback_data="achievements")],
    [InlineKeyboardButton(text="🏆 РЕЙТИНГ", callback_data="leaderboard"),
     InlineKeyboardButton(text="📜 ИСТОРИЯ ЗАПРОСОВ", callback_data="history")],
    [InlineKeyboardButton(text="📊 МОЯ СТАТИСТИКА", callback_data="my_stats")],
    [InlineKeyboardButton(text="🎟️ ВВЕСТИ ПРОМОКОД", callback_data="enter_promo"),
     InlineKeyboardButton(text="👥 ДОБАВИТЬ В ГРУППУ", callback_data="add_to_group")],
    [InlineKeyboardButton(text="ℹ️ О БОТЕ", callback_data="help"),
     InlineKeyboardButton(text="✖️ ЗАКРЫТЬ", callback_data="close")]
])

# ========== ПОДМЕНЮ НАСТРОЕК ==========
profile_settings_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ Сменить имя", callback_data="change_name")],
    [InlineKeyboardButton(text="📱 Добавить/заменить телефон", callback_data="add_phone")],
    [InlineKeyboardButton(text="🌍 Добавить/заменить город", callback_data="add_city")],
    [InlineKeyboardButton(text="🕒 Указать время рождения", callback_data="add_birth_time")],
    [InlineKeyboardButton(text="📍 Указать место рождения", callback_data="add_birth_place")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")]
])

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

menu_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
])

challenge_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔥 Начать челлендж 7 дней", callback_data="start_challenge")],
    [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="challenge_progress")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
])

# ========== АДМИН-МЕНЮ ==========
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 СТАТИСТИКА АКТИВНОСТИ")],
        [KeyboardButton(text="👥 СПИСОК ЮЗЕРОВ"), KeyboardButton(text="✉️ РАССЫЛКА")],
        [KeyboardButton(text="💰 ВЫДАТЬ ПОДПИСКУ"), KeyboardButton(text="🎫 ПРОМОКОДЫ")],
        [KeyboardButton(text="🔧 ПРОМПТ"), KeyboardButton(text="📤 ЭКСПОРТ БАЗЫ")],
        [KeyboardButton(text="📤 ЭКСПОРТ АКТИВНОСТИ")],
        [KeyboardButton(text="📥 СБОР СООБЩЕНИЙ"), KeyboardButton(text="📤 ВЫГРУЗИТЬ СООБЩЕНИЯ")],
        [KeyboardButton(text="🚫 БЛЭК-ЛИСТ"), KeyboardButton(text="💬 ОТВЕТИТЬ")],
        [KeyboardButton(text="💰 ЦЕНА ПОДПИСКИ"), KeyboardButton(text="🏆 ЛИДЕРБОРД")],
        [KeyboardButton(text="📋 ЛОГИ"), KeyboardButton(text="👤 ИНФО ПОЛЬЗОВАТЕЛЯ")],
        [KeyboardButton(text="👥 УПРАВЛЕНИЕ ГРУППАМИ"), KeyboardButton(text="📤 ТЕСТ ГРУППЫ")],
        [KeyboardButton(text="🔧 УПРАВЛЕНИЕ ПРОМПТАМИ")],
        [KeyboardButton(text="📰 СТАТЬИ")],
        [KeyboardButton(text="🗑️ ОЧИСТКА БД")],
        [KeyboardButton(text="⬅️ ВЫЙТИ ИЗ АДМИНКИ")]
    ],
    resize_keyboard=True
)

def cancel_button(callback_data: str = "cancel_action") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=callback_data)]
    ])

async def set_main_menu(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
    ])