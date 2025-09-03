from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.types import ReplyKeyboardRemove
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Setting


async def _is_banned(tg_id: int) -> bool:
    """Check USER:{tg_id}:BANNED flag in settings ("1"/"true")."""
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:BANNED"))
        return bool(row and str(row.value).strip().lower() in {"1", "true"})


async def _rbk_sent(tg_id: int) -> bool:
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:RBK_SENT"))
        return bool(row and str(row.value).strip())


async def _mark_rbk_sent(tg_id: int) -> None:
    from datetime import datetime
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:RBK_SENT"))
        if not row:
            session.add(Setting(key=f"USER:{tg_id}:RBK_SENT", value=datetime.utcnow().isoformat()))
        else:
            row.value = datetime.utcnow().isoformat()
        await session.commit()


class BanGateMiddleware(BaseMiddleware):
    """
    Hard ban gate: blocks all messages and callbacks for banned users.
    - No appeal UI or capture: feature removed by request.
    - Removes reply keyboards to disable access to menu.
    """

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        tg_id = user.id
        if not await _is_banned(tg_id):
            return await handler(event, data)

        # Remove reply keyboard once per ban session
        try:
            sent_before = await _rbk_sent(tg_id)
        except Exception:
            sent_before = False
        if not sent_before:
            try:
                await event.bot.send_message(chat_id=tg_id, text="⛔️", reply_markup=ReplyKeyboardRemove())
            except Exception:
                pass
            try:
                await _mark_rbk_sent(tg_id)
            except Exception:
                pass

        # Block further processing and notify user minimally
        if isinstance(event, Message):
            try:
                await event.answer("⛔️ حساب شما در ربات بن شده است.")
            except Exception:
                pass
        else:
            # CallbackQuery: show a short alert/toast
            try:
                await event.answer("blocked")
            except Exception:
                pass
        return None
