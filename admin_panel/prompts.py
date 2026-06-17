from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import admin_menu, cancel_button
from database import get_prompts_for_function, set_prompts_for_function, get_all_function_names
from utils import is_admin, admin_log
from yandex_gpt import get_yandex_gpt_response

class PromptStates(StatesGroup):
    waiting_function = State()
    waiting_system_prompt = State()
    waiting_free_prompt = State()
    waiting_paid_prompt = State()
    waiting_test_prompt = State()

def register_prompts_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "🔧 УПРАВЛЕНИЕ ПРОМПТАМИ")
    async def prompts_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Список функций", callback_data="prompts_list")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
        await message.answer("🔧 *Управление промптами*\n\nВыберите действие:", parse_mode="Markdown", reply_markup=kb)

    @dp.callback_query(F.data == "prompts_list")
    async def prompts_list(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        function_names = get_all_function_names()
        if not function_names:
            await callback.message.edit_text("Нет функций с промптами.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]]))
            await callback.answer()
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"prompt_edit_{name}")] for name in function_names
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]])
        await callback.message.edit_text("Выберите функцию для редактирования промптов:", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data.startswith("prompt_edit_"))
    async def prompt_edit(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        function_name = callback.data.split("_")[-1]
        prompts = get_prompts_for_function(function_name)
        if not prompts:
            await callback.message.answer("Промпты для этой функции не найдены.")
            await callback.answer()
            return
        await state.update_data(function_name=function_name)
        text = f"📝 *{function_name}*\n\n"
        text += f"*Системный:*\n{prompts['system']}\n\n"
        text += f"*Бесплатный:*\n{prompts['free']}\n\n"
        text += f"*Платный:*\n{prompts['paid']}\n\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="prompt_edit_start")],
            [InlineKeyboardButton(text="🧪 Тестовый запрос", callback_data="prompt_test")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="prompts_list")]
        ])
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data == "prompt_edit_start")
    async def prompt_edit_start(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        await callback.message.answer("Введите новый системный промпт (или отправьте '-' чтобы оставить без изменений):", reply_markup=cancel_button())
        await state.set_state(PromptStates.waiting_system_prompt)
        await callback.answer()

    @dp.message(PromptStates.waiting_system_prompt)
    async def prompt_edit_system(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        data = await state.get_data()
        function_name = data.get("function_name")
        prompts = get_prompts_for_function(function_name)
        new_system = message.text.strip()
        if new_system == "-":
            new_system = prompts["system"]
        await state.update_data(system_prompt=new_system)
        await message.answer("Введите новый бесплатный промпт (или '-' для пропуска):", reply_markup=cancel_button())
        await state.set_state(PromptStates.waiting_free_prompt)

    @dp.message(PromptStates.waiting_free_prompt)
    async def prompt_edit_free(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        data = await state.get_data()
        function_name = data.get("function_name")
        prompts = get_prompts_for_function(function_name)
        new_free = message.text.strip()
        if new_free == "-":
            new_free = prompts["free"]
        await state.update_data(free_prompt=new_free)
        await message.answer("Введите новый платный промпт (или '-' для пропуска):", reply_markup=cancel_button())
        await state.set_state(PromptStates.waiting_paid_prompt)

    @dp.message(PromptStates.waiting_paid_prompt)
    async def prompt_edit_paid(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        data = await state.get_data()
        function_name = data.get("function_name")
        prompts = get_prompts_for_function(function_name)
        new_paid = message.text.strip()
        if new_paid == "-":
            new_paid = prompts["paid"]
        set_prompts_for_function(function_name, data.get("system_prompt"), data.get("free_prompt"), new_paid)
        admin_log(message.from_user.id, "edit_prompts", f"function={function_name}")
        await message.answer(f"✅ Промпты для функции {function_name} обновлены.", reply_markup=admin_menu)
        await state.clear()

    @dp.callback_query(F.data == "prompt_test")
    async def prompt_test_start(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        await callback.message.answer("Введите текст для тестового запроса (будет отправлен с текущими промптами):", reply_markup=cancel_button())
        await state.set_state(PromptStates.waiting_test_prompt)
        await callback.answer()

    @dp.message(PromptStates.waiting_test_prompt)
    async def prompt_test_execute(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id, admin_ids):
            return
        data = await state.get_data()
        function_name = data.get("function_name")
        if not function_name:
            await message.answer("Ошибка: не указана функция.")
            await state.clear()
            return
        test_text = message.text.strip()
        response = await get_yandex_gpt_response(test_text, message.from_user.id, function_name)
        await message.answer(f"🧪 *Ответ на тестовый запрос:*\n\n{response}", parse_mode="Markdown")
        await state.clear()