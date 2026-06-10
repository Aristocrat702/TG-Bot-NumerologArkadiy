import datetime
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

def calculate_destiny_number(birth_date: str) -> int:
    s = birth_date.replace('.', '')
    total = sum(int(d) for d in s)
    while total > 9 and total not in (11, 22, 33):
        total = sum(int(d) for d in str(total))
    return total

def add_subscription_days(user_id: int, days: int):
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

def get_user_subscription_status(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_active FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else False

def increment_free_query(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT free_queries_today FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return True
    count = row[0]
    if count >= 5:
        conn.close()
        return False
    cursor.execute("UPDATE users SET free_queries_today = free_queries_today + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return True

def can_ask_free_question(user_id: int) -> bool:
    if get_user_subscription_status(user_id):
        return True
    return increment_free_query(user_id)

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
