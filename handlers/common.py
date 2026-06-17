from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType
from keyboards import main_menu, menu_button

def register_common_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.callback_query(F.data == "back_to_menu")
    async def back_to_menu_callback(callback: types.CallbackQuery):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Главное меню недоступно в группах.")
            await callback.answer()
            return
        await callback.message.answer("Главное меню", reply_markup=main_menu)
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "close")
    async def close_callback(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "share_result")
    async def share_result_callback(callback: types.CallbackQuery):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Поделиться результатом можно только в личном чате.")
            await callback.answer()
            return
        # Здесь можно реализовать логику шаринга, но пока просто заглушка
        await callback.message.answer("Скопируйте этот текст и поделитесь с друзьями!")
        await callback.answer()