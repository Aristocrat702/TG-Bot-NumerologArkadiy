import datetime
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_connection
from keyboards import admin_menu, cancel_button
from utils import is_admin, admin_log
from .states import AdminStates

class PromoCreationStates(StatesGroup):
    waiting_code = State()
    waiting_days = State()
    waiting_max_uses = State()
    waiting_expiry = State()

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
        await message.answer("🎫 *Управление промокодами*\n\nВыберите действие:", parse_mode="Markdown", reply_markup=keyboard)

    @dp.callback_query(F.data == "admin_create_promo")
    async def create_promo_start(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        await callback.message.answer(
            "Шаг 1 из 4\n\n"
            "Введите название промокода (латиница, цифры, без пробелов).\n"
            "Пример: SUMMER2026",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(PromoCreationStates.waiting_code)
        await callback.answer()

    @dp.message(PromoCreationStates.waiting_code)
    async def get_promo_code(message: types.Message, state: FSMContext):
        code = message.text.strip()
        if not code or " " in code:
            await message.answer(
                "Код не должен содержать пробелов. Попробуйте снова.",
                reply_markup=cancel_button("admin_cancel_action")
            )
            return
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
            "Шаг 2 из 4\n\n"
            "На сколько дней подписки рассчитан промокод?\n"
            "Введите число (например, 30).",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(PromoCreationStates.waiting_days)

    @dp.message(PromoCreationStates.waiting_days)
    async def get_promo_days(message: types.Message, state: FSMContext):
        try:
            days = int(message.text.strip())
            if days <= 0:
                raise ValueError
            await state.update_data(days=days)
            await message.answer(
                "Шаг 3 из 4\n\n"
                "Сколько раз можно активировать этот промокод?\n"
                "Введите число (0 = безлимит).",
                reply_markup=cancel_button("admin_cancel_action")
            )
            await state.set_state(PromoCreationStates.waiting_max_uses)
        except:
            await message.answer(
                "Ошибка. Введите целое положительное число.",
                reply_markup=cancel_button("admin_cancel_action")
            )

    @dp.message(PromoCreationStates.waiting_max_uses)
    async def get_promo_max_uses(message: types.Message, state: FSMContext):
        try:
            max_uses = int(message.text.strip())
            if max_uses < 0:
                raise ValueError
            await state.update_data(max_uses=max_uses)
            await message.answer(
                "Шаг 4 из 4 (последний)\n\n"
                "До какого числа действует промокод?\n"
                "Введите дату в формате ГГГГ-ММ-ДД (например, 2026-12-31)\n"
                "или напишите 'never' для бессрочного действия.",
                reply_markup=cancel_button("admin_cancel_action")
            )
            await state.set_state(PromoCreationStates.waiting_expiry)
        except:
            await message.answer(
                "Ошибка. Введите целое неотрицательное число.",
                reply_markup=cancel_button("admin_cancel_action")
            )

    @dp.message(PromoCreationStates.waiting_expiry)
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
        admin_log(message.from_user.id, "create_promocode", f"code={code}, days={days}, max_uses={max_uses}, expires={expiry or 'never'}")
        await message.answer(
            f"✅ *Промокод «{code}» создан!*\n\n"
            f"• Дней подписки: {days}\n"
            f"• Макс. использований: {max_uses if max_uses > 0 else '∞ (безлимит)'}\n"
            f"• Действует до: {expiry if expiry else 'бессрочно'}\n\n"
            "Теперь пользователи могут активировать его в профиле.",
            parse_mode="Markdown",
            reply_markup=admin_menu
        )
        await state.clear()

    @dp.callback_query(F.data == "admin_list_promos")
    async def list_promos(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code, action_value, max_uses, used_count, expires_at FROM promocodes")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await callback.message.answer("📭 Нет промокодов.")
        else:
            text = "📋 *Список промокодов:*\n\n"
            for row in rows:
                code, days, max_uses, used, expires = row
                used_str = f"{used}/{max_uses if max_uses > 0 else '∞'}"
                expires_str = expires if expires else "бессрочно"
                text += f"• `{code}` — {days} дн., активаций: {used_str}, до {expires_str}\n"
            await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer()

    @dp.callback_query(F.data == "admin_promo_stats")
    async def promo_stats(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code, user_id, activated_at FROM promocode_activations ORDER BY activated_at DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await callback.message.answer("Нет активаций.")
        else:
            text = "📊 *Последние 50 активаций:*\n\n"
            for row in rows:
                code, uid, at = row
                text += f"• {code} — пользователь {uid} — {at[:10]}\n"
            await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer()

    @dp.callback_query(F.data == "admin_back")
    async def admin_back(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.message.answer("Админ-панель", reply_markup=admin_menu)
        await callback.answer()