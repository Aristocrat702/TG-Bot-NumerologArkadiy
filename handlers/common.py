from aiogram import Router, types, F
from aiogram.enums import ChatType
from keyboards import main_menu

router = Router()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: types.CallbackQuery):
    """Возвращает пользователя в главное меню (удаляет текущее сообщение и отправляет меню)."""
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Главное меню недоступно в группах.")
        await callback.answer()
        return
    await callback.message.answer("Главное меню", reply_markup=main_menu)
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "close")
async def close_callback(callback: types.CallbackQuery):
    """Закрывает текущее сообщение (удаляет его)."""
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "share_result")
async def share_result_callback(callback: types.CallbackQuery):
    """Заглушка для функции «Поделиться результатом»."""
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Поделиться результатом можно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer("Скопируйте этот текст и поделитесь с друзьями!")
    await callback.answer()