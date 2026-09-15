from aiogram import Router

from . import user, admin


def setup_routers() -> Router:
    """
    Собирает все роутеры в один.

    ВАЖНО: порядок важен!
    - admin идёт первым, чтобы /admin не перехватывался fallback-хендлером AI
    - user идёт вторым — он обрабатывает всё остальное
    """
    router = Router()
    router.include_router(admin.router)
    router.include_router(user.router)
    return router