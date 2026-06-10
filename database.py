import sqlite3
import datetime

DB_PATH = "arkadiy_bot.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            birth_date TEXT,
            destiny_number INTEGER,
            subscription_active BOOLEAN DEFAULT 0,
            subscription_end TEXT,
            reg_date TEXT,
            last_active TEXT,
            free_queries_today INTEGER DEFAULT 0,
            send_daily BOOLEAN DEFAULT 1,
            is_sleeping BOOLEAN DEFAULT 0,
            referred_by INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages_cache (
            user_id INTEGER,
            request_type TEXT,
            response_text TEXT,
            cache_date TEXT,
            PRIMARY KEY (user_id, request_type)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dialog_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            action_type TEXT DEFAULT 'subscription_days',
            action_value INTEGER,
            max_uses INTEGER,
            used_count INTEGER DEFAULT 0,
            expires_at TEXT,
            created_by INTEGER,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocode_activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code TEXT,
            activated_at TEXT,
            result_text TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            blocked_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            achievement TEXT,
            earned_at TEXT,
            PRIMARY KEY (user_id, achievement)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS challenges (
            user_id INTEGER,
            day INTEGER,
            completed BOOLEAN DEFAULT 0,
            completed_at TEXT,
            start_date TEXT,
            PRIMARY KEY (user_id, day)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_log (
            user_id INTEGER,
            mood INTEGER,
            log_date TEXT,
            PRIMARY KEY (user_id, log_date)
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('system_prompt', 'Вы — Аркадий Викторович...')")
    conn.commit()
    conn.close()