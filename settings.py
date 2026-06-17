import os

BOT_VERSION = "2.2.0"
LOGS_DIR = "/root/arkadiy_bot/logs"
HEALTHCHECK_PORT = 9001
DEFAULT_TIMEZONE = "Europe/Moscow"
FSM_STORAGE_PATH = "fsm_states.db"
SUBSCRIPTION_REMIND_DAYS = 3
RATE_LIMIT_MESSAGES = 20
PROMOCODE_ATTEMPTS_LIMIT = 5

CRISIS_HELP_LINKS = {
    "phone": "https://ваш-сайт/help",
    "url": "https://ваш-сайт/psychology"
}

LEVELS = {
    1: {"name": "Искатель", "xp": 0},
    2: {"name": "Любопытный", "xp": 150},
    3: {"name": "Понимающий", "xp": 400},
    4: {"name": "Доверяющий числам", "xp": 800},
    5: {"name": "Знающий", "xp": 1400},
    6: {"name": "Видящий", "xp": 2200},
    7: {"name": "Друг чисел", "xp": 3200},
    8: {"name": "Проводник", "xp": 4500},
    9: {"name": "Мастер гармонии", "xp": 6000},
    10: {"name": "Мастер судьбы", "xp": 8000},
    11: {"name": "Хранитель знаний", "xp": 10500},
    12: {"name": "Видящий", "xp": 13500},
    13: {"name": "Наставник", "xp": 17000},
    14: {"name": "Мудрец", "xp": 21000},
    15: {"name": "Просветлённый", "xp": 26000},
    16: {"name": "Аркадий (почётный)", "xp": 32000},
    17: {"name": "Хранитель чисел", "xp": 39000},
    18: {"name": "Властелин чисел", "xp": 47000},
    19: {"name": "Нумерологический гуру", "xp": 56000},
    20: {"name": "Абсолют", "xp": 66000}
}

XP_REWARDS = {
    "first_calculation": 50,
    "daily_visit": 10,
    "ask_question": 5,
    "test_passed": 30,
    "challenge_completed": 100,
    "referral_subscription": 150,
    "mood_log_7_days": 40,
    "daily_card_received": 5
}

DAILY_CARD_HOUR = 9
MIN_ACTIVE_DAYS_FOR_PHONE_REQUEST = 2

STARS_TO_RUB_RATE = 2

PAYMENTS_TOKEN = os.getenv("PAYMENTS_TOKEN", "")

# ---------- НАСТРОЙКИ СЕКСОЛОГИИ ----------
SEXOLOGY_FREE_QUERIES_LIMIT = 3  # бесплатных вопросов в день
SEXOLOGY_ARTICLES_PER_WEEK = 2   # статей в неделю
SEXOLOGY_ARTICLES_INITIAL_COUNT = 10  # начальное количество статей
SEXOLOGY_TOPICS = [
    "Как стресс влияет на либидо",
    "Как говорить с партнёром о сексе",
    "Женская сексуальность и самооценка",
    "Мужская сексуальность и уверенность",
    "Как разнообразить интимную жизнь",
    "Сексуальные практики для укрепления отношений",
    "Как восстановить влечение после кризиса",
    "Сексуальная совместимость: мифы и реальность",
    "Как справляться с несовпадением либидо",
    "Психология секса и близости",
    "Как улучшить интимную связь",
    "Секс и эмоциональная близость",
    "Как обсуждать желания",
    "Сексуальная жизнь после рождения ребёнка",
    "Как сохранить страсть в долгих отношениях"
]