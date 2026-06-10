import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InputMediaPhoto
from keyboards import admin_menu, main_menu
from database import get_connection
from utils import is_admin, add_subscription_days

def register_admin_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("admin"))
    async def admin_panel(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            await message.answer("Нет доступа.")
            return
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
        await message.answer(f"📊 Статистика:\nВсего: {total}\nАктивных подписок: {active}")
        conn.close()

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

    # ---------- НОВАЯ РАССЫЛКА (с поддержкой фото и текста) ----------
    @dp.message(F.text == "✉️ РАССЫЛКА")
    async def broadcast_start(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer(
            "Отправьте сообщение для рассылки.\n"
            "Можно отправить текст, фото, документ – всё будет доставлено всем пользователям.\n"
            "Для отмены отправьте /cancel_broadcast"
        )
        # Сохраняем состояние, что админ собирается отправить рассылку
        dp["broadcast_msg"] = None

    @dp.message(F.text, lambda m: m.text.startswith("/cancel_broadcast"))
    async def cancel_broadcast(message: types.Message):
        dp.pop("broadcast_msg", None)
        await message.answer("Рассылка отменена.")

    @dp.message(F.content_type.in_({"text", "photo", "document", "animation", "video"}))
    async def handle_broadcast(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        if "broadcast_msg" not in dp:
            # Не в режиме рассылки – игнорируем
            return

        # Сохраняем сообщение для рассылки
        broadcast_content = message
        dp["broadcast_msg"] = broadcast_content

        # Подтверждение
        await message.answer(
            "Сообщение получено. Начинаю рассылку... Это может занять некоторое время.\n"
            "Статус будет показан по окончании."
        )

        # Получаем всех пользователей (кроме заблокированных и спящих)
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
                # Отправляем копию сообщения (копируем медиа, если есть)
                if broadcast_content.photo:
                    # Берём самое большое фото
                    photo = broadcast_content.photo[-1]
                    await bot.send_photo(user_id, photo.file_id, caption=broadcast_content.caption)
                elif broadcast_content.document:
                    await bot.send_document(user_id, broadcast_content.document.file_id, caption=broadcast_content.caption)
                elif broadcast_content.animation:
                    await bot.send_animation(user_id, broadcast_content.animation.file_id, caption=broadcast_content.caption)
                elif broadcast_content.video:
                    await bot.send_video(user_id, broadcast_content.video.file_id, caption=broadcast_content.caption)
                else:
                    await bot.send_message(user_id, broadcast_content.text)
                sent += 1
            except Exception as e:
                failed += 1
                # Логируем, но не показываем админу каждую ошибку
            await asyncio.sleep(0.05)  # пауза, чтобы не забанили

        await message.answer(f"✅ Рассылка завершена.\nОтправлено: {sent}\nОшибок: {failed}")
        dp.pop("broadcast_msg", None)

    # ---------- Остальные админ-функции (заглушки) ----------
    @dp.message(F.text == "💰 ВЫДАТЬ ПОДПИСКУ")
    async def give_sub(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("Введите user_id и дни через пробел (например 123456789 30)")
        @dp.message(F.text)
        async def process_give(msg: types.Message):
            if not is_admin(msg.from_user.id, admin_ids):
                return
            try:
                uid, days = map(int, msg.text.split())
                add_subscription_days(uid, days)
                await msg.answer(f"Выдана подписка на {days} дней пользователю {uid}")
                await bot.send_message(uid, f"Администратор выдал вам подписку на {days} дней!")
            except:
                await msg.answer("Ошибка. Формат: ID дни")
            dp.message.unregister(process_give)

    @dp.message(F.text == "⬅️ ВЫЙТИ ИЗ АДМИНКИ")
    async def exit_admin(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("Выход из админки", reply_markup=main_menu)

    @dp.message(F.text.in_(["🎫 ПРОМОКОДЫ", "🔧 ПРОМПТ", "📤 ЭКСПОРТ БАЗЫ", "🚫 БЛЭК-ЛИСТ", "💬 ОТВЕТИТЬ", "💰 ЦЕНА ПОДПИСКИ"]))
    async def placeholder(message: types.Message):
        if is_admin(message.from_user.id, admin_ids):
            await message.answer("Функция в разработке.")