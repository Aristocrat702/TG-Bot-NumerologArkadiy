from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram import Bot

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔮 МОЯ МАТРИЦА"), KeyboardButton(text="📅 ЧИСЛО РОЖДЕНИЯ")],
        [KeyboardButton(text="❤️ СОВМЕСТИМОСТЬ"), KeyboardButton(text="🎁 КАРТА ДНЯ")],
        [KeyboardButton(text="💬 ЗАДАТЬ ВОПРОС"), KeyboardButton(text="👤 МОЙ ПРОФИЛЬ")]
    ],
    resize_keyboard=True
)

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎟️ ВВЕСТИ ПРОМОКОД", callback_data="enter_promo")],
    [InlineKeyboardButton(text="🔗 ПРИВЕСТИ ДРУГА", callback_data="referral")],
    [InlineKeyboardButton(text="📜 ИСТОРИЯ ЗАПРОСОВ", callback_data="history")],
    [InlineKeyboardButton(text="⚙️ НАСТРОЙКИ", callback_data="settings")],
    [InlineKeyboardButton(text="🎁 ПОДАРИТЬ ПОДПИСКУ", callback_data="gift")],
    [InlineKeyboardButton(text="❌ ОТМЕНИТЬ ПОДПИСКУ", callback_data="cancel_sub")],
    [InlineKeyboardButton(text="✖️ ЗАКРЫТЬ", callback_data="close")]
])

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 СТАТИСТИКА"), KeyboardButton(text="👥 СПИСОК ЮЗЕРОВ")],
        [KeyboardButton(text="✉️ РАССЫЛКА"), KeyboardButton(text="💰 ВЫДАТЬ ПОДПИСКУ")],
        [KeyboardButton(text="🎫 ПРОМОКОДЫ"), KeyboardButton(text="🔧 ПРОМПТ")],
        [KeyboardButton(text="📤 ЭКСПОРТ БАЗЫ"), KeyboardButton(text="🚫 БЛЭК-ЛИСТ")],
        [KeyboardButton(text="💬 ОТВЕТИТЬ"), KeyboardButton(text="💰 ЦЕНА ПОДПИСКИ")],
        [KeyboardButton(text="⬅️ ВЫЙТИ ИЗ АДМИНКИ")]
    ],
    resize_keyboard=True
)

async def set_main_menu(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Админ-панель (только для админа)")
    ])
EOF