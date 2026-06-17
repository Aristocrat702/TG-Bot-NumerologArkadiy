from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import main_menu
from database import get_connection
from utils import add_subscription_days, update_last_active

router = Router()

class PromoStates(StatesGroup):
    waiting_promocode = State()

@router.callback_query(F.data == "enter_promo")
async def promo_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите промокод:")
    await state.set_state(PromoStates.waiting_promocode)
    await callback.answer()

@router.message(PromoStates.waiting_promocode)
async def process_promocode(message: types.Message, state: FSMContext):
    code = message.text.strip()
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT action_value, max_uses, used_count, expires_at FROM promocodes WHERE code=?", (code,))
    promo = cursor.fetchone()
    if not promo:
        await message.answer("Неверный код.", reply_markup=main_menu)
        await state.clear()
        return
    action_days = promo[0]
    max_uses = promo[1]
    used_count = promo[2]
    expires_at = promo[3]
    if expires_at and expires_at < datetime.datetime.now().isoformat():
        await message.answer("Код просрочен.", reply_markup=main_menu)
        await state.clear()
        return
    if max_uses > 0 and used_count >= max_uses:
        await message.answer("Код уже использован.", reply_markup=main_menu)
        await state.clear()
        return
    cursor.execute("SELECT 1 FROM promocode_activations WHERE user_id=? AND code=?", (user_id, code))
    if cursor.fetchone():
        await message.answer("Вы уже активировали этот код.", reply_markup=main_menu)
        await state.clear()
        return
    add_subscription_days(user_id, action_days, check_referral=True, admin_id=0)
    cursor.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code=?", (code,))
    cursor.execute("INSERT INTO promocode_activations (user_id, code, activated_at, result_text) VALUES (?, ?, ?, ?)",
                   (user_id, code, datetime.datetime.now().isoformat(), f"+{action_days} дней"))
    conn.commit()
    conn.close()
    await message.answer(f"🎉 Поздравляем! Вы активировали промокод +{action_days} дней подписки.", reply_markup=main_menu)
    await state.clear()