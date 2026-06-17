from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import admin_menu, cancel_button
from database import export_user_visits_csv, get_user_visits_stats
from utils import is_admin

class ActivityExportStates(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()

def register_activity_export_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "📤 ЭКСПОРТ АКТИВНОСТИ")
    async def activity_export_menu(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Все пользователи", callback_data="export_activity_all")],
            [InlineKeyboardButton(text="👤 Конкретный пользователь", callback_data="export_activity_user")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
        await message.answer("📤 *Экспорт активности*\n\nВыберите, что выгрузить:", parse_mode="Markdown", reply_markup=kb)

    @dp.callback_query(F.data == "export_activity_all")
    async def export_activity_all(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        days = 30  # по умолчанию
        csv_data = export_user_visits_csv(days=days)
        await callback.message.answer_document(
            types.BufferedInputFile(csv_data.encode('utf-8'), filename=f"activity_all_{days}days.csv"),
            caption=f"📊 Активность всех пользователей за {days} дней"
        )
        await callback.answer()

    @dp.callback_query(F.data == "export_activity_user")
    async def export_activity_user_start(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        await callback.message.answer("Введите user_id пользователя:", reply_markup=cancel_button())
        await state.set_state(ActivityExportStates.waiting_user_id)
        await callback.answer()

    @dp.message(ActivityExportStates.waiting_user_id)
    async def export_activity_user_id(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            user_id = int(message.text.strip())
            await state.update_data(user_id=user_id)
            await message.answer("Введите количество дней (например, 30):", reply_markup=cancel_button())
            await state.set_state(ActivityExportStates.waiting_days)
        except:
            await message.answer("Ошибка. Введите числовой ID.")

    @dp.message(ActivityExportStates.waiting_days)
    async def export_activity_days(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        try:
            days = int(message.text.strip())
            data = await state.get_data()
            user_id = data.get("user_id")
            csv_data = export_user_visits_csv(user_id=user_id, days=days)
            await message.answer_document(
                types.BufferedInputFile(csv_data.encode('utf-8'), filename=f"activity_{user_id}_{days}days.csv"),
                caption=f"📊 Активность пользователя {user_id} за {days} дней"
            )
        except:
            await message.answer("Ошибка. Введите целое число дней.")
        await state.clear()