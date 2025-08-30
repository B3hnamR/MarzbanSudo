from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot

logger = logging.getLogger(__name__)

_bot_singleton: Optional[Bot] = None
_bot_lock = asyncio.Lock()


async def _get_bot() -> Optional[Bot]:
    global _bot_singleton
    if _bot_singleton is not None:
        return _bot_singleton
    async with _bot_lock:
        if _bot_singleton is not None:
            return _bot_singleton
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            logger.warning("notify: TELEGRAM_BOT_TOKEN missing; notifications disabled")
            return None
        _bot_singleton = Bot(token=token)
        return _bot_singleton


async def notify_user(telegram_id: int, text: str, *, disable_web_page_preview: bool = True) -> bool:
    """Send a direct message to a user. Returns True if sent, False otherwise."""
    bot = await _get_bot()
    if bot is None:
        return False
    try:
        await bot.send_message(chat_id=telegram_id, text=text, disable_web_page_preview=disable_web_page_preview)
        return True
    except Exception as e:
        logger.warning("notify_user failed", extra={"extra": {"telegram_id": telegram_id, "err": str(e)}})
        return False


async def notify_log(text: str, *, disable_web_page_preview: bool = True) -> bool:
    """Send a message to LOG_CHAT_ID if configured. Returns True if sent, False otherwise."""
    bot = await _get_bot()
    if bot is None:
        return False
    raw = os.getenv("LOG_CHAT_ID", "").strip()
    if not raw:
        return False
    try:
        chat_id = int(raw)
    except Exception:
        logger.warning("notify_log: invalid LOG_CHAT_ID: %s", raw)
        return False
    try:
        await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=disable_web_page_preview)
        return True
    except Exception as e:
        logger.warning("notify_log failed", extra={"extra": {"err": str(e)}})
        return False


async def aclose_bot() -> None:
    global _bot_singleton
    if _bot_singleton is not None:
        try:
            await _bot_singleton.session.close()
        finally:
            _bot_singleton = None
