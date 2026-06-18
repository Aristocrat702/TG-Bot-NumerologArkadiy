from .admin import register_admin_entry_handler
from .stats import register_stats_handlers
from .broadcast import register_broadcast_handlers
from .subscription import register_subscription_handlers
from .promocodes import register_promocodes_handlers
from .prompt import register_prompt_handlers
from .blacklist import register_blacklist_handlers
from .reply import register_reply_handlers
from .price import register_price_handlers
from .leaderboard import register_leaderboard_handlers
from .logs import register_logs_handlers
from .userinfo import register_userinfo_handlers
from .groups_management import register_groups_management_handlers
from .test_group import register_test_group_handlers
from .articles import register_articles_handlers
from .prompts import register_prompts_handlers
from .activity_export import register_activity_export_handlers
from .group_messages import register_group_messages_handlers
from .clear_db import register_clear_db_handlers

def register_admin_handlers(dp, bot, admin_ids: list):
    register_admin_entry_handler(dp, bot, admin_ids)
    register_stats_handlers(dp, bot, admin_ids)
    register_broadcast_handlers(dp, bot, admin_ids)
    register_subscription_handlers(dp, bot, admin_ids)
    register_promocodes_handlers(dp, bot, admin_ids)
    register_prompt_handlers(dp, bot, admin_ids)
    register_blacklist_handlers(dp, bot, admin_ids)
    register_reply_handlers(dp, bot, admin_ids)
    register_price_handlers(dp, bot, admin_ids)
    register_leaderboard_handlers(dp, bot, admin_ids)
    register_logs_handlers(dp, bot, admin_ids)
    register_userinfo_handlers(dp, bot, admin_ids)
    register_groups_management_handlers(dp, bot, admin_ids)
    register_test_group_handlers(dp, bot, admin_ids)
    register_articles_handlers(dp, bot, admin_ids)
    register_prompts_handlers(dp, bot, admin_ids)
    register_activity_export_handlers(dp, bot, admin_ids)
    register_group_messages_handlers(dp, bot, admin_ids)
    register_clear_db_handlers(dp, bot, admin_ids)