import asyncio
import datetime
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_connection
from keyboards import admin_menu, cancel_button
from utils import admin_log, is_admin
from .states import AdminStates

def register_broadcast_handlers(dp, bot, admin_ids):

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
        if segment == "cancel":
            await state.clear()
            await callback.message.answer("Рассылка отменена.", reply_markup=admin_menu)
            await callback.answer()
            return
        await state.update_data(segment=segment)
        await callback.message.answer(
            "Отправьте сообщение для рассылки (текст, фото, документ).\nДля отмены нажмите кнопку ниже.",
            reply_markup=cancel_button("admin_cancel_action")
        )
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
        await message.answer(f"✅ Рассылка завершена.\nСегмент: {segment}\nОтправлено: {sent}\nОшибок: {failed}", reply_markup=admin_menu)
        await state.clear()