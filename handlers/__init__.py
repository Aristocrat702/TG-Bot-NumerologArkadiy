from handlers.start import register_start_handlers
from handlers.profile import register_profile_handlers
from handlers.psycho import register_psycho_handlers
from handlers.main import register_main_handlers
from handlers.challenge import register_challenge_handlers
from handlers.promo import register_promo_handlers
from handlers.common import register_common_handlers

def register_handlers(dp, bot, admin_ids, bot_version):
    register_start_handlers(dp, bot, admin_ids, bot_version)
    register_profile_handlers(dp, bot, admin_ids)
    register_psycho_handlers(dp, bot, admin_ids)
    register_main_handlers(dp, bot, admin_ids)
    register_challenge_handlers(dp, bot, admin_ids)
    register_promo_handlers(dp, bot, admin_ids)
    register_common_handlers(dp, bot, admin_ids)