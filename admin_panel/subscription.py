from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_connection, create_user, get_user
from keyboards import admin_menu, cancel_button
from utils import is_admin, add_subscription_days, admin_log
from .states import AdminStates

def register_subscription_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "💰 ВЫДАТЬ ПОДПИСКУ")
    async def give_sub(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer(
            "Введите ID, @username или имя пользователя и количество дней через пробел.\n"
            "Примеры:\n"
            "123456789 30\n"
            "@username 30\n"
            "Алексей 30\n\n"
            "⚠️ Если пользователь ещё не написал боту /start, используйте его числовой ID.",
            reply_markup=cancel_button("admin_cancel_action")
        )
        await state.set_state(AdminStates.waiting_reply_user_id)

    @dp.message(AdminStates.waiting_reply_user_id)
    async def process_give_prompt(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        parts = message.text.strip().split()
        if len(parts) < 2:
            await message.answer(
                "Ошибка. Введите ID/username/имя и дни через пробел.\nПример: 123456789 30",
                reply_markup=cancel_button("admin_cancel_action")
            )
            return
        try:
            days = int(parts[-1])
            query = " ".join(parts[:-1])
        except ValueError:
            await message.answer(
                "Количество дней должно быть числом. Повторите ввод.",
                reply_markup=cancel_button("admin_cancel_action")
            )
            return

        user_id = None
        user_name = None
        conn = get_connection()
        cursor = conn.cursor()

        # Поиск по @username
        if query.startswith("@"):
            username = query[1:]
            try:
                chat = await bot.get_chat(f"@{username}")
                user_id = chat.id
                user_name = chat.first_name or chat.username
            except Exception as e:
                error_msg = str(e).lower()
                if "chat not found" in error_msg:
                    await message.answer(
                        f"⚠️ Пользователь @{username} не найден в Telegram.\n\n"
                        "Причина: он ещё не взаимодействовал с ботом (не написал /start).\n"
                        "Решение:\n"
                        "1. Попросите пользователя написать боту любое сообщение (например, /start).\n"
                        "2. Или узнайте его числовой ID (через @userinfobot) и введите его вместо @username.\n\n"
                        "Пример: 123456789 30",
                        reply_markup=cancel_button("admin_cancel_action")
                    )
                else:
                    await message.answer(
                        f"Ошибка при поиске @{username}: {e}",
                        reply_markup=cancel_button("admin_cancel_action")
                    )
                conn.close()
                return
        else:
            # Поиск по ID или имени
            if query.isdigit():
                uid = int(query)
                # Проверяем в БД
                cursor.execute("SELECT user_id, name FROM users WHERE user_id = ?", (uid,))
                row = cursor.fetchone()
                if row:
                    user_id = row[0]
                    user_name = row[1]
                else:
                    # Пробуем получить из Telegram по ID (даже если не писал боту, ID может сработать)
                    try:
                        chat = await bot.get_chat(uid)
                        user_id = chat.id
                        user_name = chat.first_name or chat.username or str(uid)
                    except:
                        await message.answer(
                            f"⚠️ Пользователь с ID {uid} не найден ни в БД, ни в Telegram.\n"
                            "Убедитесь, что ID верный, или попросите пользователя написать /start.",
                            reply_markup=cancel_button("admin_cancel_action")
                        )
                        conn.close()
                        return
            else:
                # Поиск по имени в БД
                cursor.execute("SELECT user_id, name FROM users WHERE LOWER(name) LIKE ?", (f"%{query.lower()}%",))
                rows = cursor.fetchall()
                if len(rows) == 0:
                    # Не нашли в БД – пробуем поискать по username в Telegram (без @)
                    try:
                        chat = await bot.get_chat(f"@{query}")
                        user_id = chat.id
                        user_name = chat.first_name or chat.username
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "chat not found" in error_msg:
                            await message.answer(
                                f"⚠️ Пользователь с именем «{query}» не найден.\n"
                                "Возможно, он ещё не взаимодействовал с ботом.\n"
                                "Попробуйте ввести его числовой ID.",
                                reply_markup=cancel_button("admin_cancel_action")
                            )
                        else:
                            await message.answer(
                                f"Ошибка: {e}",
                                reply_markup=cancel_button("admin_cancel_action")
                            )
                        conn.close()
                        return
                elif len(rows) > 1:
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"{row[1]} (ID {row[0]})", callback_data=f"select_user_{row[0]}")]
                        for row in rows[:5]
                    ])
                    await message.answer(f"Найдено несколько пользователей с именем «{query}». Выберите:", reply_markup=kb)
                    await state.update_data(give_days=days)
                    await state.set_state(AdminStates.waiting_confirm_action)
                    conn.close()
                    return
                else:
                    user_id = rows[0][0]
                    user_name = rows[0][1]

        # Если нашли user_id, но его нет в БД – создаём
        if user_id:
            existing = get_user(user_id)
            if not existing:
                create_user(user_id, name=user_name or str(user_id), birth_date=None, destiny_number=0)
                await message.answer(f"👤 Пользователь {user_id} ({user_name}) был автоматически добавлен в БД.")
            # Сохраняем в состояние
            await state.update_data(give_uid=user_id, give_days=days)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="confirm_give_yes")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="confirm_give_no")]
            ])
            conn2 = get_connection()
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT name FROM users WHERE user_id=?", (user_id,))
            row2 = cursor2.fetchone()
            conn2.close()
            name = row2[0] if row2 and row2[0] else user_name or "без имени"
            await message.answer(f"Выдать подписку на {days} дней пользователю {user_id} ({name})? Подтвердите.", reply_markup=kb)

        conn.close()

    @dp.callback_query(F.data.startswith("select_user_"), AdminStates.waiting_confirm_action)
    async def select_user_callback(callback: types.CallbackQuery, state: FSMContext):
        user_id = int(callback.data.split("_")[-1])
        data = await state.get_data()
        days = data.get("give_days", 30)
        await state.update_data(give_uid=user_id, give_days=days)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        name = row[0] if row and row[0] else "без имени"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="confirm_give_yes")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="confirm_give_no")]
        ])
        await callback.message.answer(f"Выдать подписку на {days} дней пользователю {user_id} ({name})? Подтвердите.", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data == "confirm_give_yes", AdminStates.waiting_confirm_action)
    async def confirm_give(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        uid = data.get("give_uid")
        days = data.get("give_days")
        add_subscription_days(uid, days, check_referral=True, admin_id=callback.from_user.id)
        await callback.message.answer(f"✅ Выдана подписка на {days} дней пользователю {uid}", reply_markup=admin_menu)
        try:
            await bot.send_message(uid, f"Администратор выдал вам подписку на {days} дней! Теперь вам доступны все премиум-функции бота.")
        except:
            pass
        await state.clear()
        await callback.answer()

    @dp.callback_query(F.data == "confirm_give_no", AdminStates.waiting_confirm_action)
    async def cancel_give(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.answer("Действие отменено.", reply_markup=admin_menu)
        await callback.answer()