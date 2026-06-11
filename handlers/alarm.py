from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu
from database import get_connection
import datetime

class AlarmStates(StatesGroup):
    waiting_hour = State()
    waiting_minute = State()

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
        text += "Выберите время, когда я пришлю вам мотивирующий совет, прогноз погоды и фазу луны."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕒 Установить будильник", callback_data="set_alarm_step1")],
            [InlineKeyboardButton(text="🔕 Отключить все", callback_data="disable_all_alarms")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data == "set_alarm_step1")
    async def set_alarm_hour(callback: types.CallbackQuery, state: FSMContext):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{h:02d}", callback_data=f"alarm_hour_{h}") for h in range(0, 24, 6)]
        ])
        await callback.message.answer("Выберите час:", reply_markup=kb)
        await state.set_state(AlarmStates.waiting_hour)
        await callback.answer()

    @dp.callback_query(AlarmStates.waiting_hour, F.data.startswith("alarm_hour_"))
    async def set_alarm_minute(callback: types.CallbackQuery, state: FSMContext):
        hour = int(callback.data.split("_")[-1])
        await state.update_data(hour=hour)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{m:02d}", callback_data=f"alarm_minute_{m}") for m in range(0, 60, 15)]
        ])
        await callback.message.answer(f"Выбрано {hour:02d} часов. Теперь выберите минуты:", reply_markup=kb)
        await state.set_state(AlarmStates.waiting_minute)
        await callback.answer()

    @dp.callback_query(AlarmStates.waiting_minute, F.data.startswith("alarm_minute_"))
    async def save_alarm(callback: types.CallbackQuery, state: FSMContext):
        minute = int(callback.data.split("_")[-1])
        data = await state.get_data()
        hour = data.get("hour")
        time_str = f"{hour:02d}:{minute:02d}"
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO alarms (user_id, alarm_time, created_at) VALUES (?, ?, ?)",
                       (user_id, time_str, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        await callback.message.answer(f"✅ Будильник на {time_str} установлен!")
        await state.clear()
        await callback.answer()

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
    async def alarm_command(message: types.Message):
        await message.answer("Используйте меню «Умный будильник» в профиле для установки времени.")