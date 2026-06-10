import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from keyboards import admin_menu, main_menu
from database import get_connection
from utils import is_admin, add_subscription_days

def register_admin_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(Command("admin"))
    async def admin_panel(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            await message.answer("ет доступа.")
            return
        await message.answer("дмин-панель", reply_markup=admin_menu)

    @dp.message(F.text == "📊 СТТСТ")
    async def admin_stats(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_active=1")
        active = cursor.fetchone()[0]
        await message.answer(f"📊 Статистика:\nсего: {total}\nктивных подписок: {active}")
        conn.close()

    @dp.message(F.text == "👥 СС ")
    async def list_users(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, subscription_active FROM users LIMIT 20")
        rows = cursor.fetchall()
        text = "оследние 20:\n"
        for r in rows:
            text += f"ID: {r[0]}, мя: {r[1]}, одписка: {'да' if r[2] else 'нет'}\n"
        await message.answer(text)
        conn.close()

    @dp.message(F.text == "✉️ ССЫ")
    async def broadcast_start(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("ведите текст рассылки:")
        @dp.message(F.text)
        async def send_broadcast(msg: types.Message):
            if not is_admin(msg.from_user.id, admin_ids):
                return
            text = msg.text
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE is_sleeping=0")
            users = cursor.fetchall()
            conn.close()
            sent = 0
            for u in users:
                try:
                    await bot.send_message(u[0], text)
                    sent += 1
                    await asyncio.sleep(0.05)
                except:
                    pass
            await msg.answer(f"тправлено {sent} пользователям.")
            dp.message.unregister(send_broadcast)

    @dp.message(F.text == "💰 ЫТЬ С")
    async def give_sub(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("ведите user_id и дни через пробел (например 123456789 30)")
        @dp.message(F.text)
        async def process_give(msg: types.Message):
            if not is_admin(msg.from_user.id, admin_ids):
                return
            try:
                uid, days = map(int, msg.text.split())
                add_subscription_days(uid, days)
                await msg.answer(f"ыдана подписка на {days} дней пользователю {uid}")
                await bot.send_message(uid, f"дминистратор выдал вам подписку на {days} дней!")
            except:
                await msg.answer("шибка. ормат: ID дни")
            dp.message.unregister(process_give)

    @dp.message(F.text == "⬅️ ЫТ  ")
    async def exit_admin(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        await message.answer("ыход из админки", reply_markup=main_menu)

    @dp.message(F.text.in_(["🎫 Ы", "🔧 Т", "📤 СТ Ы", "🚫 -СТ", "💬 ТТТЬ", "💰  С"]))
    async def placeholder(message: types.Message):
        if is_admin(message.from_user.id, admin_ids):
            await message.answer("ункция в разработке.")
