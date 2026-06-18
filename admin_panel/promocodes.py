import datetime
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_connection
from keyboards import admin_menu, cancel_button
from utils import is_admin, admin_log
from .states import AdminStates

# Дополнительные состояния для создания промокода
class PromoCreationStates(StatesGroup):
    waiting_code = State()
    waiting_days = State()
    waiting_max_uses = State()
    waiting_expiry = State()
    waiting_confirm = State()

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
        await message.answer("🎫 <b>Управление промокодами</b>\n\nВыберите действие:", parse_mode="HTML", reply_markup=keyboard)

    # ===== НОВЫЙ МАСТЕР СОЗДАНИЯ ПРОМОКОДА =====
    @dp.callback_query(F.data == "admin_create_promo")
    async def create_promo_start(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        await callback.message.answer(
            "🆕 <b>Создание нового промокода</b>\n\n"
            "Шаг 1: Введите название промокода (латиница, цифры, без пробелов).\n"
            "Например: <code>SUMMER2026</code>",
            parse_mode="HTML",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(PromoCreationStates.waiting_code)
        await callback.answer()

    @dp.message(PromoCreationStates.waiting_code)
    async def promo_get_code(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        code = message.text.strip()
        if not code or len(code) < 3:
            await message.answer(
                "⚠️ Код должен быть не менее 3 символов. Попробуйте снова:",
                reply_markup=cancel_button("admin_cancel_action")
            )
            return
        # Проверка на существование
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM promocodes WHERE code=?", (code,))
        if cursor.fetchone():
            await message.answer(
                f"⚠️ Код <code>{code}</code> уже существует. Придумайте другой.",
                parse_mode="HTML",
                reply_markup=cancel_button("admin_cancel_action")
            )
            conn.close()
            return
        conn.close()
        await state.update_data(code=code)
        await message.answer(
            "✅ Код принят.\n\n"
            "Шаг 2: На сколько дней подписки действует промокод?\n"
            "Введите число (например, <code>30</code>):",
            parse_mode="HTML",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(PromoCreationStates.waiting_days)

    @dp.message(PromoCreationStates.waiting_days)
    async def promo_get_days(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            days = int(message.text.strip())
            if days <= 0:
                raise ValueError
        except:
            await message.answer(
                "⚠️ Введите целое положительное число (например, 30).",
                reply_markup=cancel_button("admin_cancel_action")
            )
            return
        await state.update_data(days=days)
        await message.answer(
            f"✅ Количество дней: <b>{days}</b>\n\n"
            "Шаг 3: Сколько раз можно активировать этот промокод?\n"
            "Введите число (например, <code>100</code>) или <code>0</code> для безлимита:",
            parse_mode="HTML",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(PromoCreationStates.waiting_max_uses)

    @dp.message(PromoCreationStates.waiting_max_uses)
    async def promo_get_max_uses(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            max_uses = int(message.text.strip())
            if max_uses < 0:
                raise ValueError
        except:
            await message.answer(
                "⚠️ Введите целое неотрицательное число (0 – безлимит).",
                reply_markup=cancel_button("admin_cancel_action")
            )
            return
        await state.update_data(max_uses=max_uses)
        await message.answer(
            f"✅ Максимум использований: <b>{'безлимит' if max_uses == 0 else max_uses}</b>\n\n"
            "Шаг 4: До какого числа действует промокод?\n"
            "Введите дату в формате <b>ГГГГ-ММ-ДД</b> (например, <code>2026-09-01</code>) или напишите <code>never</code> для бессрочного:",
            parse_mode="HTML",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(PromoCreationStates.waiting_expiry)

    @dp.message(PromoCreationStates.waiting_expiry)
    async def promo_get_expiry(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        expiry = message.text.strip().lower()
        if expiry == "never":
            expiry_date = None
        else:
            try:
                datetime.datetime.strptime(expiry, "%Y-%m-%d")
                expiry_date = expiry
            except:
                await message.answer(
                    "⚠️ Неверный формат даты. Используйте ГГГГ-ММ-ДД или 'never'.",
                    reply_markup=cancel_button("admin_cancel_action")
                )
                return
        await state.update_data(expiry=expiry_date)

        # Получаем все данные для подтверждения
        data = await state.get_data()
        code = data["code"]
        days = data["days"]
        max_uses = data["max_uses"]
        expiry_str = expiry_date if expiry_date else "бессрочно"

        # Показываем итоговую информацию и запрашиваем подтверждение
        confirm_text = (
            f"📋 <b>Проверьте данные промокода:</b>\n\n"
            f"🔹 <b>Код:</b> <code>{code}</code>\n"
            f"🔹 <b>Дней подписки:</b> {days}\n"
            f"🔹 <b>Макс. использований:</b> {'безлимит' if max_uses == 0 else max_uses}\n"
            f"🔹 <b>Действует до:</b> {expiry_str}\n\n"
            "Всё верно?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, создать", callback_data="promo_confirm_yes")],
            [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="admin_cancel_action")]
        ])
        await message.answer(confirm_text, parse_mode="HTML", reply_markup=kb)
        await state.set_state(PromoCreationStates.waiting_confirm)

    @dp.callback_query(F.data == "promo_confirm_yes", PromoCreationStates.waiting_confirm)
    async def promo_confirm_yes(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        data = await state.get_data()
        code = data["code"]
        days = data["days"]
        max_uses = data["max_uses"]
        expiry = data.get("expiry")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO promocodes (code, action_value, max_uses, expires_at, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code, days, max_uses, expiry, callback.from_user.id, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()

        admin_log(callback.from_user.id, "create_promocode", f"code={code}, days={days}, max_uses={max_uses}, expiry={expiry}")

        await callback.message.answer(
            f"✅ <b>Промокод успешно создан!</b>\n\n"
            f"🔹 <b>Код:</b> <code>{code}</code>\n"
            f"🔹 <b>Дней подписки:</b> {days}\n"
            f"🔹 <b>Макс. использований:</b> {'безлимит' if max_uses == 0 else max_uses}\n"
            f"🔹 <b>Действует до:</b> {expiry if expiry else 'бессрочно'}\n\n"
            "Вы можете поделиться этим кодом с пользователями.",
            parse_mode="HTML",
            reply_markup=admin_menu
        )
        await state.clear()
        await callback.answer()

    # ===== СПИСОК ПРОМОКОДОВ =====
    @dp.callback_query(F.data == "admin_list_promos")
    async def list_promos(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT code, action_value, max_uses, used_count, expires_at FROM promocodes ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await callback.message.answer("📭 Нет промокодов.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
            ]))
        else:
            text = "📋 <b>Список промокодов:</b>\n\n"
            for row in rows:
                code, days, max_uses, used, expires = row
                expiry_str = expires if expires else "бессрочно"
                text += f"🔹 <code>{code}</code> – {days} дн., использовано {used}/{max_uses if max_uses > 0 else '∞'}, действует до {expiry_str}\n"
            await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()

    # ===== СТАТИСТИКА АКТИВАЦИЙ =====
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
            await callback.message.answer("📊 Нет активаций промокодов.")
        else:
            text = "📊 <b>Последние 50 активаций промокодов:</b>\n\n"
            for row in rows:
                code, user_id, activated = row
                text += f"🔹 <code>{code}</code> – пользователь {user_id}, {activated[:10]}\n"
            await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()

    # ===== ВОЗВРАТ В АДМИНКУ =====
    @dp.callback_query(F.data == "admin_back")
    async def admin_back(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.message.answer("Админ-панель", reply_markup=admin_menu)
        await callback.answer()