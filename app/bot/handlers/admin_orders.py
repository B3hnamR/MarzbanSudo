from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Order, User, Plan
from app.services import marzban_ops as ops
from app.services.audit import log_audit
from app.utils.username import tg_username

router = Router()


def _is_admin(message: Message) -> bool:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "").strip()
    ids = {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
    return bool(message.from_user and message.from_user.id in ids)


def _is_admin_uid(uid: int | None) -> bool:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "").strip()
    ids = {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
    return bool(uid and uid in ids)


def _token_from_subscription_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        return url.rstrip("/").split("/")[-1]
    except Exception:
        return None


@router.message(Command("admin_orders_pending"))
async def admin_orders_pending(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    async with session_scope() as session:
        stmt = (
            select(Order, User, Plan)
            .join(User, Order.user_id == User.id)
            .join(Plan, Order.plan_id == Plan.id)
            .where(Order.status == "pending")
            .order_by(Order.created_at.asc())
            .limit(20)
        )
        rows = (await session.execute(stmt)).all()
        if not rows:
            await message.answer("سفارشی برای بررسی موجود نیست.")
            return
        for o, u, p in rows:
            extra = []
            if o.provider_ref:
                extra.append(f"ref={o.provider_ref}")
            if o.receipt_file_path:
                extra.append("file=✓")
            extra_str = f" | {' '.join(extra)}" if extra else ""
            text = (
                f"Order #{o.id} | {o.status}{extra_str}\n"
                f"User: {u.marzban_username} (tg:{u.telegram_id})\n"
                f"Plan: {p.title} | Amount: {o.amount} {o.currency}\n"
                f"Ref: {o.provider_ref or '-'} | Created: {o.created_at}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Approve ✅", callback_data=f"ord:approve:{o.id}"),
                    InlineKeyboardButton(text="Reject ❌", callback_data=f"ord:reject:{o.id}"),
                ]
            ])
            await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("ord:approve:"))
async def cb_approve_order(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    if not _is_admin_uid(cb.from_user.id):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        order_id = int(cb.data.split(":")[2]) if cb.data else 0
    except Exception:
        await cb.answer("Invalid order id", show_alert=True)
        return
    async with session_scope() as session:
        row = (
            await session.execute(
                select(Order, User, Plan)
                .join(User, Order.user_id == User.id)
                .join(Plan, Order.plan_id == Plan.id)
                .where(Order.id == order_id)
            )
        ).first()
        if not row:
            await cb.answer("Order not found", show_alert=True)
            return
        order, user, plan = row
        # Idempotency guard
        if order.status in ("paid", "provisioned"):
            await cb.answer("Already processed", show_alert=True)
            return
        # Mark as paid
        order.status = "paid"
        order.paid_at = datetime.utcnow()
        await log_audit(session, actor="admin", action="order_paid", target_type="order", target_id=order.id, meta=str({"by": cb.from_user.id if cb.from_user else None}))
        await session.flush()
        # Provision in Marzban (UI-safe)
        username = user.marzban_username or tg_username(user.telegram_id)
        try:
            info = await ops.provision_for_plan(username, plan)
        except Exception:
            await cb.answer("Provision failed", show_alert=True)
            return
        # Persist token if available
        sub_url = info.get("subscription_url", "") if isinstance(info, dict) else ""
        token = _token_from_subscription_url(sub_url)
        if token:
            user.subscription_token = token
        # Mark provisioned
        order.status = "provisioned"
        order.provisioned_at = datetime.utcnow()
        await log_audit(session, actor="system", action="order_provisioned", target_type="order", target_id=order.id, meta=str({"user": user.id, "plan": plan.id}))
        await session.commit()
    # Notify user with links
    try:
        lines = ["سفارش شما تایید و سرویس فعال شد."]
        sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
        if token and sub_domain:
            lines += [
                f"لینک اشتراک: https://{sub_domain}/sub4me/{token}/",
                f"v2ray: https://{sub_domain}/sub4me/{token}/v2ray",
                f"JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json",
            ]
        await cb.message.bot.send_message(chat_id=user.telegram_id, text="\n".join(lines))
    except Exception:
        pass
    await cb.message.edit_text(cb.message.text + "\n\nApproved ✅")
    await cb.answer("Approved")


@router.callback_query(F.data.startswith("ord:reject:"))
async def cb_reject_order(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    if not _is_admin_uid(cb.from_user.id):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        order_id = int(cb.data.split(":")[2]) if cb.data else 0
    except Exception:
        await cb.answer("Invalid order id", show_alert=True)
        return
    async with session_scope() as session:
        order = await session.scalar(select(Order).where(Order.id == order_id))
        if not order:
            await cb.answer("Order not found", show_alert=True)
            return
        if order.status in ("failed", "provisioned"):
            await cb.answer("Already processed", show_alert=True)
            return
        order.status = "failed"
        order.updated_at = datetime.utcnow()
        await log_audit(session, actor="admin", action="order_rejected", target_type="order", target_id=order.id, meta=str({"by": cb.from_user.id if cb.from_user else None}))
        await session.commit()
    await cb.message.edit_text(cb.message.text + "\n\nRejected ❌")
    await cb.answer("Rejected")
