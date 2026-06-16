import asyncio
import csv
import io
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from keyboards import admin_menu, main_menu
from database import get_connection
from utils import (
    is_admin, add_subscription_days, add_to_blacklist,
    remove_from_blacklist, backup_database, get_bot_config,
    set_bot_config, admin_log
)

class AdminStates(StatesGroup):
    waiting_promo_code = State()
    waiting_promo_days = State()
    waiting_promo_max_uses = State()
    waiting_promo_expiry = State()
    waiting_reply_user_id = State()
    waiting_reply_text = State()
    waiting_new_price = State()
    waiting_new_prompt = State()
    waiting_broadcast = State()
    waiting_broadcast_segment = State()
    waiting_userinfo = State()
    waiting_confirm_action = State()

def register_admin_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("admin"))
    async def admin_panel(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            await message.answer("Нет доступа.")
            return
        await state.clear()
        await message.answer("Админ-панель", reply_markup=admin_menu)

    @dp.message(F.text == "📊 СТАТИСТИКА")
    async def admin_stats(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_active=1")
        active = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM group_chats WHERE is_active=1")
        active_groups = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM group_chats")
        total_groups = cursor.fetchone()[0]
        conn.close()
        await message.answer(f"📊 *Статистика*\n\n👥 Пользователей: {total}\n💎 Активных подписок: {active}\n👥 Групп (всего): {total_groups}\n✅ Активных групп: {active_groups}", parse_mode="Markdown")

    @dp.message(F.text == "👥 СПИСОК ЮЗЕРОВ")
    async def list_users(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, subscription_active FROM users LIMIT 20")
        rows = cursor.fetchall()
        text = "Последние 20:\n"
        for r in rows:
            text += f"ID: {r[0]}, Имя: {r[1]}, Подписка: {'да' if r[2] else 'нет'}\n"
        await message.answer(text)
        conn.close()

    @dp.message(F.text == "✉️ РАССЫЛКА")
    async def broadcast_start(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="broadcast_all")],
            [InlineKeyboardButton(text="💎 Только подписчикам", callback_data="broadcast_subscribers")],
            [InlineKeyboardButton(text="🆕 Новым (за 7 дней)", callback_data="broadcast_new")],
            [InlineKeyboardButton(text="🧪 Тестовый (только админу)", callback_data="broadcast_test")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")]
        ])
        await message.answer("Выберите сегмент для рассылки:", reply_markup=kb)
        await state.set_state(AdminStates.waiting_broadcast_segment)

    @dp.callback_query(F.data.startswith("broadcast_"), AdminStates.waiting_broadcast_segment)
    async def broadcast_select_segment(callback: types.CallbackQuery, state: FSMContext):
        segment = callback.data.split("_")[1]
        await state.update_data(segment=segment)
        await callback.message.answer("Отправьте сообщение для рассылки (текст, фото, документ). Для отмены /cancel")
        await state.set_state(AdminStates.waiting_broadcast)
        await callback.answer()

    @dp.message(AdminStates.waiting_broadcast)
    async def handle_broadcast(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        data = await state.get_data()
        segment = data.get("segment", "all")
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
        if segment == "all":
            cursor.execute("SELECT user_id FROM users WHERE is_sleeping = 0")
        elif segment == "subscribers":
            cursor.execute("SELECT user_id FROM users WHERE subscription_active=1 AND is_sleeping=0")
        elif segment == "new":
            cursor.execute("SELECT user_id FROM users WHERE reg_date >= ? AND is_sleeping=0", (week_ago,))
        else:  # test
            users = [(message.from_user.id,)]
            await message.answer("Тестовая рассылка только для вас.")
        if segment != "test":
            users = cursor.fetchall()
        conn.close()

        sent = 0
        failed = 0
        for user in users:
            user_id = user[0]
            try:
                if message.photo:
                    photo = message.photo[-1]
                    await bot.send_photo(user_id, photo.file_id, caption=message.caption)
                elif message.document:
                    await bot.send_document(user_id, message.document.file_id, caption=message.caption)
                elif message.animation:
                    await bot.send_animation(user_id, message.animation.file_id, caption=message.caption)
                elif message.video:
                    await bot.send_video(user_id, message.video.file_id, caption=message.caption)
                else:
                    await bot.send_message(user_id, message.text)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
        admin_log(message.from_user.id, "broadcast", f"segment={segment}, sent={sent}, failed={failed}")
        await message.answer(f"✅ Рассылка завершена.\nСегмент: {segment}\nОтправлено: {sent}\nОшибок: {failed}")
        await state.clear()

    @dp.callback_query(F.data == "broadcast_cancel")
    async def broadcast_cancel(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.answer("Рассылка отменена.")
        await callback.answer()

    @dp.message(F.text == "💰 ВЫДАТЬ ПОДПИСКУ")
    async def give_sub(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("Введите user_id и дни через пробел (например 123456789 30)")
        await state.set_state(AdminStates.waiting_reply_user_id)

    @dp.message(AdminStates.waiting_reply_user_id)
    async def process_give_prompt(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            uid, days = map(int, message.text.split())
            await state.update_data(give_uid=uid, give_days=days)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="confirm_give_yes")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="confirm_give_no")]
            ])
            await message.answer(f"Выдать подписку на {days} дней пользователю {uid}? Подтвердите.", reply_markup=kb)
            await state.set_state(AdminStates.waiting_confirm_action)
        except:
            await message.answer("Ошибка. Формат: ID дни")

    @dp.callback_query(F.data == "confirm_give_yes", AdminStates.waiting_confirm_action)
    async def confirm_give(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        uid = data.get("give_uid")
        days = data.get("give_days")
        add_subscription_days(uid, days, check_referral=True, admin_id=callback.from_user.id)
        await callback.message.answer(f"Выдана подписка на {days} дней пользователю {uid}")
        await bot.send_message(uid, f"Администратор выдал вам подписку на {days} дней!")
        await state.clear()
        await callback.answer()

    @dp.callback_query(F.data == "confirm_give_no", AdminStates.waiting_confirm_action)
    async def cancel_give(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.answer("Действие отменено.")
        await callback.answer()

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
        await callback.message.answer("Введите код (латиница/цифры, без пробелов):")
        await state.set_state(AdminStates.waiting_promo_code)
        await callback.answer()

    @dp.message(AdminStates.waiting_promo_code)
    async def get_promo_code(message: types.Message, state: FSMContext):
        code = message.text.strip()
        await state.update_data(code=code)
        await message.answer("Введите количество дней (целое число):")
        await state.set_state(AdminStates.waiting_promo_days)

    @dp.message(AdminStates.waiting_promo_days)
    async def get_promo_days(message: types.Message, state: FSMContext):
        try:
            days = int(message.text.strip())
            await state.update_data(days=days)
            await message.answer("Введите максимальное количество использований (0 = безлимит):")
            await state.set_state(AdminStates.waiting_promo_max_uses)
        except:
            await message.answer("Ошибка. Введите целое число.")

    @dp.message(AdminStates.waiting_promo_max_uses)
    async def get_promo_max_uses(message: types.Message, state: FSMContext):
        try:
            max_uses = int(message.text.strip())
            await state.update_data(max_uses=max_uses)
            await message.answer("Введите срок действия в формате ГГГГ-ММ-ДД (или 'never' для бессрочного):")
            await state.set_state(AdminStates.waiting_promo_expiry)
        except:
            await message.answer("Ошибка. Введите целое число.")

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
                await message.answer("Неверный формат даты. Используйте ГГГГ-ММ-ДД или 'never'")
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
        await message.answer(f"Промокод `{code}` создан на {days} дней, лимит {max_uses}.")
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

    @dp.message(F.text == "🚫 БЛЭК-ЛИСТ")
    async def blacklist_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, reason FROM blacklist")
        rows = cursor.fetchall()
        conn.close()
        text = "Чёрный список:\n"
        if not rows:
            text += "пуст"
        else:
            for r in rows:
                text += f"ID: {r[0]}, причина: {r[1]}\n"
        await message.answer(text + "\n\n➕ Добавить: /add_blacklist USER_ID [причина]\n🗑 Удалить: /remove_blacklist USER_ID")

    @dp.message(Command("add_blacklist"))
    async def add_blacklist(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.answer("Использование: /add_blacklist USER_ID [причина]")
            return
        user_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else ""
        add_to_blacklist(user_id, reason)
        await message.answer(f"Пользователь {user_id} добавлен в чёрный список.")
        try:
            await bot.send_message(user_id, "🚫 Вы были заблокированы администратором. Если считаете это ошибкой, свяжитесь с @Aristocrat102")
        except:
            pass

    @dp.message(Command("remove_blacklist"))
    async def remove_blacklist(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /remove_blacklist USER_ID")
            return
        user_id = int(parts[1])
        remove_from_blacklist(user_id)
        await message.answer(f"Пользователь {user_id} удалён из чёрного списка.")

    @dp.message(F.text == "📤 ЭКСПОРТ БАЗЫ")
    async def export_db(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, birth_date, destiny_number, subscription_active, subscription_end, reg_date, last_active, referred_by, phone, city, timezone, birth_time, birth_place FROM users")
        rows = cursor.fetchall()
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_id", "name", "birth_date", "destiny_number", "subscription_active", "subscription_end", "reg_date", "last_active", "referred_by", "phone", "city", "timezone", "birth_time", "birth_place"])
        writer.writerows(rows)
        csv_data = output.getvalue().encode("utf-8")
        await message.answer_document(types.BufferedInputFile(csv_data, filename="users_export.csv"))
        await message.answer("Также можно скачать резервную копию БД: /download_backup")

    @dp.message(Command("download_backup"))
    async def download_backup(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        backup_path = backup_database()
        await message.answer_document(FSInputFile(backup_path))

    @dp.message(F.text == "🏆 ЛИДЕРБОРД")
    async def leaderboard_now(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        from scheduler import weekly_leaderboard
        await weekly_leaderboard(bot, message.from_user.id)
        await message.answer("Лидерборд отправлен.")

    @dp.message(F.text == "📋 ЛОГИ")
    async def show_logs(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT admin_id, action, details, created_at FROM admin_logs ORDER BY created_at DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            text = "Логи пусты."
        else:
            text = "📋 Последние действия:\n\n"
            for row in rows:
                text += f"{row[3][:16]} | admin {row[0]} | {row[1]} | {row[2]}\n"
        await message.answer(text)

    @dp.message(F.text == "👤 ИНФО ПОЛЬЗОВАТЕЛЯ")
    async def userinfo_start(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("Введите user_id пользователя:")
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
                await message.answer("Пользователь не найден.")
                await state.clear()
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
            await message.answer(text, parse_mode="Markdown")
        except:
            await message.answer("Ошибка. Введите числовой user_id.")
        await state.clear()

    # ---------- УПРАВЛЕНИЕ ГРУППАМИ (ТОЛЬКО ДЛЯ АДМИНА) ----------
    @dp.message(F.text == "👥 УПРАВЛЕНИЕ ГРУППАМИ")
    async def groups_management_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 ГЛОБАЛЬНАЯ ЧАСТОТА", callback_data="admin_global_frequency")],
            [InlineKeyboardButton(text="📋 СПИСОК ВСЕХ ГРУПП", callback_data="admin_list_all_groups")],
            [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_back")]
        ])
        await message.answer("👥 *Управление группами*\n\nВыберите действие:", parse_mode="Markdown", reply_markup=kb)

    @dp.callback_query(F.data == "admin_global_frequency")
    async def set_global_frequency(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 сообщение в час", callback_data="admin_set_global_freq_1")],
            [InlineKeyboardButton(text="2 сообщения в час", callback_data="admin_set_global_freq_2")],
            [InlineKeyboardButton(text="3 сообщения в час", callback_data="admin_set_global_freq_3")],
            [InlineKeyboardButton(text="4 сообщения в час", callback_data="admin_set_global_freq_4")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]
        ])
        await callback.message.edit_text("🌐 *Глобальная частота*\n\nВыберите количество сообщений в час для всех групп (по умолчанию 2):", parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_set_global_freq_"))
    async def set_global_frequency_value(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        freq = int(callback.data.split("_")[-1])
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE group_chats SET frequency = ?", (freq,))
        conn.commit()
        conn.close()
        await callback.message.edit_text(f"✅ Глобальная частота установлена: {freq} сообщения в час для всех групп.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]]))
        await callback.answer()

    @dp.callback_query(F.data == "admin_list_all_groups")
    async def list_all_groups(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, is_active, frequency, created_at FROM group_chats ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await callback.message.edit_text("Нет активных групп.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]]))
            await callback.answer()
            return
        text = "📋 *Список групп:*\n\n"
        for row in rows:
            chat_id, is_active, freq, created_at = row
            status = "✅ Активна" if is_active else "❌ Неактивна"
            text += f"Чат: {chat_id}\nСтатус: {status}\nЧастота: {freq} сообщ/час\nДата: {created_at[:10]}\n\n"
        # Добавляем кнопку для каждой группы (пока только первая группа для примера)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_groups_back")]
        ])
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data == "admin_groups_back")
    async def groups_back(callback: types.CallbackQuery):
        await groups_management_menu(callback.message)
        await callback.answer()

    @dp.message(F.text == "⬅️ ВЫЙТИ ИЗ АДМИНКИ")
    async def exit_admin(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await state.clear()
        await message.answer("Выход из админки", reply_markup=main_menu)