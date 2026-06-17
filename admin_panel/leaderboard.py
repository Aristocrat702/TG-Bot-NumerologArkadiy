from aiogram import types, F
from utils import is_admin
import scheduler

def register_leaderboard_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "🏆 ЛИДЕРБОРД")
    async def leaderboard_now(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await scheduler.weekly_leaderboard(bot, message.from_user.id)
        await message.answer("Лидерборд отправлен.")