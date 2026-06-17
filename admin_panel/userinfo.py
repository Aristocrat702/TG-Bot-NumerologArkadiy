from aiogram import types, F
from aiogram.fsm.context import FSMContext
from database import get_connection
from keyboards import admin_menu, cancel_button
from utils import is_admin, get_dialog_history
from .states import AdminStates

def register_userinfo_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "👤 ИНФО ПОЛЬЗОВАТЕЛЯ")
    async def userinfo_start(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer(
            "Введите user_id пользователя:",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(AdminStates.waiting_userinfo)

    @dp.message(AdminStates.waiting_userinfo)
    async def userinfo_show(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            uid = int(message.text.strip())
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name, birth_date, destiny_number, subscription_active, subscription_end, reg_date, last_active, referred_by, phone, city, timezone, birth_time, birth_place FROM users WHERE user_id=?", (uid,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                await message.answer(
                    "Пользователь не найден.",
                    reply_markup=cancel_button("admin_cancel_action")
                )
                return
            name, birth, destiny, sub_active, sub_end, reg_date, last_active, referred, phone, city, timezone, birth_time, birth_place = row
            sub_status = "Активна" if sub_active else "Неактивна"
            sub_end_str = sub_end if sub_end else "—"
            history = get_dialog_history(uid, 5)
            hist_text = ""
            for role, msg, ts in history:
                hist_text += f"{ts[:16]} | {role}: {msg[:50]}\n"
            text = f"👤 *Информация о пользователе {uid}*\n\n"
            text += f"Имя: {name}\nДата: {birth}\nВремя рождения: {birth_time or '—'}\nМесто рождения: {birth_place or '—'}\nЧисло судьбы: {destiny}\nПодписка: {sub_status}\nДействительна до: {sub_end_str}\n"
            text += f"Регистрация: {reg_date[:16]}\nПоследняя активность: {last_active[:16] if last_active else '—'}\nРеферал от: {referred if referred else '—'}\nТелефон: {phone or '—'}\nГород: {city or '—'}\nЧасовой пояс: {timezone or '—'}\n\n"
            text += f"📜 *Последние 5 сообщений:*\n{hist_text}"
            await message.answer(text, parse_mode="Markdown", reply_markup=admin_menu)
        except:
            await message.answer(
                "Ошибка. Введите числовой user_id.",
                reply_markup=cancel_button("admin_cancel_action")
            )
        await state.clear()