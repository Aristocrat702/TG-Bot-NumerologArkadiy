from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu
from database import get_connection
from utils import get_user_subscription_status, update_last_active
import datetime
import re

class AlarmStates(StatesGroup):
    waiting_time = State()

def register_alarm_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.callback_query(F.data == "alarm_menu")
    async def alarm_menu(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, alarm_time, is_active FROM alarms WHERE user_id=? AND is_active=1", (user_id,))
        alarms = cursor.fetchall()
        conn.close()
        text = "⏰ *Умный будильник*\n\n"
        if alarms:
            text += "Ваши активные будильники:\n"
            for a in alarms:
                text += f"• {a[1]}\n"
            text += "\n"
        else:
            text += "Активных будильников нет.\n\n"
        text += "Установите будильник командой `/alarm ЧЧ:ММ` (например, `/alarm 09:00`).\n"
        text += "В указанное время я пришлю вам мотивирующий совет, прогноз погоды (если указали город) и фазу луны."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Установить будильник", callback_data="set_alarm")],
            [InlineKeyboardButton(text="🔕 Отключить все", callback_data="disable_all_alarms")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data == "set_alarm")
    async def set_alarm_prompt(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("Напишите время в формате ЧЧ:ММ (например, 09:00).")
        await state.set_state(AlarmStates.waiting_time)
        await callback.answer()

    @dp.message(AlarmStates.waiting_time)
    async def process_alarm_time(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        time_str = message.text.strip()
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
            await message.answer("Неверный формат. Используйте ЧЧ:ММ, например 09:00.")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO alarms (user_id, alarm_time, created_at) VALUES (?, ?, ?)",
                       (user_id, time_str, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Будильник на {time_str} установлен! В это время я пришлю вам полезный совет.")
        await state.clear()

    @dp.callback_query(F.data == "disable_all_alarms")
    async def disable_all_alarms(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE alarms SET is_active=0 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        await callback.message.answer("Все будильники отключены.")
        await callback.answer()

    @dp.message(Command("alarm"))
    async def alarm_command(message: types.Message, state: FSMContext):
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("Использование: /alarm ЧЧ:ММ (например, /alarm 09:00)")
            return
        time_str = parts[1]
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
            await message.answer("Неверный формат.")
            return
        user_id = message.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO alarms (user_id, alarm_time, created_at) VALUES (?, ?, ?)",
                       (user_id, time_str, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Будильник на {time_str} установлен!")