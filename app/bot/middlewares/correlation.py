from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.utils.correlation import set_correlation_id, clear_correlation_id


class CorrelationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Generate correlation id for each incoming update, reuse if exists on nested calls
        cid = set_correlation_id()
        # put cid into handler data so handlers can log/use it if needed
        data["correlation_id"] = cid
        try:
            return await handler(event, data)
        finally:
            # Clear after processing to avoid leaking across tasks
            clear_correlation_id()
