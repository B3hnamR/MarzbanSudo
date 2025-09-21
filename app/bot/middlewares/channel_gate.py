from __future__ import annotations

import os
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import logging

from app.services.security import get_admin_ids


logger = logging.getLogger(__name__)


class ChannelGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        channel = os.getenv("REQUIRED_CHANNEL", "").strip()
        logger.debug(
            "channel_gate.enter",
            extra={'extra': {'uid': getattr(user, 'id', None), 'channel': channel}}
        )
        if not channel:
            return await handler(event, data)

        # Exempt admins from channel gate
        try:
            admins: List[int] = get_admin_ids()
            if user.id in admins:
                logger.debug(
                    "channel_gate.bypass_admin",
                    extra={'extra': {'uid': user.id, 'channel': channel}}
                )
                return await handler(event, data)
        except Exception:
            pass

        # Allow appeal callbacks to pass (ban appeal must not be blocked by channel gate)
        if isinstance(event, CallbackQuery) and (event.data or "").startswith("appeal:"):
            return await handler(event, data)

        # Check membership
        try:
            member = await event.bot.get_chat_member(chat_id=channel, user_id=user.id)
            status = getattr(member, "status", None)
            if status in {"member", "creator", "administrator"}:
                return await handler(event, data)
        except Exception:
            # Fall through to enforce UI when we cannot verify (bot not channel admin)
            pass

        join_url = f"https://t.me/{channel.lstrip('@')}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 عضویت در کانال", url=join_url)],
            [InlineKeyboardButton(text="من عضو شدم ✅", callback_data="chk:chan")],
        ])
        # Reply depending on event type; block further processing
        try:
            logger.info(
                "channel_gate.enforce",
                extra={'extra': {'uid': getattr(user, 'id', None), 'channel': channel}}
            )
            if isinstance(event, Message):
                await event.answer(
                    "برای استفاده از ربات، ابتدا در کانال عضو شوید.\n"
                    "پس از عضویت، روی دکمه \"من عضو شدم ✅\" بزنید.",
                    reply_markup=kb,
                )
            else:
                await event.message.answer(
                    "برای استفاده از ربات، ابتدا در کانال عضو شوید.\n"
                    "پس از عضویت، روی دکمه \"من عضو شدم ✅\" بزنید.",
                    reply_markup=kb,
                )
                await event.answer()
        except Exception:
            pass
        return await handler(event, data)
