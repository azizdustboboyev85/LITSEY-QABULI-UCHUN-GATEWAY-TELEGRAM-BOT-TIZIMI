from aiogram import Router
from . import student, group, panel

def get_router() -> Router:
    """Barcha routerlarni yagona routerga birlashtirish."""
    router = Router()
    router.include_router(student.router)
    router.include_router(group.router)
    router.include_router(panel.router)
    return router
