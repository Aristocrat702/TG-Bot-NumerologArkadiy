from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards import main_menu
from database import get_connection
from utils import update_last_active

# Глобальный словарь для последнего ответа (чтобы делиться)
last_answer = {}

def register_common_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.callback_query(F.data == "close")
    async def close_profile(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "back_to_menu")
    async def back_to_menu_callback(callback: types.CallbackQuery):
        await callback.message.answer("Главное меню", reply_markup=main_menu)
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(F.data == "share_result")
    async def share_result(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        last = last_answer.get(user_id, "результат вашего обращения")
        text = f"🔮 Мой нумерологический разбор от Аркадия Викторовича:\n\n«{last[:200]}»\n\nУзнайте свою судьбу -> https://t.me/NumerologArkadiy_bot"
        await callback.message.answer(text, reply_markup=main_menu)
        await callback.answer()

    @dp.message(Command("menu"))
    async def menu_command(message: types.Message):
        await message.answer("Главное меню", reply_markup=main_menu)

    @dp.message(Command("cancel"))
    async def cancel_handler(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu)

    @dp.message(Command("unsubscribe_daily"))
    async def unsubscribe_daily(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET send_daily = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await message.answer("Вы отписались от ежедневной карты дня.")

    @dp.message(Command("subscribe_daily"))
    async def subscribe_daily(message: types.Message):
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET send_daily = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await message.answer("Вы подписались на ежедневную карту дня. Она будет приходить в 9:00 по вашему городу.")