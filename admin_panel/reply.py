from aiogram import types, F
from aiogram.fsm.context import FSMContext
from keyboards import admin_menu, cancel_button
from utils import is_admin, admin_log
from .states import AdminStates

def register_reply_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "💬 ОТВЕТИТЬ")
    async def reply_to_user_start(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer(
            "Введите ID пользователя, которому хотите ответить:",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(AdminStates.waiting_reply_user_id)

    @dp.message(AdminStates.waiting_reply_user_id)
    async def reply_to_user_get_id(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            uid = int(message.text.strip())
            await state.update_data(reply_uid=uid)
            await message.answer(
                f"Введите текст сообщения для пользователя {uid} (можно с HTML-разметкой):",
                reply_markup=cancel_button("admin_cancel_action")
            )
            await state.set_state(AdminStates.waiting_reply_text)
        except:
            await message.answer(
                "Ошибка. Введите числовой ID.",
                reply_markup=cancel_button("admin_cancel_action")
            )

    @dp.message(AdminStates.waiting_reply_text)
    async def reply_to_user_send(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        data = await state.get_data()
        uid = data.get("reply_uid")
        text = message.text
        try:
            await bot.send_message(uid, f"✉️ *Сообщение от администратора:*\n\n{text}", parse_mode="HTML")
            admin_log(message.from_user.id, "reply_to_user", f"user_id={uid}")
            await message.answer(f"✅ Сообщение отправлено пользователю {uid}.", reply_markup=admin_menu)
        except Exception as e:
            await message.answer(
                f"❌ Ошибка отправки: {str(e)}",
                reply_markup=cancel_button("admin_cancel_action")
            )
        await state.clear()