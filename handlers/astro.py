import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import astro_submenu, main_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import update_last_active, get_zodiac_sign

def register_astro_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "🌟 АСТРОЛОГИЯ")
    async def astro_menu(message: types.Message):
        await message.answer("🌟 *Астрологический раздел*\n\nВыберите, что вас интересует:", parse_mode="Markdown", reply_markup=astro_submenu)

    @dp.callback_query(F.data == "astro_natal")
    async def natal_chart(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date, birth_time, birth_place FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала укажите дату рождения в профиле (настройки).", reply_markup=main_menu)
            await callback.answer()
            return
        birth_date = row[0]
        birth_time = row[1] if row[1] else "неизвестно"
        birth_place = row[2] if row[2] else "не указано"
        prompt = f"Составь описание натальной карты для человека, родившегося {birth_date} в {birth_time} в {birth_place}. Укажи основные планеты, дома, аспекты. Дай краткий, но содержательный прогноз."
        status_msg = await callback.message.answer("🌌 Аркадий Викторович строит вашу натальную карту...")
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        await callback.message.answer(f"🌌 *Ваша натальная карта*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        update_last_active(user_id)
        await callback.answer()

    @dp.callback_query(F.data == "astro_transits")
    async def transits(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала укажите дату рождения в профиле.", reply_markup=main_menu)
            await callback.answer()
            return
        birth_date = row[0]
        zodiac = get_zodiac_sign(birth_date)
        prompt = f"Составь прогноз транзитов для человека со знаком {zodiac} на ближайший месяц. Укажи благоприятные и неблагоприятные периоды, дай совет."
        status_msg = await callback.message.answer("🔄 Аркадий Викторович анализирует транзиты...")
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        await callback.message.answer(f"🔄 *Транзиты на месяц*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        update_last_active(user_id)
        await callback.answer()

    @dp.callback_query(F.data == "astro_solar")
    async def solar(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT birth_date FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            await callback.message.answer("Сначала укажите дату рождения в профиле.", reply_markup=main_menu)
            await callback.answer()
            return
        birth_date = row[0]
        zodiac = get_zodiac_sign(birth_date)
        prompt = f"Составь прогноз соляра для человека со знаком {zodiac} на предстоящий год. Укажи ключевые события, периоды роста и возможные трудности."
        status_msg = await callback.message.answer("☀️ Аркадий Викторович рассчитывает соляр...")
        response = await get_yandex_gpt_response(prompt, user_id)
        await status_msg.delete()
        await callback.message.answer(f"☀️ *Ваш соляр на год*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        update_last_active(user_id)
        await callback.answer()

    @dp.callback_query(F.data == "astro_compatibility")
    async def astro_compatibility(callback: types.CallbackQuery):
        # Заглушка для совместимости по знакам (можно расширить)
        await callback.message.answer("♊ *Совместимость по знакам зодиака*\n\nВведите дату рождения партнёра в формате ДД.ММ.ГГГГ:", reply_markup=menu_button)
        # Здесь нужна FSM, но для простоты пока просто сообщение
        # В реальности лучше сделать отдельный обработчик, но мы оставим как есть
        await callback.answer()