from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Deque, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from app.services.security import is_admin_uid


class RateLimitMiddleware(BaseMiddleware):
    """Simple per-user rate limiter.

    Limits number of messages per user within a 60-second window.
    """

    def __init__(self, max_per_minute: int = 20, notify_text: str | None = None) -> None:
        self.max = max_per_minute
        self.window = 60.0
        self.history: Dict[int, Deque[float]] = defaultdict(deque)
        self.notify_text = notify_text or "محدودیت نرخ پیام: لطفاً کمی بعد تلاش کنید."

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Admins are exempt from rate limiting
        uid_admin = None
        if isinstance(event, Message) and event.from_user:
            uid_admin = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            uid_admin = event.from_user.id
        if uid_admin and is_admin_uid(uid_admin):
            return await handler(event, data)
        # Message throttling
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
            now = time.monotonic()
            q = self.history[uid]
            while q and (now - q[0]) > self.window:
                q.popleft()
            if len(q) >= self.max:
                try:
                    await event.answer(self.notify_text)
                except Exception:
                    pass
                return None
            q.append(now)
        # CallbackQuery throttling
        elif isinstance(event, CallbackQuery) and event.from_user:
            uid = event.from_user.id
            now = time.monotonic()
            q = self.history[uid]
            while q and (now - q[0]) > self.window:
                q.popleft()
            if len(q) >= self.max:
                try:
                    # Show a short toast (not an alert popup)
                    await event.answer(self.notify_text, show_alert=False)
                except Exception:
                    pass
                return None
            q.append(now)
        return await handler(event, data)
