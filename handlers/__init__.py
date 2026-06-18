from aiogram import Dispatcher
from .start import router as start_router
from .profile import router as profile_router
from .psycho import router as psycho_router
from .main import router as main_router
from .challenge import router as challenge_router
from .promo import router as promo_router
from .common import router as common_router
from .horoscope import router as horoscope_router
from .astro import router as astro_router
from .groups import router as groups_router
from .help import router as help_router
from .premium import router as premium_router
from .sexology import router as sexology_router

def register_handlers(dp: Dispatcher, bot, admin_ids, bot_version):
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(psycho_router)
    dp.include_router(main_router)
    dp.include_router(challenge_router)
    dp.include_router(promo_router)
    dp.include_router(common_router)
    dp.include_router(horoscope_router)
    dp.include_router(astro_router)      # <-- зарегистрирован
    dp.include_router(groups_router)
    dp.include_router(help_router)
    dp.include_router(premium_router)
    dp.include_router(sexology_router)