import datetime

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

def get_progress_bar(user_id: int):
    from .calculations import calculate_level
    level, xp, next_xp = calculate_level(user_id)
    if next_xp == 0:
        return "[████████████████████] 100%"
    progress = int((xp / next_xp) * 20)
    bar = "█" * progress + "░" * (20 - progress)
    return f"[{bar}] {xp}/{next_xp} XP"

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