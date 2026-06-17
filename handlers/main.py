from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards import main_menu, quick_topics_menu, menu_button
from database import get_user, get_subscription_status, get_cached_response, save_cache
from yandex_gpt import get_yandex_response
from utils import get_birth_number, get_zodiac_sign, admin_log
import datetime

router = Router()

@router.message(F.text == "🔮 МОЯ МАТРИЦА")
async def my_matrix(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or not user.get('birth_date'):
        await message.answer("Сначала укажите дату рождения через /start")
        return
    if not get_subscription_status(user_id):
        await message.answer("Эта функция доступна только по подписке. Купите подписку в профиле.", reply_markup=main_menu)
        return
    date = user['birth_date']
    # Проверяем кэш
    cached = get_cached_response(user_id, f"matrix_{date}")
    if cached:
        await message.answer(cached)
        return
    # Генерируем через YandexGPT
    prompt = f"Составь полную матрицу судьбы (22 аркана) для даты рождения {date}. Дай развёрнутую характеристику (10-15 предложений)."
    answer = await get_yandex_response(prompt)
    save_cache(user_id, f"matrix_{date}", answer)
    await message.answer(answer)

@router.message(F.text == "🔢 МОЁ ЧИСЛО")
async def my_number(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or not user.get('birth_number'):
        await message.answer("Сначала укажите дату рождения через /start")
        return
    number = user['birth_number']
    cached = get_cached_response(user_id, f"number_{number}")
    if cached:
        await message.answer(cached + "\nВыберите тему:", reply_markup=quick_topics_menu)
        return
    prompt = f"Дай краткую характеристику числа судьбы {number} (3-5 предложений)."
    answer = await get_yandex_response(prompt)
    save_cache(user_id, f"number_{number}", answer)
    await message.answer(answer + "\nВыберите тему:", reply_markup=quick_topics_menu)

@router.callback_query(F.data.startswith("topic_"))
async def topic_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user:
        await callback.answer("Ошибка", show_alert=True)
        return
    number = user.get('birth_number')
    if not number:
        await callback.answer("Укажите дату рождения", show_alert=True)
        return
    topic = callback.data.split("_")[1]
    prompt = f"Для числа {number} расскажи о {topic} (кратко, 3-5 предложений)."
    answer = await get_yandex_response(prompt)
    await callback.message.edit_text(answer, reply_markup=quick_topics_menu)
    await callback.answer()

@router.message(F.text == "❤️ СОВМЕСТИМОСТЬ")
async def compatibility_start(message: Message):
    await message.answer("Введите дату рождения партнёра в формате ДД.ММ.ГГГГ")

@router.message(lambda msg: msg.text and len(msg.text)==10 and msg.text[2]=='.' and msg.text[5]=='.' and msg.text)
async def process_partner_date(message: Message):
    user_id = message.from_user.id
    try:
        date_obj = datetime.datetime.strptime(message.text, "%d.%m.%Y").date()
        partner_number = get_birth_number(date_obj)
        user = get_user(user_id)
        if not user or not user.get('birth_number'):
            await message.answer("Сначала укажите свою дату рождения через /start")
            return
        my_number = user['birth_number']
        prompt = f"Оцени совместимость чисел {my_number} и {partner_number}. Дай 5-7 предложений."
        answer = await get_yandex_response(prompt)
        await message.answer(answer, reply_markup=main_menu)
    except ValueError:
        await message.answer("Неверный формат даты.")

@router.message(F.text == "🎁 КАРТА ДНЯ")
async def daily_card(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    date = datetime.date.today().isoformat()
    cached = get_cached_response(user_id, f"card_{date}")
    if cached:
        await message.answer(cached)
        return
    prompt = "Составь прогноз на сегодня (3-5 предложений) с психологической практикой."
    answer = await get_yandex_response(prompt)
    save_cache(user_id, f"card_{date}", answer)
    await message.answer(answer)

@router.message(F.text == "💬 ЗАДАТЬ ВОПРОС")
async def ask_question(message: Message):
    await message.answer("Напишите ваш вопрос. (до 5 вопросов в день бесплатно)")

@router.message(lambda msg: msg.text and not msg.text.startswith('/'))
async def handle_free_question(message: Message):
    # Здесь логика подсчёта вопросов и ответа
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or not user.get('birth_number'):
        await message.answer("Сначала укажите дату рождения через /start")
        return
    is_sub = get_subscription_status(user_id)
    if not is_sub:
        # Проверяем лимит 5 в день
        # Упрощённо: отвечаем коротко
        prompt = f"Ответь на вопрос пользователя кратко (1-2 предложения): {message.text}"
        answer = await get_yandex_response(prompt)
        await message.answer(answer + "\nПолный разбор – по подписке.")
    else:
        prompt = f"Ответь развёрнуто на вопрос пользователя с учётом его числа судьбы {user['birth_number']}: {message.text}"
        answer = await get_yandex_response(prompt)
        await message.answer(answer)