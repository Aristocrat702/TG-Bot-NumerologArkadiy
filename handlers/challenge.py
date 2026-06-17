from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import challenge_menu, main_menu
from utils import start_challenge, complete_challenge_day, get_challenge_progress, add_xp

router = Router()  # <-- ОБЯЗАТЕЛЬНО

@router.callback_query(F.data == "start_challenge")
async def start_challenge_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    progress = get_challenge_progress(user_id)
    if progress and any(not comp for _, comp in progress):
        await callback.message.answer("У вас уже есть активный челлендж. Выполняйте задания каждый день.", reply_markup=challenge_menu)
        await callback.answer()
        return
    start_challenge(user_id)
    await callback.message.answer(
        "🔥 Вы начали челлендж «7 дней до силы»!\n"
        "Каждый день я буду давать небольшое задание. Выполняйте его и нажимайте «Выполнил».\n"
        "За успешное прохождение всех 7 дней вы получите +3 дня подписки.\n\n"
        "Задание дня 1: Скажите «нет» человеку, который вас напрягает (мысленно или вслух).\n"
        "Как выполните – нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнил день 1", callback_data="challenge_day_1")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("challenge_day_"))
async def complete_challenge_day_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    day = int(callback.data.split("_")[-1])
    completed = complete_challenge_day(user_id, day)
    if completed:
        await callback.message.answer("🎉 Поздравляю! Вы прошли весь челлендж и получили +3 дня подписки. Продолжайте изучать нумерологию!")
        add_xp(user_id, "challenge_completed")
    else:
        next_day = day + 1
        tasks = {
            2: "Сделайте спонтанный поступок (поменяйте маршрут, купите необычный продукт).",
            3: "Напишите себе письмо «Что я изменю через месяц».",
            4: "Сделайте зарядку 5 минут.",
            5: "Поблагодарите себя за что-то вслух.",
            6: "Отдайте ненужную вещь.",
            7: "Запланируйте конкретную цель на неделю."
        }
        if next_day <= 7:
            task_text = tasks.get(next_day, "Продолжайте челлендж!")
            await callback.message.answer(f"✅ День {day} выполнен!\n\nЗадание дня {next_day}: {task_text}\n\nНажмите «Выполнил», когда сделаете.",
                                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                               [InlineKeyboardButton(text=f"✅ Выполнил день {next_day}", callback_data=f"challenge_day_{next_day}")]
                                           ]))
    await callback.answer()

@router.callback_query(F.data == "challenge_progress")
async def show_challenge_progress(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    progress = get_challenge_progress(user_id)
    if not progress:
        await callback.message.answer("Вы ещё не начинали челлендж. Нажмите «Начать челлендж 7 дней» в профиле.", reply_markup=main_menu)
    else:
        text = "📊 Прогресс челленджа:\n"
        for day, completed in progress:
            status = "✅" if completed else "❌"
            text += f"День {day}: {status}\n"
        await callback.message.answer(text, reply_markup=challenge_menu)
    await callback.answer()