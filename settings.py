# settings.py
import os

# Версия бота
BOT_VERSION = "2.0.0"  # первая версия глобального обновления

# Папки и логи
LOGS_DIR = "/root/arkadiy_bot/logs"
HEALTHCHECK_PORT = 9001

# Часовой пояс по умолчанию
DEFAULT_TIMEZONE = "Europe/Moscow"

# Путь к базе данных FSM (состояний)
FSM_STORAGE_PATH = "fsm_states.db"

# Интервал напоминания о подписке (дни)
SUBSCRIPTION_REMIND_DAYS = 3

# Лимиты
RATE_LIMIT_MESSAGES = 20  # сообщений в минуту
PROMOCODE_ATTEMPTS_LIMIT = 5  # попыток ввода кода

# Ссылки на ресурсы помощи
CRISIS_HELP_LINKS = {
    "phone": "https://ваш-сайт/help",
    "url": "https://ваш-сайт/psychology"
}

# Настройки уровней (опыт для каждого уровня)
LEVELS = {
    1: {"name": "Искатель", "xp": 0},
    2: {"name": "Любопытный", "xp": 100},
    3: {"name": "Понимающий", "xp": 250},
    4: {"name": "Доверяющий числам", "xp": 500},
    5: {"name": "Знающий", "xp": 800},
    6: {"name": "Видущий", "xp": 1200},
    7: {"name": "Друг чисел", "xp": 1700},
    8: {"name": "Проводник", "xp": 2300},
    9: {"name": "Мастер гармонии", "xp": 3000},
    10: {"name": "Мастер судьбы", "xp": 4000},
    11: {"name": "Хранитель знаний", "xp": 5200},
    12: {"name": "Видящий", "xp": 6600},
    13: {"name": "Наставник", "xp": 8200},
    14: {"name": "Мудрец", "xp": 10000},
    15: {"name": "Просветлённый", "xp": 12500},
    16: {"name": "Аркадий (почётный)", "xp": 15500},
    17: {"name": "Хранитель чисел", "xp": 19000},
    18: {"name": "Властелин чисел", "xp": 23000},
    19: {"name": "Нумерологический гуру", "xp": 28000},
    20: {"name": "Абсолют", "xp": 35000}
}

# Действия, за которые начисляются очки опыта
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

# Настройки рассылки
DAILY_CARD_HOUR = 9  # час рассылки карты дня по местному времени
MIN_ACTIVE_DAYS_FOR_PHONE_REQUEST = 2  # через сколько дней активного использования просить номер телефона