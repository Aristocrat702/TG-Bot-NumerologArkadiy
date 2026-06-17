from aiogram import types, F
from aiogram.fsm.context import FSMContext
from keyboards import admin_menu, cancel_button
from utils import is_admin, get_bot_config, set_bot_config, admin_log
from .states import AdminStates

def register_price_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "💰 ЦЕНА ПОДПИСКИ")
    async def change_price(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        current_price_rub = get_bot_config("subscription_price_rub", "249")
        current_price_stars = int(int(current_price_rub) * 2)
        await message.answer(
            f"💰 *Текущая цена:* {current_price_rub} ₽ (≈ {current_price_stars} Stars)\n\n"
            "Введите новую цену в рублях (только число, например 249):",
            parse_mode="Markdown",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(AdminStates.waiting_new_price)

    @dp.message(AdminStates.waiting_new_price)
    async def set_price(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            price_rub = int(message.text.strip())
            stars = int(price_rub * 2)
            set_bot_config("subscription_price_rub", str(price_rub))
            set_bot_config("subscription_price_stars", str(stars))
            admin_log(message.from_user.id, "change_price", f"new_price_rub={price_rub}, stars={stars}")
            await message.answer(f"✅ Цена изменена: {price_rub} ₽ (≈ {stars} Stars)", reply_markup=admin_menu)
        except:
            await message.answer(
                "Ошибка. Введите целое число.",
                reply_markup=cancel_button("admin_cancel_action")
            )
        await state.clear()