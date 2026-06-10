import datetime
import glob
import os
import time
from database import get_connection

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

def remove_from_blacklist(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def calculate_destiny_number(birth_date: str) -> int:
    s = birth_date.replace('.', '')
    total = sum(int(d) for d in s)
    while total > 9 and total not in (11, 22, 33):
        total = sum(int(d) for d in str(total))
    return total

def add_subscription_days(user_id: int, days: int, check_referral: bool = False):
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
    # Реферальный бонус при первой активации подписки
    if check_referral:
        add_referral_bonus(user_id)

def get_user_subscription_status(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_active FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else False

# ---------- Реферальная система ----------
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
    add_subscription_days(referrer_id, 7, check_referral=False)
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

# ---------- Лимиты бесплатных вопросов ----------
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

# ---------- История диалогов ----------
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
    cursor.execute("SELECT role, message FROM dialog_history WHERE user_id=? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows]

# ---------- Кэширование ответов ----------
def get_cached_response(user_id: int, request_type: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT response_text, cache_date FROM messages_cache WHERE user_id=? AND request_type=?", (user_id, request_type))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def save_cached_response(user_id: int, request_type: str, response: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO messages_cache (user_id, request_type, response_text, cache_date) VALUES (?, ?, ?, ?)",
                   (user_id, request_type, response, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ---------- Достижения ----------
def grant_achievement(user_id: int, achievement: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO achievements (user_id, achievement, earned_at) VALUES (?, ?, ?)",
                   (user_id, achievement, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_achievements(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT achievement, earned_at FROM achievements WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows]

# ---------- Челлендж 7 дней ----------
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
        add_subscription_days(user_id, 3, check_referral=False)
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

# ---------- Дневник эмоций ----------
def log_mood(user_id: int, mood: int):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    cursor.execute("INSERT OR REPLACE INTO mood_log (user_id, mood, log_date) VALUES (?, ?, ?)", (user_id, mood, today))
    conn.commit()
    conn.close()

def get_week_moods(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    cursor.execute("SELECT log_date, mood FROM mood_log WHERE user_id=? AND log_date >= ? ORDER BY log_date", (user_id, week_ago))
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows]

# ---------- Бэкап базы данных ----------
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
    return dst

# ---------- Управление настройками ----------
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