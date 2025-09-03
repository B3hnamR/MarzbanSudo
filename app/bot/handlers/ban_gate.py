from __future__ import annotations

from typing import Dict, List
from datetime import datetime

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import SkipHandler
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Setting, User
from app.services.security import get_admin_ids

router = Router()

# One-time appeal capture intent: user_id -> True
_APPEAL_CAPTURE: Dict[int, bool] = {}


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
    # Make sure a DB user exists (appeal flow may be first interaction)
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if not u:
            u = User(telegram_id=tg_id, marzban_username=f"tg{tg_id}", status="active", data_limit_bytes=0, balance=0)
            session.add(u)
            await session.commit()


def _appeal_intro_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📨 ارسال درخواست رفع بن", callback_data="appeal:start")]])


@router.message()
async def ban_gate_messages(message: Message) -> None:
    if not message.from_user:
        return
    tg_id = message.from_user.id
    if not await _is_banned(tg_id):
        raise SkipHandler
    # Banned: block all except appeal flow
    status = await _get_appeal_status(tg_id)
    if _APPEAL_CAPTURE.get(tg_id, False):
        # capture one message
        text = (message.text or "").strip()
        if not text:
            await message.answer("متن درخواست رفع بن را به‌صورت متنی ارسال کنید.")
            return
        await _ensure_user(tg_id)
        await _set_setting(f"USER:{tg_id}:APPEAL_TEXT", text)
        await _set_setting(f"USER:{tg_id}:APPEAL_STATUS", "pending")
        await _set_setting(f"USER:{tg_id}:APPEAL_AT", datetime.utcnow().isoformat())
        _APPEAL_CAPTURE.pop(tg_id, None)
        # notify admins
        try:
            admins: List[int] = get_admin_ids()
            for aid in admins:
                try:
                    await message.bot.send_message(chat_id=aid, text=f"📨 Appeal جدید\n🆔 tg:{tg_id}\nمتن:\n{text}")
                except Exception:
                    pass
        except Exception:
            pass
        await message.answer("درخواست شما ثبت شد و در دست بررسی است.")
        return

    if status == "none":
        await message.answer(
            "حساب شما در ربات بن شده است. اگر فکر می‌کنید اشتباهی رخ داده، می‌توانید یک‌بار درخواست رفع بن ارسال کنید.",
            reply_markup=_appeal_intro_kb()
        )
    elif status == "pending":
        await message.answer("درخواست رفع بن شما در دست بررسی است.")
    elif status == "denied":
        await message.answer("درخواست رفع بن شما رد شده است. امکان استفاده از ربات وجود ندارد.")
    else:
        await message.answer("حساب شما در وضعیت نامعتبر است. لطفاً بعداً تلاش کنید.")
    return


@router.callback_query()
async def ban_gate_callbacks(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    tg_id = cb.from_user.id
    if not await _is_banned(tg_id):
        raise SkipHandler
    data = cb.data or ""
    status = await _get_appeal_status(tg_id)

    if data == "appeal:start" and status == "none":
        _APPEAL_CAPTURE[tg_id] = True
        await cb.message.answer("لطفاً توضیح خود را درباره رفع بن در یک پیام متنی ارسال کنید (تنها یک‌بار).")
        await cb.answer()
        return

    # otherwise block
    if status == "none":
        try:
            await cb.message.answer(
                "حساب شما در ربات بن شده است. برای ارسال درخواست رفع بن، از دکمه زیر استفاده کنید.",
                reply_markup=_appeal_intro_kb()
            )
        except Exception:
            pass
        await cb.answer("blocked")
    elif status == "pending":
        await cb.answer("در دست بررسی", show_alert=True)
    elif status == "denied":
        await cb.answer("درخواست شما رد شده است.", show_alert=True)
    else:
        await cb.answer("blocked")
    return
