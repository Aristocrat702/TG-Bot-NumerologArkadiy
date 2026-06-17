from aiogram import types, F
from aiogram.fsm.context import FSMContext
from keyboards import admin_menu, cancel_button
from utils import is_admin, get_bot_config, set_bot_config, admin_log
from .states import AdminStates

def register_prompt_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "🔧 ПРОМПТ")
    async def prompt_menu(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        current_prompt = get_bot_config("system_prompt", "Не установлен")
        await message.answer(
            f"📝 *Текущий системный промпт:*\n\n{current_prompt}\n\n"
            "Чтобы изменить, введите новый текст промпта (он заменит текущий).",
            parse_mode="Markdown",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(AdminStates.waiting_new_prompt)

    @dp.message(AdminStates.waiting_new_prompt)
    async def set_prompt(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        new_prompt = message.text.strip()
        if len(new_prompt) < 10:
            await message.answer(
                "Промпт должен быть не менее 10 символов. Попробуйте снова.",
                reply_markup=cancel_button("admin_cancel_action")
            )
            return
        set_bot_config("system_prompt", new_prompt)
        admin_log(message.from_user.id, "change_prompt", f"new_prompt_length={len(new_prompt)}")
        await message.answer("✅ Системный промпт обновлён!", reply_markup=admin_menu)
        await state.clear()