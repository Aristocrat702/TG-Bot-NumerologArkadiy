from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_promo_code = State()
    waiting_promo_days = State()
    waiting_promo_max_uses = State()
    waiting_promo_expiry = State()
    waiting_reply_user_id = State()
    waiting_reply_text = State()
    waiting_new_price = State()
    waiting_new_prompt = State()
    waiting_broadcast = State()
    waiting_broadcast_segment = State()
    waiting_userinfo = State()
    waiting_confirm_action = State()