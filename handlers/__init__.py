from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.psycho import router as psycho_router
from handlers.main import router as main_router
from handlers.challenge import router as challenge_router
from handlers.promo import router as promo_router
from handlers.common import router as common_router
from handlers.horoscope import router as horoscope_router
from handlers.astro import router as astro_router
from handlers.groups import router as groups_router
from handlers.help import router as help_router
# alarm удалён

def register_handlers(dp, bot, admin_ids, bot_version):
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(psycho_router)
    dp.include_router(main_router)
    dp.include_router(challenge_router)
    dp.include_router(promo_router)
    dp.include_router(common_router)
    dp.include_router(horoscope_router)
    dp.include_router(astro_router)
    dp.include_router(groups_router)
    dp.include_router(help_router)