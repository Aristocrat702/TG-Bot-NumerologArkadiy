import datetime
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_connection
from keyboards import admin_menu, cancel_button
from utils import is_admin, admin_log
from .states import AdminStates

def register_promocodes_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "🎫 ПРОМОКОДЫ")
    async def promocodes_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
            [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos")],
            [InlineKeyboardButton(text="📊 Детальная статистика", callback_data="admin_promo_stats")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
        await message.answer("Управление промокодами:", reply_markup=keyboard)

    @dp.callback_query(F.data == "admin_create_promo")
    async def create_promo_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer(
            "Введите код (латиница/цифры, без пробелов):",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(AdminStates.waiting_promo_code)
        await callback.answer()

    @dp.message(AdminStates.waiting_promo_code)
    async def get_promo_code(message: types.Message, state: FSMContext):
        code = message.text.strip()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM promocodes WHERE code=?", (code,))
        if cursor.fetchone():
            await message.answer(
                "Такой код уже существует. Придумайте другой.",
                reply_markup=cancel_button("admin_cancel_action")
            )
            conn.close()
            return
        conn.close()
        await state.update_data(code=code)
        await message.answer(
            "Введите количество дней (целое число):",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(AdminStates.waiting_promo_days)

    @dp.message(AdminStates.waiting_promo_days)
    async def get_promo_days(message: types.Message, state: FSMContext):
        try:
            days = int(message.text.strip())
            await state.update_data(days=days)
            await message.answer(
                "Введите максимальное количество использований (0 = безлимит):",
                reply_markup=cancel_button("admin_cancel_action")
            )
            await state.set_state(AdminStates.waiting_promo_max_uses)
        except:
            await message.answer(
                "Ошибка. Введите целое число.",
                reply_markup=cancel_button("admin_cancel_action")
            )

    @dp.message(AdminStates.waiting_promo_max_uses)
    async def get_promo_max_uses(message: types.Message, state: FSMContext):
        try:
            max_uses = int(message.text.strip())
            await state.update_data(max_uses=max_uses)
            await message.answer(
                "Введите срок действия в формате ГГГГ-ММ-ДД (или 'never' для бессрочного):",
                reply_markup=cancel_button("admin_cancel_action")
            )
            await state.set_state(AdminStates.waiting_promo_expiry)
        except:
            await message.answer(
                "Ошибка. Введите целое число.",
                reply_markup=cancel_button("admin_cancel_action")
            )

    @dp.message(AdminStates.waiting_promo_expiry)
    async def get_promo_expiry(message: types.Message, state: FSMContext):
        expiry = message.text.strip()
        data = await state.get_data()
        code = data["code"]
        days = data["days"]
        max_uses = data["max_uses"]
        if expiry.lower() != "never":
            try:
                datetime.datetime.strptime(expiry, "%Y-%m-%d")
            except:
                await message.answer(
                    "Неверный формат даты. Используйте ГГГГ-ММ-ДД или 'never'.",
                    reply_markup=cancel_button("admin_cancel_action")
                )
                return
        else:
            expiry = None
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO promocodes (code, action_value, max_uses, expires_at, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       (code, days, max_uses, expiry, message.from_user.id, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        admin_log(message.from_user.id, "create_promocode", f"code={code}, days={days}, max_uses={max_uses}")
        await message.answer(f"Промокод `{code}` создан на {days} дней, лимит {max_uses}.", reply_markup=admin_menu)
        await state.clear()

    @dp.callback_query(F.data == "admin_list_promos")
    async def list_promos(callback: types.CallbackQuery):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code, action_value, max_uses, used_count, expires_at FROM promocodes")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await callback.message.answer("Нет промокодов.")
        else:
            text = "📋 Промокоды:\n\n"
            for row in rows:
                text += f"Код: {row[0]}, дней: {row[1]}, использовано: {row[3]}/{row[2]}, действует до: {row[4] or 'бессрочно'}\n"
            await callback.message.answer(text)
        await callback.answer()

    @dp.callback_query(F.data == "admin_promo_stats")
    async def promo_stats(callback: types.CallbackQuery):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code, user_id, activated_at FROM promocode_activations ORDER BY activated_at DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await callback.message.answer("Нет активаций.")
        else:
            text = "📊 Последние активации промокодов:\n\n"
            for row in rows:
                text += f"Код {row[0]}, пользователь {row[1]}, дата {row[2][:10]}\n"
            await callback.message.answer(text)
        await callback.answer()

    @dp.callback_query(F.data == "admin_back")
    async def admin_back(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.answer()