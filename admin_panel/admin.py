from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards import admin_menu, main_menu
from utils import is_admin

def register_admin_entry_handler(dp, bot, admin_ids):

    @dp.message(Command("admin"))
    async def admin_panel(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            await message.answer("Нет доступа.")
            return
        await state.clear()
        await message.answer("Админ-панель", reply_markup=admin_menu)

    @dp.message(F.text == "⬅️ ВЫЙТИ ИЗ АДМИНКИ")
    async def exit_admin(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await state.clear()
        await message.answer("Выход из админки", reply_markup=main_menu)