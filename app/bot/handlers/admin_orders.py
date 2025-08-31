from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, update

from app.db.session import session_scope
from app.db.models import Order, User, Plan
from app.services import marzban_ops as ops
from app.services.audit import log_audit
from app.utils.username import tg_username
from app.services.security import has_capability_async, CAP_ORDERS_MODERATE
from app.marzban.client import get_client

router = Router()






def _token_from_subscription_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        return url.rstrip("/").split("/")[-1]
    except Exception:
        return None


@router.message(Command("admin_orders_pending"))
async def admin_orders_pending(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_ORDERS_MODERATE)):
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
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_ORDERS_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        order_id = int(cb.data.split(":")[2]) if cb.data else 0
    except Exception:
        await cb.answer("Invalid order id", show_alert=True)
        return
    token: Optional[str] = None
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
        # Atomically mark as paid only if currently pending
        res = await session.execute(
            update(Order)
            .where(Order.id == order_id, Order.status == "pending")
            .values(status="paid", paid_at=datetime.utcnow())
            .execution_options(synchronize_session=False)
        )
        if (res.rowcount or 0) == 0:
            await cb.answer("Already processed", show_alert=True)
            return
        await log_audit(session, actor="admin", action="order_paid", target_type="order", target_id=order.id, meta=str({"by": cb.from_user.id}))
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
        # Mark provisioned if still paid
        await session.execute(
            update(Order)
            .where(Order.id == order_id, Order.status == "paid")
            .values(status="provisioned", provisioned_at=datetime.utcnow())
            .execution_options(synchronize_session=False)
        )
        await log_audit(session, actor="system", action="order_provisioned", target_type="order", target_id=order.id, meta=str({"user": user.id, "plan": plan.id}))
        await session.commit()
    # Notify user with full delivery: summary, direct configs, QR, manage buttons
    try:
        sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
        summary_lines = [
            "✅ سفارش شما تایید و سرویس فعال شد.",
            f"🧩 پلن: {plan.title}",
        ]
        if token and sub_domain:
            summary_lines += [
                f"🔗 لینک اشتراک: https://{sub_domain}/sub4me/{token}/",
                f"🛰️ v2ray: https://{sub_domain}/sub4me/{token}/v2ray",
                f"🧰 JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json",
            ]
        await cb.message.bot.send_message(chat_id=user.telegram_id, text="\n".join(summary_lines))
        # Fetch latest user info for direct configs
        links = []
        sub_url = ""
        try:
            client = await get_client()
            info = await client.get_user(user.marzban_username or tg_username(user.telegram_id))
            links = info.get("links") or []
            sub_url = info.get("subscription_url") or ""
        except Exception:
            links = []
            sub_url = ""
        finally:
            try:
                await client.aclose()  # type: ignore
            except Exception:
                pass
        # Inline manage keyboard
        manage_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 مدیریت اکانت", callback_data="acct:refresh"), InlineKeyboardButton(text="📋 کپی همه", callback_data="acct:copyall")]])
        # Send text configs in chunks
        if links:
            chunk = []
            size = 0
            for ln in links:
                s = str(ln).strip()
                if not s:
                    continue
                entry = ("\n\n" if chunk else "") + s
                if size + len(entry) > 3500:
                    await cb.message.bot.send_message(chat_id=user.telegram_id, text="\n\n".join(chunk))
                    chunk = [s]
                    size = len(s)
                    continue
                chunk.append(s)
                size += len(entry)
            if chunk:
                await cb.message.bot.send_message(chat_id=user.telegram_id, text="\n\n".join(chunk), reply_markup=manage_kb)
        else:
            await cb.message.bot.send_message(chat_id=user.telegram_id, text="برای مدیریت و دریافت کانفیگ‌ها از دکمه زیر استفاده کنید.", reply_markup=manage_kb)
        # Send QR
        disp_url = ""
        if sub_domain and token:
            disp_url = f"https://{sub_domain}/sub4me/{token}/"
        elif sub_url:
            disp_url = sub_url
        if disp_url:
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={disp_url}"
            try:
                await cb.message.bot.send_photo(chat_id=user.telegram_id, photo=qr_url, caption="🔳 QR اشتراک")
            except Exception:
                await cb.message.bot.send_message(chat_id=user.telegram_id, text=disp_url)
    except Exception:
        pass
    await cb.message.edit_text(cb.message.text + "\n\nApproved ✅")
    await cb.answer("Approved")


@router.callback_query(F.data.startswith("ord:reject:"))
async def cb_reject_order(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_ORDERS_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        order_id = int(cb.data.split(":")[2]) if cb.data else 0
    except Exception:
        await cb.answer("Invalid order id", show_alert=True)
        return
    async with session_scope() as session:
        # Reject only if pending
        res = await session.execute(
            update(Order)
            .where(Order.id == order_id, Order.status == "pending")
            .values(status="failed", updated_at=datetime.utcnow())
            .execution_options(synchronize_session=False)
        )
        if (res.rowcount or 0) == 0:
            await cb.answer("Already processed", show_alert=True)
            return
        await log_audit(session, actor="admin", action="order_rejected", target_type="order", target_id=order_id, meta=str({"by": cb.from_user.id}))
        await session.commit()
    await cb.message.edit_text(cb.message.text + "\n\nRejected ❌")
    await cb.answer("Rejected")
