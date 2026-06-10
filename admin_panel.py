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
    set_bot_config
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
    waiting_broadcast = State()   # новое состояние для рассылки

# Глобальное состояние для рассылки (чтобы не конфликтовать с dp)
broadcast_active = {}

def register_admin_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("admin"))
    async def admin_panel(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            await message.answer("Нет доступа.")
            return
        await state.clear()
        await message.answer("Админ-панель", reply_markup=admin_menu)

    # ---------- СТАТИСТИКА ----------
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
        await message.answer(f"📊 Статистика:\nВсего: {total}\nАктивных подписок: {active}")
        conn.close()

    # ---------- СПИСОК ЮЗЕРОВ ----------
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

    # ---------- РАССЫЛКА (исправлена) ----------
    @dp.message(F.text == "✉️ РАССЫЛКА")
    async def broadcast_start(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("Отправьте сообщение для рассылки (текст, фото, документ). Для отмены /cancel_broadcast")
        await state.set_state(AdminStates.waiting_broadcast)

    @dp.message(Command("cancel_broadcast"))
    async def cancel_broadcast(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("Рассылка отменена.")

    @dp.message(AdminStates.waiting_broadcast)
    async def handle_broadcast(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await state.clear()
        await message.answer("Начинаю рассылку...")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE is_sleeping = 0")
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

        await message.answer(f"✅ Рассылка завершена.\nОтправлено: {sent}\nОшибок: {failed}")

    # ---------- ВЫДАТЬ ПОДПИСКУ ----------
    @dp.message(F.text == "💰 ВЫДАТЬ ПОДПИСКУ")
    async def give_sub(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("Введите user_id и дни через пробел (например 123456789 30)")
        await state.set_state(AdminStates.waiting_reply_user_id)

    @dp.message(AdminStates.waiting_reply_user_id)
    async def process_give(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            uid, days = map(int, message.text.split())
            add_subscription_days(uid, days, check_referral=True)
            await message.answer(f"Выдана подписка на {days} дней пользователю {uid}")
            await bot.send_message(uid, f"Администратор выдал вам подписку на {days} дней!")
        except:
            await message.answer("Ошибка. Формат: ID дни")
        await state.clear()

    # ---------- ПРОМОКОДЫ ----------
    @dp.message(F.text == "🎫 ПРОМОКОДЫ")
    async def promocodes_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
            [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos")],
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

    @dp.callback_query(F.data == "admin_back")
    async def admin_back(callback: types.CallbackQuery):
        await callback.message.delete()
        await callback.answer()

    # ---------- ЧЁРНЫЙ СПИСОК ----------
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
        await message.answer(text + "\nДля добавления отправьте /add_blacklist USER_ID [причина]\nДля удаления: /remove_blacklist USER_ID")

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

    # ---------- ЭКСПОРТ БАЗЫ ----------
    @dp.message(F.text == "📤 ЭКСПОРТ БАЗЫ")
    async def export_db(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, birth_date, destiny_number, subscription_active, subscription_end, reg_date, last_active, referred_by FROM users")
        rows = cursor.fetchall()
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_id", "name", "birth_date", "destiny_number", "subscription_active", "subscription_end", "reg_date", "last_active", "referred_by"])
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

    # ---------- ЛИДЕРБОРД ----------
    @dp.message(F.text == "🏆 ЛИДЕРБОРД")
    async def leaderboard_now(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        from scheduler import weekly_leaderboard
        await weekly_leaderboard(bot, message.from_user.id)
        await message.answer("Лидерборд отправлен.")

    # ---------- ЦЕНА ПОДПИСКИ ----------
    @dp.message(F.text == "💰 ЦЕНА ПОДПИСКИ")
    async def change_price(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("Введите новую цену подписки в рублях (только число):")
        await state.set_state(AdminStates.waiting_new_price)

    @dp.message(AdminStates.waiting_new_price)
    async def set_price(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            price = int(message.text.strip())
            set_bot_config("subscription_price", str(price))
            await message.answer(f"Цена подписки изменена на {price} ₽")
        except:
            await message.answer("Ошибка. Введите число.")
        await state.clear()

    # ---------- РЕДАКТИРОВАНИЕ ПРОМПТА ----------
    @dp.message(F.text == "🔧 ПРОМПТ")
    async def edit_prompt(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        current = get_bot_config("system_prompt", "Промпт не задан")
        await message.answer(f"Текущий промпт:\n\n{current}\n\nОтправьте новый промпт (или /cancel_prompt)")
        await state.set_state(AdminStates.waiting_new_prompt)

    @dp.message(Command("cancel_prompt"))
    async def cancel_prompt(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("Редактирование отменено.")

    @dp.message(AdminStates.waiting_new_prompt)
    async def save_new_prompt(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        new_prompt = message.text
        set_bot_config("system_prompt", new_prompt)
        await message.answer("Промпт обновлён. Изменения вступят в силу после перезапуска бота.")
        await state.clear()

    # ---------- ОТВЕТИТЬ ПОЛЬЗОВАТЕЛЮ ----------
    @dp.message(F.text == "💬 ОТВЕТИТЬ")
    async def reply_to_user_start(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("Введите user_id пользователя, которому хотите ответить:")
        await state.set_state(AdminStates.waiting_reply_user_id)

    @dp.message(AdminStates.waiting_reply_user_id)
    async def reply_get_user_id(message: types.Message, state: FSMContext):
        try:
            user_id = int(message.text.strip())
            await state.update_data(reply_user_id=user_id)
            await message.answer("Введите текст ответа (можно с форматированием):")
            await state.set_state(AdminStates.waiting_reply_text)
        except:
            await message.answer("Ошибка. Введите числовой user_id.")

    @dp.message(AdminStates.waiting_reply_text)
    async def reply_send_message(message: types.Message, state: FSMContext):
        data = await state.get_data()
        user_id = data.get("reply_user_id")
        text = message.text
        try:
            await bot.send_message(user_id, f"✉️ Сообщение от администратора:\n\n{text}")
            await message.answer(f"Сообщение отправлено пользователю {user_id}.")
        except Exception as e:
            await message.answer(f"Ошибка при отправке: {e}")
        await state.clear()

    # ---------- ВЫХОД ИЗ АДМИНКИ ----------
    @dp.message(F.text == "⬅️ ВЫЙТИ ИЗ АДМИНКИ")
    async def exit_admin(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await state.clear()
        await message.answer("Выход из админки", reply_markup=main_menu)