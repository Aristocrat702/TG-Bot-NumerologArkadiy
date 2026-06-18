from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import admin_menu, cancel_button
from database import (
    get_connection,
    add_sexology_article,
    get_sexology_articles,
    update_article_status,
    delete_sexology_article,
    add_psychology_article,
    get_psychology_articles,
    update_psychology_article_status,
    delete_psychology_article,
    admin_log
)
from utils import is_admin
from yandex_gpt import get_yandex_gpt_response
from settings import SEXOLOGY_TOPICS, PSYCHOLOGY_TOPICS
import random
import datetime

class ArticleStates(StatesGroup):
    waiting_category = State()
    waiting_title = State()
    waiting_content = State()

def register_articles_handlers(dp, bot, admin_ids):

    # ===== ГЛАВНОЕ МЕНЮ СТАТЕЙ =====
    @dp.message(F.text == "📰 СТАТЬИ")
    async def articles_main_menu(message: types.Message):
        if not is_admin(message.from_user.id, admin_ids):
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 ПСИХОЛОГИЯ", callback_data="articles_category_psychology")],
            [InlineKeyboardButton(text="🧠 СЕКСОЛОГИЯ", callback_data="articles_category_sexology")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
        await message.answer("📰 *Управление статьями*\n\nВыберите категорию:", parse_mode="Markdown", reply_markup=kb)

    # ===== ВЫБОР КАТЕГОРИИ =====
    @dp.callback_query(F.data.startswith("articles_category_"))
    async def articles_category_menu(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        category = callback.data.split("_")[-1]  # psychology или sexology
        await callback.message.edit_text(
            f"📂 *Категория: {category.capitalize()}*\n\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Список статей", callback_data=f"articles_list_{category}")],
                [InlineKeyboardButton(text="➕ Сгенерировать новую", callback_data=f"articles_generate_{category}")],
                [InlineKeyboardButton(text="📝 Добавить вручную", callback_data=f"articles_add_manual_{category}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="articles_back_main")]
            ])
        )
        await callback.answer()

    # ===== СПИСОК СТАТЕЙ =====
    @dp.callback_query(F.data.startswith("articles_list_"))
    async def articles_list(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        category = callback.data.split("_")[-1]
        if category == "sexology":
            articles = get_sexology_articles(limit=50)
            update_func = update_article_status
            delete_func = delete_sexology_article
        else:
            articles = get_psychology_articles(limit=50)
            update_func = update_psychology_article_status
            delete_func = delete_psychology_article
        if not articles:
            await callback.message.edit_text(f"Нет статей в категории {category}.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=f"articles_category_{category}")]]))
            await callback.answer()
            return
        for article in articles:
            status_emoji = "✅" if article['status'] == "published" else "⏳"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"✅ Опубликовать", callback_data=f"article_publish_{category}_{article['id']}") if article['status'] != "published" else None],
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"article_delete_{category}_{article['id']}")],
                [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"article_regenerate_{category}_{article['id']}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"articles_category_{category}")]
            ])
            kb.inline_keyboard = [row for row in kb.inline_keyboard if row[0] is not None]
            text = f"{status_emoji} *{article['title']}*\n{article['created_at'][:10]}\n\n{article['content'][:200]}..."
            await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()

    # ===== ГЕНЕРАЦИЯ СТАТЬИ =====
    @dp.callback_query(F.data.startswith("articles_generate_"))
    async def articles_generate(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        category = callback.data.split("_")[-1]
        topics = SEXOLOGY_TOPICS if category == "sexology" else PSYCHOLOGY_TOPICS
        topic = random.choice(topics)
        prompt = f"Напиши развёрнутую полезную статью (10-12 предложений) на тему '{topic}'. Она должна быть интересной, содержательной, с практическими советами. Используй стиль Аркадия Викторовича: тепло, профессионально, без сложных терминов. Добавь интригу в конце."
        content = await get_yandex_gpt_response(prompt, callback.from_user.id, function_name="article_generation")
        if category == "sexology":
            add_sexology_article(topic, content, topic, "pending")
        else:
            add_psychology_article(topic, content, topic, "pending")
        admin_log(callback.from_user.id, "article_generate", f"category={category}, topic={topic}")
        await callback.message.edit_text(f"✅ Новая статья в категории {category} сгенерирована и добавлена в список на модерацию.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=f"articles_category_{category}")]]))
        await callback.answer()

    # ===== ДОБАВЛЕНИЕ ВРУЧНУЮ =====
    @dp.callback_query(F.data.startswith("articles_add_manual_"))
    async def articles_add_manual_start(callback: types.CallbackQuery, state: FSMContext):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        category = callback.data.split("_")[-1]
        await state.update_data(category=category)
        await callback.message.answer("Введите заголовок статьи:", reply_markup=cancel_button())
        await state.set_state(ArticleStates.waiting_title)
        await callback.answer()

    @dp.message(ArticleStates.waiting_title)
    async def article_manual_title(message: types.Message, state: FSMContext):
        title = message.text.strip()
        await state.update_data(title=title)
        await message.answer("Введите текст статьи (10-12 предложений):", reply_markup=cancel_button())
        await state.set_state(ArticleStates.waiting_content)

    @dp.message(ArticleStates.waiting_content)
    async def article_manual_content(message: types.Message, state: FSMContext):
        content = message.text.strip()
        data = await state.get_data()
        category = data.get("category")
        title = data.get("title")
        if category == "sexology":
            add_sexology_article(title, content, "", "pending")
        else:
            add_psychology_article(title, content, "", "pending")
        admin_log(message.from_user.id, "article_manual_add", f"category={category}, title={title}")
        await message.answer(f"✅ Статья «{title}» добавлена в категорию {category} и ожидает публикации.", reply_markup=admin_menu)
        await state.clear()

    # ===== ОПУБЛИКОВАТЬ, УДАЛИТЬ, ПЕРЕГЕНЕРИРОВАТЬ =====
    @dp.callback_query(F.data.startswith("article_publish_"))
    async def article_publish(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        parts = callback.data.split("_")
        category = parts[2]
        article_id = int(parts[3])
        if category == "sexology":
            update_article_status(article_id, "published")
        else:
            update_psychology_article_status(article_id, "published")
        admin_log(callback.from_user.id, "article_publish", f"category={category}, id={article_id}")
        await callback.message.answer(f"✅ Статья опубликована в категории {category}.")
        # Отправляем уведомление
        await send_article_notification(bot, article_id, category)
        await callback.answer()

    @dp.callback_query(F.data.startswith("article_delete_"))
    async def article_delete(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        parts = callback.data.split("_")
        category = parts[2]
        article_id = int(parts[3])
        if category == "sexology":
            delete_sexology_article(article_id)
        else:
            delete_psychology_article(article_id)
        admin_log(callback.from_user.id, "article_delete", f"category={category}, id={article_id}")
        await callback.message.answer(f"🗑 Статья удалена из категории {category}.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("article_regenerate_"))
    async def article_regenerate(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id, admin_ids):
            await callback.answer("Нет доступа.")
            return
        parts = callback.data.split("_")
        category = parts[2]
        article_id = int(parts[3])
        # Получаем старую тему
        conn = get_connection()
        cursor = conn.cursor()
        if category == "sexology":
            cursor.execute("SELECT topic FROM sexology_articles WHERE id=?", (article_id,))
        else:
            cursor.execute("SELECT topic FROM psychology_articles WHERE id=?", (article_id,))
        row = cursor.fetchone()
        conn.close()
        topic = row[0] if row and row[0] else random.choice(SEXOLOGY_TOPICS if category == "sexology" else PSYCHOLOGY_TOPICS)
        prompt = f"Напиши развёрнутую полезную статью (10-12 предложений) на тему '{topic}'. Она должна быть интересной, содержательной, с практическими советами. Используй стиль Аркадия Викторовича: тепло, профессионально, без сложных терминов. Добавь интригу в конце."
        new_content = await get_yandex_gpt_response(prompt, callback.from_user.id, function_name="article_generation")
        conn = get_connection()
        cursor = conn.cursor()
        if category == "sexology":
            cursor.execute("UPDATE sexology_articles SET content = ?, created_at = ? WHERE id = ?",
                           (new_content, datetime.datetime.now().isoformat(), article_id))
        else:
            cursor.execute("UPDATE psychology_articles SET content = ?, created_at = ? WHERE id = ?",
                           (new_content, datetime.datetime.now().isoformat(), article_id))
        conn.commit()
        conn.close()
        admin_log(callback.from_user.id, "article_regenerate", f"category={category}, id={article_id}")
        await callback.message.answer("🔄 Статья перегенерирована. Проверьте и опубликуйте.")
        await callback.answer()

    # ===== НАЗАД =====
    @dp.callback_query(F.data == "articles_back_main")
    async def articles_back_main(callback: types.CallbackQuery):
        await articles_main_menu(callback.message)
        await callback.answer()

    # ===== ОТПРАВКА УВЕДОМЛЕНИЯ =====
    async def send_article_notification(bot, article_id: int, category: str):
        conn = get_connection()
        cursor = conn.cursor()
        if category == "sexology":
            cursor.execute("SELECT title FROM sexology_articles WHERE id=?", (article_id,))
        else:
            cursor.execute("SELECT title FROM psychology_articles WHERE id=?", (article_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return
        title = row[0]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Читать статью", url=f"https://t.me/NumerologArkadiy_bot?start=article_{category}_{article_id}")]
        ])
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE is_sleeping = 0")
        users = cursor.fetchall()
        conn.close()
        category_name = "Сексология" if category == "sexology" else "Психология"
        for (user_id,) in users:
            try:
                await bot.send_message(
                    user_id,
                    f"📚 *Новая статья в разделе «{category_name}»*\n\n{title}\n\nНажмите на кнопку, чтобы прочитать.",
                    parse_mode="Markdown",
                    reply_markup=kb
                )
            except:
                pass