from __future__ import annotations

from typing import Dict, Any, Callable, Awaitable, List
from datetime import datetime
import logging

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Setting, User
from app.services.security import get_admin_ids


# One-time appeal capture intent: user_id -> True
_APPEAL_CAPTURE: Dict[int, bool] = {}
logger = logging.getLogger(__name__)


async def _is_banned(tg_id: int) -> bool:
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:BANNED"))
        return bool(row and str(row.value).strip().lower() in {"1", "true"})


async def _get_appeal_status(tg_id: int) -> str:
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:APPEAL_STATUS"))
        return str(row.value).strip().lower() if row and row.value is not None else "none"


async def _set_setting(key: str, value: str) -> None:
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == key))
        if not row:
            session.add(Setting(key=key, value=value))
        else:
            row.value = value
        await session.commit()


async def _ensure_user(tg_id: int) -> None:
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if not u:
            u = User(telegram_id=tg_id, marzban_username=f"tg{tg_id}", status="active", data_limit_bytes=0, balance=0)
            session.add(u)
            await session.commit()


def _appeal_intro_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📨 ارسال درخواست رفع بن", callback_data="appeal:start")]])


class BanGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)
        tg_id = user.id
        # Check banned
        if not await _is_banned(tg_id):
            return await handler(event, data)
        try:
            logger.info("ban_gate: banned user intercepted", extra={"extra": {"tg_id": tg_id}})
        except Exception:
            pass

        # Banned: handle Appeal-only flow
        status = await _get_appeal_status(tg_id)

        # Appeal capture state (keep here for compatibility if handler not wired)
        if _APPEAL_CAPTURE.get(tg_id, False):
            if isinstance(event, Message):
                text = (event.text or "").strip()
                if not text:
                    await event.answer("متن درخواست رفع بن را به‌صورت متنی ارسال کنید.")
                    return None
                try:
                    logger.info("ban_gate: appeal text captured", extra={"extra": {"tg_id": tg_id, "len": len(text)}})
                except Exception:
                    pass
                await _ensure_user(tg_id)
                await _set_setting(f"USER:{tg_id}:APPEAL_TEXT", text)
                await _set_setting(f"USER:{tg_id}:APPEAL_STATUS", "pending")
                await _set_setting(f"USER:{tg_id}:APPEAL_AT", datetime.utcnow().isoformat())
                _APPEAL_CAPTURE.pop(tg_id, None)
                # Notify admins
                try:
                    admins: List[int] = get_admin_ids()
                    for aid in admins:
                        try:
                            await event.bot.send_message(chat_id=aid, text=f"📨 Appeal جدید\n🆔 tg:{tg_id}\nمتن:\n{text}")
                        except Exception:
                            pass
                except Exception:
                    pass
                await event.answer("درخواست شما ثبت شد و در دست بررسی است.")
                return None
            else:
                # ignore non-message when capturing
                return None

        # Pass-through appeal callbacks to routers (dedicated handler processes it)
        if isinstance(event, CallbackQuery):
            cb_data = (event.data or "").strip()
            if cb_data.startswith("appeal:"):
                try:
                    logger.info("ban_gate: callback passthrough", extra={"extra": {"tg_id": tg_id, "data": cb_data}})
                except Exception:
                    pass
                return await handler(event, data)

        # Generic banned notices
        if status == "none":
            # Show appeal button and remove reply keyboard
            try:
                # Remove reply keyboard first (send minimal text to satisfy Telegram)
                try:
                    from aiogram.types import ReplyKeyboardRemove
                    await event.bot.send_message(chat_id=tg_id, text="⛔️", reply_markup=ReplyKeyboardRemove())
                except Exception:
                    pass
                if isinstance(event, Message):
                    try:
                        logger.info("ban_gate: showing appeal intro", extra={"extra": {"tg_id": tg_id}})
                    except Exception:
                        pass
                    await event.answer(
                        "حساب شما در ربات بن شده است. اگر فکر می‌کنید اشتباهی رخ داده، می‌توانید یک‌بار درخواست رفع بن ارسال کنید.",
                        reply_markup=_appeal_intro_kb()
                    )
                elif isinstance(event, CallbackQuery):
                    await event.message.answer(
                        "حساب شما در ربات بن شده است. برای ارسال درخواست رفع بن، از دکمه زیر استفاده کنید.",
                        reply_markup=_appeal_intro_kb()
                    )
                    await event.answer("blocked")
            except Exception:
                pass
            return None
        elif status == "pending":
            try:
                if isinstance(event, Message):
                    await event.answer("درخواست رفع بن شما در دست بررسی است.")
                else:
                    await event.answer("در دست بررسی", show_alert=True)
            except Exception:
                pass
            return None
        elif status == "denied":
            try:
                if isinstance(event, Message):
                    await event.answer("درخواست رفع بن شما رد شده است. امکان استفاده از ربات وجود ندارد.")
                else:
                    await event.answer("درخواست شما رد شده است.", show_alert=True)
            except Exception:
                pass
            return None
        else:
            # accepted but still banned? Show generic error
            try:
                if isinstance(event, Message):
                    await event.answer("حساب شما در وضعیت نامعتبر است. لطفاً بعداً تلاش کنید.")
                else:
                    await event.answer("blocked")
            except Exception:
                pass
            return None
