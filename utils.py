import datetime
import glob
import os
import time
import asyncio
import aiohttp
import pytz
import hashlib
import random
from database import get_connection
from settings import LEVELS, XP_REWARDS, CRISIS_HELP_LINKS, LOGS_DIR
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
from yandex_gpt import get_yandex_gpt_response

# ---------- ОСНОВНЫЕ ФУНКЦИИ (БЫЛИ РАНЕЕ) ----------
def is_admin(user_id: int, admin_ids: list) -> bool:
    return user_id in admin_ids

def is_blacklisted(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM blacklist WHERE user_id=?", (user_id,))
    res = cursor.fetchone() is not None
    conn.close()
    return res

def add_to_blacklist(user_id: int, reason: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO blacklist (user_id, reason, blocked_at) VALUES (?, ?, ?)",
                   (user_id, reason, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    admin_log(0, "add_blacklist", f"user_id={user_id}, reason={reason}")

def remove_from_blacklist(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    admin_log(0, "remove_blacklist", f"user_id={user_id}")

def calculate_destiny_number(birth_date: str) -> int:
    s = birth_date.replace('.', '')
    total = sum(int(d) for d in s)
    while total > 9 and total not in (11, 22, 33):
        total = sum(int(d) for d in str(total))
    return total

def add_subscription_days(user_id: int, days: int, check_referral: bool = False, admin_id: int = 0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_end FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        end_date = datetime.datetime.fromisoformat(row[0])
        new_end = end_date + datetime.timedelta(days=days)
    else:
        new_end = datetime.datetime.now() + datetime.timedelta(days=days)
    cursor.execute("UPDATE users SET subscription_active = 1, subscription_end = ? WHERE user_id=?", (new_end.isoformat(), user_id))
    conn.commit()
    conn.close()
    admin_log(admin_id, "add_subscription", f"user_id={user_id}, days={days}, new_end={new_end.isoformat()}")
    if check_referral:
        add_referral_bonus(user_id)

def get_user_subscription_status(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_active, subscription_end FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    active, end_str = row
    if not active:
        conn.close()
        return False
    if end_str:
        try:
            end_date = datetime.datetime.fromisoformat(end_str)
            if end_date < datetime.datetime.now():
                cursor.execute("UPDATE users SET subscription_active = 0 WHERE user_id = ?", (user_id,))
                conn.commit()
                conn.close()
                return False
        except:
            pass
    conn.close()
    return True

def generate_referral_link(user_id: int, bot_username: str = "NumerologArkadiy_bot") -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

def add_referral_bonus(referred_user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT referred_by FROM users WHERE user_id=?", (referred_user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close()
        return
    referrer_id = row[0]
    add_subscription_days(referrer_id, 7, check_referral=False, admin_id=0)
    add_xp(referrer_id, "referral_subscription")
    conn.close()

def get_referral_stats(user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by=? AND subscription_active=1", (user_id,))
    paid_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
    total_count = cursor.fetchone()[0]
    conn.close()
    return {"total": total_count, "paid": paid_count}

def get_free_questions_remaining(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT free_queries_today, last_active FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return 5
    count = row[0]
    last_active = row[1]
    if last_active:
        last_date = datetime.datetime.fromisoformat(last_active).date()
        today = datetime.date.today()
        if last_date < today:
            count = 0
    remaining = max(0, 5 - count)
    conn.close()
    return remaining

def increment_free_query(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT free_queries_today, last_active FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, free_queries_today, last_active) VALUES (?, 1, ?)",
                       (user_id, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    count = row[0]
    last_active = row[1]
    if last_active:
        last_date = datetime.datetime.fromisoformat(last_active).date()
        today = datetime.date.today()
        if last_date < today:
            count = 0
    if count >= 5:
        conn.close()
        return False
    count += 1
    cursor.execute("UPDATE users SET free_queries_today = ?, last_active = ? WHERE user_id=?",
                   (count, datetime.datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()
    return True

def save_dialog_history(user_id: int, role: str, message_text: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO dialog_history (user_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
                   (user_id, role, message_text, datetime.datetime.now().isoformat()))
    cursor.execute("DELETE FROM dialog_history WHERE id NOT IN (SELECT id FROM dialog_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 20)", (user_id,))
    conn.commit()
    conn.close()

def get_dialog_history(user_id: int, limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, message, timestamp FROM dialog_history WHERE user_id=? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1], row[2]) for row in rows]

def get_cached_response(user_id: int, request_type: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT response_text FROM messages_cache WHERE user_id=? AND request_type=?", (user_id, request_type))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_cached_response(user_id: int, request_type: str, response: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO messages_cache (user_id, request_type, response_text, cache_date) VALUES (?, ?, ?, ?)",
                   (user_id, request_type, response, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def delete_user_cache(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages_cache WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def grant_achievement(user_id: int, achievement: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO achievements (user_id, achievement, earned_at) VALUES (?, ?, ?)",
                   (user_id, achievement, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    add_xp(user_id, "first_calculation" if achievement == "first_calculation" else None)

def get_achievements(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT achievement, earned_at FROM achievements WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows]

def start_challenge(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM challenges WHERE user_id=?", (user_id,))
    start = datetime.datetime.now().isoformat()
    for day in range(1, 8):
        cursor.execute("INSERT INTO challenges (user_id, day, completed, start_date) VALUES (?, ?, 0, ?)",
                       (user_id, day, start))
    conn.commit()
    conn.close()
    return True

def complete_challenge_day(user_id: int, day: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE challenges SET completed=1, completed_at=? WHERE user_id=? AND day=?", 
                   (datetime.datetime.now().isoformat(), user_id, day))
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM challenges WHERE user_id=? AND completed=0", (user_id,))
    incomplete = cursor.fetchone()[0]
    if incomplete == 0:
        add_subscription_days(user_id, 3, check_referral=False, admin_id=0)
        conn.close()
        return True
    conn.close()
    return False

def get_challenge_progress(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT day, completed FROM challenges WHERE user_id=? ORDER BY day", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows]

def log_mood(user_id: int, mood: int, comment: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    cursor.execute("INSERT OR REPLACE INTO mood_log (user_id, mood, comment, log_date) VALUES (?, ?, ?, ?)",
                   (user_id, mood, comment, today))
    conn.commit()
    conn.close()

def get_week_moods(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    cursor.execute("SELECT log_date, mood, comment FROM mood_log WHERE user_id=? AND log_date >= ? ORDER BY log_date", (user_id, week_ago))
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1], row[2]) for row in rows]

def backup_database():
    import shutil
    src = "arkadiy_bot.db"
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{backup_dir}/arkadiy_bot_{timestamp}.db"
    shutil.copy2(src, dst)
    for f in glob.glob(f"{backup_dir}/arkadiy_bot_*.db"):
        if os.path.getmtime(f) < time.time() - 7*86400:
            os.remove(f)
    asyncio.create_task(upload_to_yadisk(dst))
    return dst

async def upload_to_yadisk(file_path):
    print(f"Backup saved locally: {file_path}")

def set_bot_config(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_bot_config(key: str, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM bot_config WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def admin_log(admin_id: int, action: str, details: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO admin_logs (admin_id, action, details, created_at) VALUES (?, ?, ?, ?)",
                   (admin_id, action, details, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_psycho_result(user_id: int, result_text: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO psycho_results (user_id, result_text, created_at) VALUES (?, ?, ?)",
                   (user_id, result_text, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_psycho_result(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT result_text, created_at FROM psycho_results WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)

def update_last_active(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (datetime.datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def add_xp(user_id: int, action: str):
    reward = XP_REWARDS.get(action, 0)
    if reward == 0:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    current_xp = row[0] if row[0] is not None else 0
    current_level = row[1] if row[1] is not None else 1
    new_xp = current_xp + reward
    new_level = current_level
    for lvl, data in LEVELS.items():
        if new_xp >= data["xp"]:
            new_level = lvl
    cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (new_xp, new_level, user_id))
    conn.commit()
    conn.close()
    if new_level > current_level:
        pass

def calculate_level(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return 1, 0, 100
    current_xp = row[0] if row[0] is not None else 0
    current_level = row[1] if row[1] is not None else 1
    next_xp = LEVELS.get(current_level + 1, {}).get("xp", current_xp + 100)
    return current_level, current_xp, next_xp

CRISIS_KEYWORDS = ["депрессия", "суицид", "мысли о смерти", "безысходность", "не хочу жить", "покончить с собой"]

async def check_crisis(message_text: str, user_id: int, bot, admin_ids):
    text_lower = message_text.lower()
    for word in CRISIS_KEYWORDS:
        if word in text_lower:
            for admin_id in admin_ids:
                await bot.send_message(admin_id, f"⚠️ Кризисная ситуация!\nПользователь {user_id} написал: {message_text[:200]}")
            return f"Друг мой, я слышу, что вам тяжело. Пожалуйста, обратитесь за профессиональной помощью: {CRISIS_HELP_LINKS.get('url', '')}. Вы не один."
    return None

# ---------- ФУНКЦИИ ДЛЯ ПОГОДЫ И ЧАСОВЫХ ПОЯСОВ ----------
async def get_weather_by_coords(lat: float, lon: float) -> str:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "timezone": "auto"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    weather = data.get("current_weather", {})
                    temp = weather.get("temperature")
                    wind_speed = weather.get("windspeed")
                    if temp is not None and wind_speed is not None:
                        return f"🌡️ Температура: {temp}°C, 💨 Ветер: {wind_speed} м/с"
                    else:
                        return "Не удалось получить данные о погоде."
                else:
                    return f"Ошибка при получении погоды: {resp.status}"
    except Exception as e:
        print(f"Ошибка запроса погоды: {e}")
        return "Не удалось получить прогноз погоды."

async def get_timezone_by_coords(lat: float, lon: float) -> str:
    url = f"http://worldtimeapi.org/api/timezone/{lat}/{lon}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("timezone", "Europe/Moscow")
                else:
                    return "Europe/Moscow"
    except Exception:
        return "Europe/Moscow"

async def get_city_coords(city_name: str) -> tuple:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,
        "language": "ru",
        "format": "json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("results") and len(data["results"]) > 0:
                        result = data["results"][0]
                        return result.get("latitude", 55.75), result.get("longitude", 37.62)
                    else:
                        return None, None
                else:
                    return None, None
    except Exception as e:
        print(f"Ошибка поиска города: {e}")
        return None, None

def translate_timezone(tz_name: str) -> str:
    tz_map = {
        "Europe/Moscow": "Московское время (UTC+3)",
        "Europe/Samara": "Самарское время (UTC+4)",
        "Asia/Yekaterinburg": "Екатеринбургское время (UTC+5)",
        "Asia/Omsk": "Омское время (UTC+6)",
        "Asia/Novosibirsk": "Новосибирское время (UTC+7)",
        "Asia/Krasnoyarsk": "Красноярское время (UTC+7)",
        "Asia/Irkutsk": "Иркутское время (UTC+8)",
        "Asia/Yakutsk": "Якутское время (UTC+9)",
        "Asia/Vladivostok": "Владивостокское время (UTC+10)",
        "Asia/Magadan": "Магаданское время (UTC+11)",
        "Asia/Kamchatka": "Камчатское время (UTC+12)",
        "Europe/Kaliningrad": "Калининградское время (UTC+2)",
        "Europe/Volgograd": "Волгоградское время (UTC+3)",
        "Europe/London": "Лондонское время (UTC+0)",
        "America/New_York": "Нью-Йорк (UTC-4)",
        "America/Los_Angeles": "Лос-Анджелес (UTC-7)",
    }
    return tz_map.get(tz_name, tz_name)

# ---------- ФУНКЦИИ ДЛЯ ГРУПП (НОВЫЕ) ----------
def format_subscription_remaining(end_date_str: str) -> str:
    if not end_date_str:
        return "не активна"
    try:
        end = datetime.datetime.fromisoformat(end_date_str)
        now = datetime.datetime.now()
        diff = end - now
        if diff.total_seconds() <= 0:
            return "истекла"
        days = diff.days
        if days >= 1:
            return f"осталось {days} дн."
        else:
            hours = int(diff.total_seconds() // 3600)
            if hours == 0:
                return "менее часа"
            return f"осталось {hours} ч."
    except:
        return "ошибка"

async def check_and_expire_subscriptions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, subscription_end FROM users WHERE subscription_active=1 AND subscription_end IS NOT NULL")
    rows = cursor.fetchall()
    now = datetime.datetime.now()
    for user_id, end_str in rows:
        try:
            end_date = datetime.datetime.fromisoformat(end_str)
            if end_date < now:
                cursor.execute("UPDATE users SET subscription_active = 0 WHERE user_id = ?", (user_id,))
        except:
            pass
    conn.commit()
    conn.close()

def get_zodiac_sign(birth_date: str) -> str:
    try:
        day, month, _ = map(int, birth_date.split('.'))
        if (month == 3 and day >= 21) or (month == 4 and day <= 19):
            return "Овен"
        elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
            return "Телец"
        elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
            return "Близнецы"
        elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
            return "Рак"
        elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
            return "Лев"
        elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
            return "Дева"
        elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
            return "Весы"
        elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
            return "Скорпион"
        elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
            return "Стрелец"
        elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
            return "Козерог"
        elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
            return "Водолей"
        else:
            return "Рыбы"
    except:
        return "не определён"

# ---------- ГЕНЕРАЦИЯ КОНТЕНТА ДЛЯ ГРУПП ----------
TOPICS = [
    ("psychology", 35),
    ("relationships", 25),
    ("support", 25),
    ("self_knowledge", 10),
    ("numerology", 3),
    ("astrology", 2),
]

NIGHT_MESSAGES = [
    "Спокойной ночи, друзья! Пусть сны будут ясными, а завтрашний день – добрым.",
    "Уходя, оставляю вам тишину. Отдыхайте. Завтра будет новый день.",
    "Звёзды уже зажглись. Я тоже гашу свет. До встречи завтра.",
    "Ночь – время для восстановления. Спите спокойно."
]

MORNING_MESSAGES = [
    "Доброе утро! Новый день – новые возможности. Я с вами.",
    "Просыпайтесь! Мир ждёт вас. Сегодня мы разберёмся с тем, что вчера казалось сложным.",
    "Утро – время для планов. Пусть сегодняшний день будет удачным.",
    "Доброе утро! Начните день с улыбки. Я рядом."
]

def generate_night_message() -> str:
    return random.choice(NIGHT_MESSAGES)

def generate_morning_message() -> str:
    return random.choice(MORNING_MESSAGES)

async def generate_group_message(chat_id: int, is_long: bool = False) -> str:
    topics, weights = zip(*TOPICS)
    topic = random.choices(topics, weights=weights, k=1)[0]

    if is_long:
        length_desc = "развёрнутое (8–10 предложений), цепляющее, с интригой"
    else:
        length_desc = "короткое (2–3 предложения), интригующее"

    prompt = (
        f"Ты — Аркадий Викторович, мудрый собеседник. Напиши сообщение для группы людей на тему '{topic}'. "
        f"Сообщение должно быть {length_desc}. "
        "Оно должно быть тёплым, поддерживающим, без сложных терминов. "
        "Если тема психология, отношения или поддержка – сделай акцент на эмоциях, советах, аффирмациях. "
        "Если нумерология или астрология – дай краткий, но интересный факт. "
        "Сообщение должно быть уникальным, не повторять предыдущие формулировки. "
        "Не используй штампы, избегай политики и религии. "
        "Заканчивай интригой или вопросом."
    )

    response = await get_yandex_gpt_response(prompt, 0)

    # Проверка уникальности
    conn = get_connection()
    cursor = conn.cursor()
    msg_hash = hashlib.sha256(response.encode()).hexdigest()
    week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    cursor.execute("SELECT 1 FROM group_sent_log WHERE message_hash = ? AND sent_at >= ?", (msg_hash, week_ago))
    if cursor.fetchone():
        for attempt in range(3):
            new_prompt = prompt + f" (попытка {attempt+1}, используй другой подход)"
            response = await get_yandex_gpt_response(new_prompt, 0)
            msg_hash = hashlib.sha256(response.encode()).hexdigest()
            cursor.execute("SELECT 1 FROM group_sent_log WHERE message_hash = ? AND sent_at >= ?", (msg_hash, week_ago))
            if not cursor.fetchone():
                break
    conn.close()
    return response

# ---------- ГЕНЕРАЦИЯ PDF ----------
def generate_pdf_matrix(user_id: int, name: str, destiny: int, matrix_text: str) -> bytes:
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 16)
        c.drawString(30, height - 30, f"Матрица судьбы для {name}")
        c.setFont("Helvetica", 12)
        c.drawString(30, height - 50, f"Число судьбы: {destiny}")
        c.drawString(30, height - 70, f"Дата формирования: {datetime.datetime.now().strftime('%d.%m.%Y')}")
        y = height - 100
        for line in matrix_text.split('\n'):
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 12)
            if len(line) > 80:
                for i in range(0, len(line), 80):
                    c.drawString(30, y, line[i:i+80])
                    y -= 15
            else:
                c.drawString(30, y, line)
                y -= 15
        c.save()
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        print(f"Ошибка генерации PDF: {e}")
        return None
def admin_log(admin_id: int, action: str, details: str = ""):
    import datetime
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO admin_logs (admin_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (admin_id, action, details, datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()