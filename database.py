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
    
    # Таблица пользователей
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
            free_sexology_queries_today INTEGER DEFAULT 0,
            send_daily BOOLEAN DEFAULT 1,
            is_sleeping BOOLEAN DEFAULT 0,
            referred_by INTEGER,
            phone TEXT,
            bot_version TEXT,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            city TEXT,
            timezone TEXT,
            birth_time TEXT,
            birth_place TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'free_sexology_queries_today' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN free_sexology_queries_today INTEGER DEFAULT 0")
    
    # Таблица статей сексологии
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sexology_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT,
            status TEXT DEFAULT 'pending',
            topic TEXT
        )
    ''')
    
    # ========== НОВАЯ ТАБЛИЦА ДЛЯ ПРОМПТОВ ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            function_name TEXT PRIMARY KEY,
            system_prompt TEXT,
            free_prompt TEXT,
            paid_prompt TEXT,
            updated_at TEXT
        )
    ''')
    
    # Остальные таблицы
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
            comment TEXT,
            log_date TEXT,
            PRIMARY KEY (user_id, log_date)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS psycho_results (
            user_id INTEGER,
            result_text TEXT,
            created_at TEXT,
            PRIMARY KEY (user_id, created_at)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_chats (
            chat_id INTEGER PRIMARY KEY,
            is_active BOOLEAN DEFAULT 0,
            created_at TEXT,
            frequency INTEGER DEFAULT 2
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_sent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            sent_at TEXT,
            message_hash TEXT,
            content_type TEXT
        )
    ''')
    
    # Настройки
    cursor.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('system_prompt', 'Вы — Аркадий Викторович...')")
    cursor.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('subscription_price', '249')")
    cursor.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('sexology_free_queries_limit', '3')")
    cursor.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('sexology_articles_per_week', '2')")
    
    # Инициализация промптов (создаём начальные записи)
    initialize_default_prompts()
    
    conn.commit()
    conn.close()

# ---------- ФУНКЦИИ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ----------
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
                               "reg_date", "last_active", "free_queries_today", "free_sexology_queries_today",
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
                       "free_sexology_queries_today", "send_daily", "is_sleeping", "referred_by",
                       "phone", "bot_version", "xp", "level", "city", "timezone",
                       "birth_time", "birth_place"):
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

# ---------- ФУНКЦИИ ДЛЯ СЕКСОЛОГИИ ----------
def get_sexology_free_queries_today(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT free_sexology_queries_today, last_active FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return 0
    count = row[0]
    last_active = row[1]
    if last_active:
        last_date = datetime.datetime.fromisoformat(last_active).date()
        today = datetime.date.today()
        if last_date < today:
            return 0
    return count

def increment_sexology_free_query(user_id: int) -> bool:
    limit = int(get_bot_config("sexology_free_queries_limit", "3"))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT free_sexology_queries_today, last_active FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, free_sexology_queries_today, last_active) VALUES (?, 1, ?)",
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
    if count >= limit:
        conn.close()
        return False
    count += 1
    cursor.execute("UPDATE users SET free_sexology_queries_today = ?, last_active = ? WHERE user_id=?",
                   (count, datetime.datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()
    return True

def add_sexology_article(title: str, content: str, topic: str = "", status: str = "pending") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sexology_articles (title, content, created_at, status, topic) VALUES (?, ?, ?, ?, ?)",
                   (title, content, datetime.datetime.now().isoformat(), status, topic))
    conn.commit()
    article_id = cursor.lastrowid
    conn.close()
    return article_id

def get_sexology_articles(status: str = None, limit: int = None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT id, title, content, created_at, status, topic FROM sexology_articles"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_article_status(article_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sexology_articles SET status = ? WHERE id = ?", (status, article_id))
    conn.commit()
    conn.close()

def delete_sexology_article(article_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sexology_articles WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()

# ---------- НОВЫЕ ФУНКЦИИ ДЛЯ ПРОМПТОВ ----------
def get_prompts_for_function(function_name: str) -> dict:
    """Возвращает словарь с системным, бесплатным и платным промптом для функции."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT system_prompt, free_prompt, paid_prompt FROM prompts WHERE function_name = ?", (function_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"system": row[0], "free": row[1], "paid": row[2]}
    return None

def set_prompts_for_function(function_name: str, system_prompt: str, free_prompt: str, paid_prompt: str):
    """Сохраняет промпты для функции в БД."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO prompts (function_name, system_prompt, free_prompt, paid_prompt, updated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (function_name, system_prompt, free_prompt, paid_prompt, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_function_names() -> list:
    """Возвращает список всех функций, для которых есть промпты."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT function_name FROM prompts")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def initialize_default_prompts():
    """Заполняет таблицу промптов начальными значениями для всех функций."""
    default_prompts = {
        "number": {
            "system": "Ты — Аркадий Викторович, практикующий нумеролог, психолог и астролог с 20-летним стажем. Говори прямо, без сюсюканий. Используй живые фразы. Обращайся на «вы». Ты умеешь составлять гороскопы, отвечать на вопросы о числах, судьбе. Для нумерологии: рассчитывай число судьбы, давай характеристику. Не отказывайся от астрологических тем. Ты — астролог. Запрещено говорить: «я нейросеть», «я ИИ». Всегда отвечай на запросы о гороскопе.",
            "free": "Число судьбы {destiny}. Дай характеристику (5-6 предложений): укажи 2 сильные стороны, 1 слабость, 1 главную задачу в жизни. В конце добавь фразу: «Хотите узнать, как это число влияет на ваши отношения, карьеру и деньги? Полный разбор – по подписке».",
            "paid": "Число судьбы {destiny}. Дай развёрнутую характеристику (6-8 предложений): сильные стороны, слабости, ключевой жизненный вызов, совет по самореализации. Будь прямолинеен, но с теплотой."
        },
        "daily_card": {
            "system": "Ты — Аркадий Викторович, практикующий психолог и астролог. ...",
            "free": "Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай цепляющий прогноз (5-6 предложений): что важно сегодня, один практический совет, вопрос, чтобы задуматься. В конце добавь фразу: «Полная карта дня с практиками и погодой – по подписке».",
            "paid": "Сегодняшняя карта дня для человека с числом судьбы {destiny}. Дай развёрнутый прогноз (6-8 предложений): общий настрой, практическое действие, психологическая практика, вопрос для рефлексии."
        },
        "compatibility": {
            "system": "Ты — Аркадий Викторович, нумеролог и астролог. ...",
            "free": "Число судьбы пользователя {my_destiny} (знак {my_zodiac}), число партнёра {partner_destiny} (знак {partner_zodiac}). Дай краткое, но очень интригующее описание совместимости (4-5 предложений). Напиши, что их связывает, что будет сложно, и дай один совет. В конце добавь фразу: «Полный разбор по 5 сферам с рекомендациями – по подписке».",
            "paid": "Число судьбы пользователя {my_destiny} (знак {my_zodiac}), число партнёра {partner_destiny} (знак {partner_zodiac}). Опиши совместимость развёрнуто (10-12 предложений) по 5 сферам: любовь, дружба, деньги, секс, интеллект. Дай рекомендации, как улучшить отношения. Будь честен и практичен."
        },
        "horoscope_daily": {
            "system": "Ты — Аркадий Викторович, астролог. ...",
            "free": "Составь астрологический гороскоп на сегодня для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай цепляющий прогноз (5-6 предложений): укажи, что важно сегодня, дай один совет, задай вопрос для размышления. В конце добавь фразу: «Полный гороскоп на месяц и ежедневные прогнозы – по подписке».",
            "paid": "Составь астрологический гороскоп на сегодня для человека с числом судьбы {destiny} и знаком зодиака {zodiac}. Дай развёрнутый прогноз (6-7 предложений) по 2 сферам (любовь и работа/деньги). Добавь совет на день."
        },
        "sexology": {
            "system": "Ты — Аркадий Викторович, практикующий психолог и сексолог с 20-летним стажем. Ты даёшь честные, деликатные, но прямые ответы на вопросы о сексуальных отношениях, интимной близости, совместимости, психологии секса. Говори на «вы», без осуждения, с уважением. Если вопрос требует профессиональной медицинской помощи – мягко направь к специалисту, но при этом дай полезный совет. Твои ответы должны быть тёплыми, человечными, без сложных терминов. Запрещено: грубость, пошлость, неэтичные советы. Используй обращения «друг мой», «уважаемый». Заканчивай вопросом или советом.",
            "free": "Дай короткий, но цепляющий ответ (3-4 предложения) на вопрос пользователя. Не раскрывай всех деталей, оставь интригу. В конце добавь фразу: «Полная консультация и практические рекомендации – по подписке».",
            "paid": "Ответь развёрнуто (8-10 предложений) как психолог и сексолог, дай практические советы, будь деликатен. Учти число судьбы, если это уместно."
        },
        # Добавьте остальные функции по аналогии...
        # Для упрощения я оставлю базовые, остальные можно добавить позже через админ-панель.
    }
    for func, prompts in default_prompts.items():
        if not get_prompts_for_function(func):
            set_prompts_for_function(func, prompts["system"], prompts["free"], prompts["paid"])