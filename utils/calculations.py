import datetime
from settings import LEVELS, XP_REWARDS

def calculate_destiny_number(birth_date: str) -> int:
    s = birth_date.replace('.', '')
    total = sum(int(d) for d in s)
    while total > 9 and total not in (11, 22, 33):
        total = sum(int(d) for d in str(total))
    return total

def get_birth_number(birth_date: str) -> int:
    return calculate_destiny_number(birth_date)

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

def calculate_level(user_id: int):
    from .db import get_connection
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

def add_xp(user_id: int, action: str):
    reward = XP_REWARDS.get(action, 0)
    if reward == 0:
        return
    from .db import get_connection
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