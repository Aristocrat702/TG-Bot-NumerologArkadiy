import sqlite3
import datetime
from database import get_connection

def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def create_user(user_id: int, name: str = None, birth_date: str = None, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        if exists:
            fields = []
            values = []
            if name is not None:
                fields.append("name = ?")
                values.append(name)
            if birth_date is not None:
                fields.append("birth_date = ?")
                values.append(birth_date)
            if kwargs:
                for key, val in kwargs.items():
                    if key in ("destiny_number", "subscription_active", "subscription_end",
                               "reg_date", "last_active", "free_queries_today",
                               "send_daily", "is_sleeping", "referred_by", "phone",
                               "bot_version", "xp", "level", "city", "timezone",
                               "birth_time", "birth_place"):
                        fields.append(f"{key} = ?")
                        values.append(val)
            if fields:
                values.append(user_id)
                query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
                cursor.execute(query, values)
        else:
            cursor.execute('''
                INSERT INTO users (user_id, name, birth_date, destiny_number, reg_date, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, name, birth_date, kwargs.get('destiny_number', 0),
                  datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка create_user: {e}")
        conn.rollback()
        conn.close()
        return False

def update_user(user_id: int, **kwargs):
    if not kwargs:
        return True
    conn = get_connection()
    cursor = conn.cursor()
    try:
        fields = []
        values = []
        for key, val in kwargs.items():
            if key in ("name", "birth_date", "destiny_number", "subscription_active",
                       "subscription_end", "reg_date", "last_active", "free_queries_today",
                       "send_daily", "is_sleeping", "referred_by", "phone", "bot_version",
                       "xp", "level", "city", "timezone", "birth_time", "birth_place"):
                fields.append(f"{key} = ?")
                values.append(val)
        if not fields:
            conn.close()
            return True
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка update_user: {e}")
        conn.rollback()
        conn.close()
        return False

def get_subscription_status(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_active, subscription_end FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    active, end_str = row
    if not active:
        return False
    if end_str:
        try:
            end_date = datetime.datetime.fromisoformat(end_str)
            if end_date < datetime.datetime.now():
                return False
        except:
            pass
    return True

def admin_log(admin_id: int, action: str, details: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO admin_logs (admin_id, action, details, created_at) VALUES (?, ?, ?, ?)",
                   (admin_id, action, details, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

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