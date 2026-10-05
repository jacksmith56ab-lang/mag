"""
Middleware для тех. режима.
Если тех. режим включён, блокирует все сообщения/колбэки не-админов.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

import database as db
MAINTENANCE_TEXT = (
    "🔧 <b>Технические работы</b>\n\n"
    "В данный момент бот временно недоступен.\n"
    "Пожалуйста, зайдите позже. Приносим извинения за неудобства! 🙏"
)


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Определяем user_id из события
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None

        # Если тех. режим и это не админ — блокируем
        if user_id and user_id not in db.get_admin_ids() and db.is_maintenance():
            if isinstance(event, Message):
                await event.answer(MAINTENANCE_TEXT, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer("🔧 Технические работы. Бот временно недоступен.", show_alert=True)
            return  # не передаём дальше

        return await handler(event, data)
