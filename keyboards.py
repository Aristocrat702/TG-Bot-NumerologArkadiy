from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram import Bot

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔮 Я Т"), KeyboardButton(text="📅 С Я")],
        [KeyboardButton(text="❤️ ССТСТЬ"), KeyboardButton(text="🎁 Т Я")],
        [KeyboardButton(text="💬 ТЬ С"), KeyboardButton(text="👤  Ь")]
    ],
    resize_keyboard=True
)

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎟️ СТ ", callback_data="enter_promo")],
    [InlineKeyboardButton(text="🔗 СТ ", callback_data="referral")],
    [InlineKeyboardButton(text="📜 СТЯ С", callback_data="history")],
    [InlineKeyboardButton(text="⚙️ СТ", callback_data="settings")],
    [InlineKeyboardButton(text="🎁 ТЬ С", callback_data="gift")],
    [InlineKeyboardButton(text="❌ ТТЬ С", callback_data="cancel_sub")],
    [InlineKeyboardButton(text="✖️ ЫТЬ", callback_data="close")]
])

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 СТТСТ"), KeyboardButton(text="👥 СС ")],
        [KeyboardButton(text="✉️ ССЫ"), KeyboardButton(text="💰 ЫТЬ С")],
        [KeyboardButton(text="🎫 Ы"), KeyboardButton(text="🔧 Т")],
        [KeyboardButton(text="📤 СТ Ы"), KeyboardButton(text="🚫 -СТ")],
        [KeyboardButton(text="💬 ТТТЬ"), KeyboardButton(text="💰  С")],
        [KeyboardButton(text="⬅️ ЫТ  ")]
    ],
    resize_keyboard=True
)

async def set_main_menu(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="апустить бота"),
        BotCommand(command="admin", description="дмин-панель (только для админа)")
    ])
