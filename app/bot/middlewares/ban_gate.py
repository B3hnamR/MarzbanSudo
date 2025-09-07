from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.types import ReplyKeyboardRemove
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Setting

# Lightweight TTL caches to reduce hot-path DB roundtrips
import os
import time

_BAN_CACHE: dict[int, tuple[bool, float]] = {}
_RBK_CACHE: dict[int, float] = {}
_TTL_SECONDS = float(os.getenv("BANGATE_CACHE_TTL", "60") or "60")


def _cache_get_bool(cache: dict[int, tuple[bool, float]], key: int) -> bool | None:
    now = time.monotonic()
    item = cache.get(key)
    if not item:
        return None
    val, ts = item
    if now - ts > _TTL_SECONDS:
        cache.pop(key, None)
        return None
    return val


def _cache_set_bool(cache: dict[int, tuple[bool, float]], key: int, val: bool) -> None:
    cache[key] = (val, time.monotonic())


def invalidate_ban_cache(tg_id: int) -> None:
    """Invalidate ban state cache for a Telegram user id."""
    _BAN_CACHE.pop(tg_id, None)


def invalidate_rbk_cache(tg_id: int) -> None:
    """Invalidate reply-keyboard-sent cache for a Telegram user id."""
    _RBK_CACHE.pop(tg_id, None)


async def _is_banned(tg_id: int) -> bool:
    """Check USER:{tg_id}:BANNED flag in settings ("1"/"true") with TTL cache."""
    cached = _cache_get_bool(_BAN_CACHE, tg_id)
    if cached is not None:
        return cached
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:BANNED"))
        val = bool(row and str(row.value).strip().lower() in {"1", "true"})
        _cache_set_bool(_BAN_CACHE, tg_id, val)
        return val


async def _rbk_sent(tg_id: int) -> bool:
    cached = _cache_get_bool(_RBK_CACHE, tg_id)
    if cached is not None:
        return cached
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:RBK_SENT"))
        val = bool(row and str(row.value).strip())
        if val:
            _cache_set_bool(_RBK_CACHE, tg_id, True)
        return val


async def _mark_rbk_sent(tg_id: int) -> None:
    from datetime import datetime
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:RBK_SENT"))
        if not row:
            session.add(Setting(key=f"USER:{tg_id}:RBK_SENT", value=datetime.utcnow().isoformat()))
        else:
            row.value = datetime.utcnow().isoformat()
        await session.commit()
    # Update cache best-effort
    try:
        _cache_set_bool(_RBK_CACHE, tg_id, True)
    except Exception:
        pass


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
                await event.answer("⛔️ حساب شما در ربات بن شده است.")
            except Exception:
                pass
        return None
