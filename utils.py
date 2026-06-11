import datetime
import glob
import os
import time
import asyncio
import aiohttp
from database import get_connection
from settings import LEVELS, XP_REWARDS, CRISIS_HELP_LINKS, LOGS_DIR
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# ---------- Основные функции ----------
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
    cursor.execute("SELECT subscription_active FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else False

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

# ---------- Генерация PDF-отчёта ----------
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