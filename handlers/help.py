from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from keyboards import menu_button

def register_help_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("help"))
    async def help_command(message: types.Message):
        text = (
            "❓ *Помощь по боту «Аркадий Викторович»*\n\n"
            "🌟 *Основные команды:*\n"
            "• /start – запустить бота\n"
            "• /menu – главное меню\n"
            "• /mynumber – узнать ваше число судьбы\n"
            "• /setcity – указать ваш город\n"
            "• /setbirth – указать время и место рождения\n"
            "• /cancel – отменить текущее действие\n\n"
            "🧠 *Разделы:*\n"
            "• 🔮 МОЯ МАТРИЦА – полная матрица судьбы (по подписке)\n"
            "• 🔢 МОЁ ЧИСЛО – характеристика числа судьбы\n"
            "• ❤️ СОВМЕСТИМОСТЬ – совместимость с партнёром\n"
            "• 🎁 КАРТА ДНЯ – прогноз на день\n"
            "• 💬 ЗАДАТЬ ВОПРОС – вопросы по нумерологии/психологии\n"
            "• 🧠 ПСИХОЛОГИЯ – тесты, дневник настроения\n"
            "• 🌟 АСТРОЛОГИЯ – натальная карта, транзиты, соляр\n"
            "• 👤 МОЙ ПРОФИЛЬ – управление подпиской, рефералы, настройки\n\n"
            "💎 *Подписка (249 ₽/мес):*\n"
            "• Полная матрица судьбы\n"
            "• Безлимитные вопросы\n"
            "• Ежедневная карта дня\n"
            "• Гороскоп на месяц\n"
            "• Еженедельные мотивирующие фразы\n\n"
            "📌 *Для групп:*\n"
            "Добавьте бота в чат и активируйте командой /start_bot.\n"
            "Настройте тип контента: /set_chat_type daily_motivation (мотивация), horoscope (гороскоп), advice (совет).\n\n"
            "👥 *Поддержка:* @Aristocrat102\n"
            "Версия бота: 2.1.0"
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=menu_button)