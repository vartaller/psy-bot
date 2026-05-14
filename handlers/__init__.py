from aiogram import Dispatcher

from .start import router as start_router
from .menu import router as menu_router
from .activities import router as activities_router
from .profile import router as profile_router
from .thinking_pattern import router as tp_router
from .history import router as history_router


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(activities_router)
    dp.include_router(profile_router)
    dp.include_router(tp_router)
    dp.include_router(history_router)
