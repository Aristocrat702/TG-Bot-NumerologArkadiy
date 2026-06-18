import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import sexology_submenu, menu_button, cancel_button
from database import (
    get_connection,
    get_sexology_free_queries_today,
    increment_sexology_free_query,
    get_sexology_articles,
    get_bot_config,
    update_user
)
from yandex_gpt import get_yandex_gpt_response
from utils import get_user_subscription_status, update_last_active

router = Router()

class SexologyStates(StatesGroup):
    waiting_question = State()

@router.message(F.text == "🧠 СЕКСОЛОГИЯ")
async def sexology_menu(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        return
    await message.answer(
        "🧠 *Сексология*\n\n"
        "Здесь вы можете задать вопрос эксперту (3 бесплатных в день) и читать полезные статьи об интимной жизни.\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=sexology_submenu
    )

@router.callback_query(F.data == "sexology_ask")
async def sexology_ask(callback: types.CallbackQuery, state: FSMContext):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    user_id = callback.from_user.id
    is_subscriber = get_user_subscription_status(user_id)
    if is_subscriber:
        await callback.message.answer(
            "Напишите ваш вопрос по сексологии. Я отвечу максимально честно и деликатно.",
            reply_markup=cancel_button()
        )
        await state.set_state(SexologyStates.waiting_question)
        await callback.answer()
        return
    limit = int(get_bot_config("sexology_free_queries_limit", "3"))
    used = get_sexology_free_queries_today(user_id)
    remaining = limit - used
    if remaining > 0:
        await callback.message.answer(
            f"У вас осталось *{remaining}* бесплатных вопросов по сексологии на сегодня.\n\n"
            "Напишите ваш вопрос, я дам короткий ответ. Полная консультация – по подписке.",
            parse_mode="Markdown",
            reply_markup=cancel_button()
        )
        await state.set_state(SexologyStates.waiting_question)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить подписку", callback_data="buy_subscription")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        await callback.message.answer(
            "❌ Вы исчерпали лимит бесплатных вопросов по сексологии на сегодня.\n"
            "Оформите подписку, чтобы задавать неограниченное количество вопросов.",
            reply_markup=kb
        )
    await callback.answer()

@router.message(SexologyStates.waiting_question)
async def sexology_question_handler(message: types.Message, state: FSMContext):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        await state.clear()
        return
    user_id = message.from_user.id
    is_subscriber = get_user_subscription_status(user_id)
    question = message.text
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT destiny_number, name FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    destiny = row[0] if row else "?"
    name = row[1] if row else "друг"
    status_msg = await message.answer("🧠 Аркадий Викторович размышляет над вашим вопросом...")
    if is_subscriber:
        prompt = f"Человек с числом судьбы {destiny} по имени {name} спрашивает о сексологии: {question}. Ответь развёрнуто (8-10 предложений) как психолог и сексолог, дай практические советы, будь деликатен. Учти число судьбы, если это уместно."
        response = await get_yandex_gpt_response(prompt, user_id, function_name="sexology")
        await status_msg.delete()
        await message.answer(response, parse_mode=None, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="sexology_ask")]
        ]))
        await state.clear()
        return
    limit = int(get_bot_config("sexology_free_queries_limit", "3"))
    used = get_sexology_free_queries_today(user_id)
    remaining = limit - used
    if remaining <= 0:
        await status_msg.delete()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить подписку", callback_data="buy_subscription")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        await message.answer("Лимит бесплатных вопросов исчерпан. Оформите подписку.", reply_markup=kb)
        await state.clear()
        return
    prompt = f"Человек с числом судьбы {destiny} по имени {name} спрашивает о сексологии: {question}. Дай короткий, но цепляющий ответ (3-4 предложения), оставь интригу. В конце добавь фразу: «Полная консультация и практические рекомендации – по подписке»."
    short_response = await get_yandex_gpt_response(prompt, user_id, function_name="sexology")
    increment_sexology_free_query(user_id)
    await status_msg.delete()
    await message.answer(
        f"🧠 {short_response}\n\nУ вас осталось *{remaining-1}* бесплатных вопросов по сексологии на сегодня.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="sexology_ask")]
        ])
    )
    await state.clear()

@router.callback_query(F.data == "sexology_articles")
async def sexology_articles_list(callback: types.CallbackQuery):
    if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await callback.message.answer("Доступно только в личном чате.")
        await callback.answer()
        return
    articles = get_sexology_articles(status="published", limit=50)
    if not articles:
        await callback.message.answer(
            "📚 Пока нет статей. Загляните позже – они скоро появятся!",
            reply_markup=menu_button
        )
        await callback.answer()
        return
    text = "📚 *Статьи по сексологии*\n\n"
    for article in articles:
        # Убрана дата
        text += f"• [{article['title']}](https://t.me/NumerologArkadiy_bot?start=article_sexology_{article['id']})\n"
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=menu_button)
    await callback.answer()

@router.message(F.text.startswith("/start article_sexology_"))
@router.message(F.text.startswith("/start article_psychology_"))
async def article_deeplink(message: types.Message):
    # Обработка deep link для статей (если пользователь ввел вручную)
    # Но основной обработчик в start.py
    pass