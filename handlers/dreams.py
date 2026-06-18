import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import main_menu, menu_button, cancel_button
from database import save_dream, get_user_dreams, get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, update_last_active, get_user_gender
from utils.notifications import get_subscription_button
from utils.calculations import get_zodiac_sign

router = Router()

class DreamStates(StatesGroup):
    waiting_dream_text = State()

@router.message(F.text == "🌙 ТОЛКОВАНИЕ СНОВ")
async def dream_menu(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        return
    await message.answer(
        "🌙 <b>Толкование снов</b>\n\n"
        "Опишите ваш сон кратко (2-3 предложения), и я дам его толкование.\n"
        "Для бесплатных пользователей – короткий ответ с основной идеей.\n"
        "По подписке – полный разбор с учётом вашего числа судьбы и знака зодиака.\n\n"
        "Также вы можете посмотреть свои предыдущие сны.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Рассказать сон", callback_data="dream_new")],
            [InlineKeyboardButton(text="📖 Мои сны", callback_data="dream_history")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
    )

@router.callback_query(F.data == "dream_new")
async def dream_new(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    await callback.message.answer(
        "Напишите ваш сон (не более 500 символов):",
        reply_markup=cancel_button()
    )
    await state.set_state(DreamStates.waiting_dream_text)
    await callback.answer()

@router.message(DreamStates.waiting_dream_text)
async def dream_process(message: types.Message, state: FSMContext):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        await state.clear()
        return
    user_id = message.from_user.id
    dream_text = message.text.strip()
    if len(dream_text) > 500:
        await message.answer("Слишком длинный сон. Сократите до 500 символов.", reply_markup=cancel_button())
        return
    if len(dream_text) < 5:
        await message.answer("Слишком коротко. Опишите сон подробнее.", reply_markup=cancel_button())
        return

    is_subscriber = get_user_subscription_status(user_id)
    gender = get_user_gender(user_id)
    status_msg = await message.answer("🌙 Аркадий Викторович толкует ваш сон...")

    # Получаем число судьбы и знак зодиака
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT destiny_number, birth_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    destiny = row[0] if row and row[0] else "?"
    zodiac = "неизвестен"
    if row and row[1]:
        zodiac = get_zodiac_sign(row[1])

    if is_subscriber:
        prompt = (
            f"Человек с числом судьбы {destiny} и знаком зодиака {zodiac} увидел сон: {dream_text}. "
            "Дай развёрнутое толкование (8-10 предложений) с практическими советами, учти его число и знак. "
            "Структурируй ответ: ключевые символы, связь с текущей ситуацией, задание на день. "
            "Будь тёплым и мудрым. Используй HTML-форматирование."
        )
        interpretation = await get_yandex_gpt_response(prompt, user_id, function_name="dream_interpretation", gender=gender)
        reply_markup = menu_button
    else:
        prompt = (
            f"Человек увидел сон: {dream_text}. "
            "Дай краткое толкование (4-5 предложений), которое затронет его глубокие переживания. "
            "В конце добавь фразу: «Полное толкование с практическими рекомендациями – по подписке». "
            "Используй HTML-форматирование."
        )
        interpretation = await get_yandex_gpt_response(prompt, user_id, function_name="dream_interpretation", gender=gender)
        reply_markup = get_subscription_button()

    await status_msg.delete()
    # Сохраняем в БД
    save_dream(user_id, dream_text, interpretation)
    update_last_active(user_id)
    await message.answer(
        f"🌙 <b>Толкование вашего сна:</b>\n\n{interpretation}",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await state.clear()

@router.callback_query(F.data == "dream_history")
async def dream_history(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    dreams = get_user_dreams(user_id, limit=5)
    if not dreams:
        await callback.message.answer("Вы ещё не записывали сны. Расскажите свой первый сон!", reply_markup=menu_button)
        await callback.answer()
        return
    text = "📖 <b>Ваши последние сны:</b>\n\n"
    for i, (dream, interp, date) in enumerate(dreams, 1):
        text += f"{i}. 🗓️ {date[:10]}\n"
        text += f"📝 Сон: {dream[:100]}...\n"
        text += f"🔮 Толкование: {interp[:150]}...\n\n"
    await callback.message.answer(text, parse_mode="HTML", reply_markup=menu_button)
    await callback.answer()