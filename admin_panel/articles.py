from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import admin_menu, cancel_button
from database import (
    get_connection,
    get_sexology_articles,
    update_article_status,
    delete_sexology_article,
    add_sexology_article,
    admin_log
)
from utils import is_admin
from yandex_gpt import get_yandex_gpt_response
from settings import SEXOLOGY_TOPICS
import random
import datetime

def register_articles_handlers(dp, bot, admin_ids):

    @dp.message(F.text == "📰 СТАТЬИ СЕКСОЛОГИИ")
    async def articles_admin_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Список статей", callback_data="admin_articles_list")],
            [InlineKeyboardButton(text="➕ Сгенерировать новую", callback_data="admin_articles_generate")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
        await message.answer("📰 *Управление статьями сексологии*", parse_mode="Markdown", reply_markup=kb)

    @dp.callback_query(F.data == "admin_articles_list")
    async def admin_articles_list(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        articles = get_sexology_articles(limit=50)
        if not articles:
            await callback.message.edit_text("Нет статей.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]]))
            await callback.answer()
            return
        for article in articles:
            status_emoji = "✅" if article['status'] == "published" else "⏳"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"✅ Опубликовать", callback_data=f"article_publish_{article['id']}") if article['status'] != "published" else None],
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"article_delete_{article['id']}")],
                [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"article_regenerate_{article['id']}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_articles_back")]
            ])
            # Убираем None
            kb.inline_keyboard = [row for row in kb.inline_keyboard if row[0] is not None]
            text = f"{status_emoji} *{article['title']}*\n{article['created_at'][:10]}\n\n{article['content'][:200]}..."
            await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data.startswith("article_publish_"))
    async def article_publish(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        article_id = int(callback.data.split("_")[-1])
        update_article_status(article_id, "published")
        admin_log(callback.from_user.id, "article_publish", f"article_id={article_id}")
        await callback.message.answer(f"✅ Статья опубликована.")
        # Отправляем уведомление всем пользователям
        await send_article_notification(bot, article_id)
        await callback.answer()

    @dp.callback_query(F.data.startswith("article_delete_"))
    async def article_delete(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        article_id = int(callback.data.split("_")[-1])
        delete_sexology_article(article_id)
        admin_log(callback.from_user.id, "article_delete", f"article_id={article_id}")
        await callback.message.answer("🗑 Статья удалена.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("article_regenerate_"))
    async def article_regenerate(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        article_id = int(callback.data.split("_")[-1])
        # Получаем старую статью
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT topic FROM sexology_articles WHERE id=?", (article_id,))
        row = cursor.fetchone()
        conn.close()
        topic = row[0] if row and row[0] else random.choice(SEXOLOGY_TOPICS)
        # Генерируем новую статью
        prompt = f"Напиши короткую полезную статью (5-7 предложений) на тему '{topic}'. Используй стиль Аркадия Викторовича: тепло, профессионально, без сложных терминов. Добавь интригу в конце."
        new_content = await get_yandex_gpt_response(prompt, callback.from_user.id)
        # Обновляем
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sexology_articles SET content = ?, created_at = ? WHERE id = ?",
                       (new_content, datetime.datetime.now().isoformat(), article_id))
        conn.commit()
        conn.close()
        admin_log(callback.from_user.id, "article_regenerate", f"article_id={article_id}")
        await callback.message.answer("🔄 Статья перегенерирована. Проверьте и опубликуйте.")
        await callback.answer()

    @dp.callback_query(F.data == "admin_articles_generate")
    async def admin_articles_generate(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        # Генерируем одну новую статью
        topic = random.choice(SEXOLOGY_TOPICS)
        prompt = f"Напиши короткую полезную статью (5-7 предложений) на тему '{topic}'. Используй стиль Аркадия Викторовича: тепло, профессионально, без сложных терминов. Добавь интригу в конце."
        content = await get_yandex_gpt_response(prompt, callback.from_user.id)
        # Сохраняем со статусом pending
        add_sexology_article(topic, content, topic, "pending")
        admin_log(callback.from_user.id, "article_generate", f"topic={topic}")
        await callback.message.answer("✅ Новая статья сгенерирована и добавлена в список на модерацию.")
        await callback.answer()

    @dp.callback_query(F.data == "admin_articles_back")
    async def admin_articles_back(callback: types.CallbackQuery):
        await articles_admin_menu(callback.message)
        await callback.answer()

async def send_article_notification(bot, article_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM sexology_articles WHERE id=?", (article_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return
    title = row[0]
    # Отправляем всем пользователям (кроме заблокированных)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_sleeping = 0")
    users = cursor.fetchall()
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Читать статью", url=f"https://t.me/NumerologArkadiy_bot?start=article_{article_id}")]
    ])
    for (user_id,) in users:
        try:
            await bot.send_message(
                user_id,
                f"📚 *Новая статья в разделе «Сексология»*\n\n{title}\n\nНажмите на кнопку, чтобы прочитать.",
                parse_mode="Markdown",
                reply_markup=kb
            )
        except:
            pass