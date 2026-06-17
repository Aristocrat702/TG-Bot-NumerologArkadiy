import datetime
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from keyboards import astro_submenu, main_menu, menu_button
from database import get_connection
from yandex_gpt import get_yandex_gpt_response
from utils import update_last_active, get_zodiac_sign, get_user_subscription_status
from utils.notifications import get_subscription_button

router = Router()

class AstroStates(StatesGroup):
    waiting_partner_birth = State()

def register_astro_handlers(dp: Dispatcher, bot: Bot, admin_ids: list):

    @dp.message(F.text == "🌟 АСТРОЛОГИЯ")
    async def astro_menu(message: types.Message):
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.answer("Эта функция доступна только в личном чате.")
            return
        await message.answer("🌟 *Астрологический раздел*\n\nВыберите, что вас интересует:", parse_mode="Markdown", reply_markup=astro_submenu)

    # ---------- НАТАЛЬНАЯ КАРТА (с монетизацией) ----------
    @dp.callback_query(F.data == "astro_natal")
    async def natal_chart(callback: types.CallbackQuery):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Доступно только в личном чате.")
            await callback.answer()
            return
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)
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

        status_msg = await callback.message.answer("🌌 Аркадий Викторович строит вашу натальную карту...")
        if is_subscriber:
            prompt = f"Составь описание натальной карты для человека, родившегося {birth_date} в {birth_time} в {birth_place}. Укажи основные планеты, дома, аспекты. Дай развёрнутый, содержательный прогноз (8-10 предложений)."
            response = await get_yandex_gpt_response(prompt, user_id)
            reply_markup = menu_button
        else:
            prompt = f"Дай очень краткое описание (2-3 предложения) того, что можно узнать из натальной карты человека, родившегося {birth_date}. Добавь интригу и фразу: «Полная натальная карта с планетами и аспектами – по подписке»."
            response = await get_yandex_gpt_response(prompt, user_id)
            reply_markup = get_subscription_button()
        await status_msg.delete()
        await callback.message.answer(f"🌌 *Ваша натальная карта*\n\n{response}", parse_mode="Markdown", reply_markup=reply_markup)
        update_last_active(user_id)
        await callback.answer()

    # ---------- ТРАНЗИТЫ (с монетизацией) ----------
    @dp.callback_query(F.data == "astro_transits")
    async def transits(callback: types.CallbackQuery):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Доступно только в личном чате.")
            await callback.answer()
            return
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)
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

        status_msg = await callback.message.answer("🔄 Аркадий Викторович анализирует транзиты...")
        if is_subscriber:
            prompt = f"Составь прогноз транзитов для человека со знаком {zodiac} на ближайший месяц. Укажи благоприятные и неблагоприятные периоды, дай развёрнутый совет (5-7 предложений)."
            response = await get_yandex_gpt_response(prompt, user_id)
            reply_markup = menu_button
        else:
            prompt = f"Дай короткий тизер транзитов (2-3 предложения) для человека со знаком {zodiac} на ближайший месяц. Добавь интригу и фразу: «Полный прогноз транзитов с датами – по подписке»."
            response = await get_yandex_gpt_response(prompt, user_id)
            reply_markup = get_subscription_button()
        await status_msg.delete()
        await callback.message.answer(f"🔄 *Транзиты на месяц*\n\n{response}", parse_mode="Markdown", reply_markup=reply_markup)
        update_last_active(user_id)
        await callback.answer()

    # ---------- СОЛЯР (с монетизацией) ----------
    @dp.callback_query(F.data == "astro_solar")
    async def solar(callback: types.CallbackQuery):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Доступно только в личном чате.")
            await callback.answer()
            return
        user_id = callback.from_user.id
        is_subscriber = get_user_subscription_status(user_id)
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

        status_msg = await callback.message.answer("☀️ Аркадий Викторович рассчитывает соляр...")
        if is_subscriber:
            prompt = f"Составь прогноз соляра для человека со знаком {zodiac} на предстоящий год. Укажи ключевые события, периоды роста и возможные трудности. Дай развёрнутый ответ (7-10 предложений)."
            response = await get_yandex_gpt_response(prompt, user_id)
            reply_markup = menu_button
        else:
            prompt = f"Дай короткий тизер соляра (2-3 предложения) для человека со знаком {zodiac} на предстоящий год. Добавь интригу и фразу: «Полный прогноз соляра на год – по подписке»."
            response = await get_yandex_gpt_response(prompt, user_id)
            reply_markup = get_subscription_button()
        await status_msg.delete()
        await callback.message.answer(f"☀️ *Ваш соляр на год*\n\n{response}", parse_mode="Markdown", reply_markup=reply_markup)
        update_last_active(user_id)
        await callback.answer()

    # ---------- СОВМЕСТИМОСТЬ ПО ЗНАКАМ (остаётся бесплатной) ----------
    @dp.callback_query(F.data == "astro_compatibility")
    async def astro_compatibility(callback: types.CallbackQuery, state: FSMContext):
        if callback.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            await callback.message.answer("Доступно только в личном чате.")
            await callback.answer()
            return
        await callback.message.answer("♊ *Совместимость по знакам зодиака*\n\nВведите дату рождения партнёра в формате ДД.ММ.ГГГГ:", reply_markup=menu_button)
        await state.set_state(AstroStates.waiting_partner_birth)
        await callback.answer()

    @dp.message(AstroStates.waiting_partner_birth)
    async def process_partner_birth_for_astro(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        partner_text = message.text.strip()
        try:
            day, month, year = map(int, partner_text.split('.'))
            partner_birth = f"{day:02d}.{month:02d}.{year:04d}"
            partner_zodiac = get_zodiac_sign(partner_birth)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT birth_date FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            if not row or not row[0]:
                await message.answer("Сначала укажите свою дату рождения в профиле.", reply_markup=menu_button)
                await state.clear()
                return
            my_birth = row[0]
            my_zodiac = get_zodiac_sign(my_birth)
            prompt = f"Опиши совместимость между знаками {my_zodiac} и {partner_zodiac}. Дай краткое описание (5-7 предложений) с советами."
            status_msg = await message.answer("♊ Анализирую совместимость...")
            response = await get_yandex_gpt_response(prompt, user_id)
            await status_msg.delete()
            await message.answer(f"♊ *Совместимость знаков*\n\n{response}", parse_mode="Markdown", reply_markup=menu_button)
        except:
            await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ", reply_markup=menu_button)
        await state.clear()