from aiogram import Router, types, F
from aiogram.enums import ChatType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import sexology_submenu, menu_button
from database import get_sexology_articles
from utils import update_last_active

router = Router()

@router.message(F.text == "🧠 СЕКСОЛОГИЯ")
async def sexology_menu(message: types.Message):
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Доступно только в личном чате.")
        return
    await message.answer(
        "🧠 *Сексология*\n\n"
        "Здесь вы можете читать полезные статьи об интимной жизни, отношениях и психологии секса.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=sexology_submenu
    )

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
        text += f"• <a href='https://t.me/NumerologArkadiy_bot?start=article_sexology_{article['id']}'>{article['title']}</a>\n"
    await callback.message.answer(text, parse_mode="HTML", reply_markup=menu_button)
    await callback.answer()
    update_last_active(callback.from_user.id)