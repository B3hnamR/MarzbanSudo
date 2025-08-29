from __future__ import annotations

import decimal
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import User, Plan, Order
from app.utils.username import tg_username
from app.services.audit import log_audit

router = Router()


@router.message(Command("orders"))
async def handle_orders(message: Message) -> None:
    if not message.from_user:
        return
    tg_id = message.from_user.id
    async with session_scope() as session:
        db_user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if not db_user:
            await message.answer("سفارشی ثبت نشده است.")
            return
        stmt = (
            select(Order, Plan)
            .join(Plan, Order.plan_id == Plan.id)
            .where(Order.user_id == db_user.id)
            .order_by(Order.created_at.desc())
            .limit(10)
        )
        rows = (await session.execute(stmt)).all()
        if not rows:
            await message.answer("سفارشی ثبت نشده است.")
            return
        lines = []
        for o, p in rows:
            amount = f"{o.amount} {o.currency}" if o.amount is not None else "-"
            lines.append(f"- #{o.id} | {o.status} | {p.title} | {amount} | {o.created_at}")
        await message.answer("آخرین سفارش‌ها:\n" + "\n".join(lines))
        # نمایش دکمه Attach/Replace برای سفارش‌های در انتظار
        for o, p in rows:
            if o.status == "pending":
                has_receipt = bool(o.provider_ref or o.receipt_file_path)
                btn_text = "Replace رسید" if has_receipt else "Attach رسید"
                cb_data = (
                    f"ord:attach:replace:{o.id}" if has_receipt else f"ord:attach:{o.id}"
                )
                extra = []
                if o.provider_ref:
                    extra.append(f"ref={o.provider_ref}")
                if o.receipt_file_path:
                    extra.append("file=✓")
                suffix = (" (" + ", ".join(extra) + ")") if extra else ""
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text=btn_text, callback_data=cb_data)]]
                )
                await message.answer(
                    f"Order #{o.id} | {p.title} | status: {o.status}{suffix}",
                    reply_markup=kb,
                )


@router.message(Command("buy"))
async def handle_buy(message: Message) -> None:
    """Create a pending order for a given plan template id.
    Usage: /buy <TEMPLATE_ID>
    """
    if not message.from_user or not message.text:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("فرمت: /buy <TEMPLATE_ID>")
        return
    try:
        tpl_id = int(parts[1])
    except ValueError:
        await message.answer("شناسه پلن نامعتبر است.")
        return

    async with session_scope() as session:
        plan = await session.scalar(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))
        if not plan:
            await message.answer("پلن یافت نشد یا غیرفعال است.")
            return
        tg_id = message.from_user.id
        username = tg_username(tg_id)
        db_user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if not db_user:
            db_user = User(
                telegram_id=tg_id,
                marzban_username=username,
                subscription_token=None,
                status="active",
                data_limit_bytes=0,
            )
            session.add(db_user)
            await session.flush()
        # Create order
        amount = decimal.Decimal(str(plan.price)) if plan.price is not None else decimal.Decimal("0")
        order = Order(
            user_id=db_user.id,
            plan_id=plan.id,
            status="pending",
            amount=amount,
            currency=plan.currency,
            provider="manual_transfer",
        )
        session.add(order)
        await log_audit(session, actor="user", action="order_created", target_type="order", target_id=order.id, meta=str({"plan": plan.id}))
        await session.commit()
        await message.answer(
            f"سفارش شما ایجاد شد. شناسه سفارش: #{order.id}\n"
            f"پلن: {plan.title}\n"
            f"مبلغ: {amount} {plan.currency}\n"
            "برای ثبت رسید، یکی از روش‌های زیر را انجام دهید:\n"
            f"- ارسال متن: /attach {order.id} <ref>\n"
            f"- ارسال عکس/فایل با کپشن: attach {order.id} <ref>"
        )


@router.message(F.text.startswith("/attach "))
async def handle_attach(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("فرمت: /attach <ORDER_ID> <ref>")
        return
    try:
        order_id = int(parts[1])
    except ValueError:
        await message.answer("شناسه سفارش نامعتبر است.")
        return
    ref = parts[2].strip()
    tg_id = message.from_user.id
    async with session_scope() as session:
        stmt = (
            select(Order, User, Plan)
            .join(User, Order.user_id == User.id)
            .join(Plan, Order.plan_id == Plan.id)
            .where(Order.id == order_id, User.telegram_id == tg_id)
        )
        row = (await session.execute(stmt)).first()
        if not row:
            await message.answer("سفارش یافت نشد.")
            return
        order, user, plan = row
        if order.provider_ref or order.receipt_file_path:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="تایید جایگزینی رسید", callback_data=f"ord:attach:confirm_replace:{order.id}")]]
            )
            await message.answer("برای این سفارش قبلاً رسید ثبت شده است. برای جایگزینی، دک��ه زیر را بزنید.", reply_markup=kb)
            return
        order.provider_ref = ref
        order.updated_at = datetime.utcnow()
        await log_audit(session, actor="user", action="order_attach_ref", target_type="order", target_id=order.id, meta=str({"ref": ref}))
        await session.commit()
        await message.answer("رسید ثبت شد و در صف بررسی ادمین قرار گرفت.")


@router.callback_query(F.data.startswith("ord:attach:replace:"))
async def cb_order_attach_replace(cb: CallbackQuery) -> None:
    try:
        order_id = int(cb.data.split(":")[-1]) if cb.data else 0
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="تایید جایگزینی", callback_data=f"ord:attach:confirm_replace:{order_id}")]]
    )
    await cb.message.answer("برای این سفارش رسید قبلاً ثبت شده است. با تایید جایگزینی، رسید قبلی پاک می‌شود و می‌توانید مجدد ارسال کنید.", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("ord:attach:confirm_replace:"))
async def cb_order_attach_confirm_replace(cb: CallbackQuery) -> None:
    try:
        order_id = int(cb.data.split(":")[-1]) if cb.data else 0
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    if not cb.from_user:
        await cb.answer()
        return
    tg_id = cb.from_user.id
    async with session_scope() as session:
        row = (
            await session.execute(
                select(Order, User)
                .join(User, Order.user_id == User.id)
                .where(Order.id == order_id, User.telegram_id == tg_id)
            )
        ).first()
        if not row:
            await cb.answer("Order not found", show_alert=True)
            return
        order, user = row
        order.provider_ref = None
        order.receipt_file_path = None
        order.updated_at = datetime.utcnow()
        await log_audit(session, actor="user", action="order_attach_clear", target_type="order", target_id=order.id)
        await session.commit()
    await cb.message.answer(
        "رسید قبلی حذف شد. برای ثبت رسید جدید یکی از روش‌های زیر را انجام دهید:\n"
        f"- ارسال متن: /attach {order_id} <ref>\n"
        f"- ارسال عکس/فایل با کپشن: attach {order_id} <ref>"
    )
    await cb.answer("Cleared")


@router.callback_query(F.data.startswith("ord:attach:") & (~F.data.contains(":replace:")) & (~F.data.contains(":confirm_replace:")))
async def cb_order_attach(cb: CallbackQuery) -> None:
    try:
        order_id = int(cb.data.split(":")[2]) if cb.data else 0
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    await cb.message.answer(
        "برای ثبت رسید یکی از روش‌های زیر را انجام دهید:\n"
        f"- ارسال متن: /attach {order_id} <ref>\n"
        f"- ارسال عکس/فایل با کپشن: attach {order_id} <ref>"
    )
    await cb.answer()


@router.message(F.caption.startswith("attach ") & (F.photo | F.document))
async def handle_attach_media(message: Message) -> None:
    if not message.from_user or not message.caption:
        return
    parts = message.caption.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("فرمت کپشن: attach <ORDER_ID> <ref>")
        return
    try:
        order_id = int(parts[1])
    except ValueError:
        await message.answer("شناسه سفارش نامعتبر است.")
        return
    ref = parts[2].strip()
    # extract file_id
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    tg_id = message.from_user.id
    async with session_scope() as session:
        stmt = (
            select(Order, User, Plan)
            .join(User, Order.user_id == User.id)
            .join(Plan, Order.plan_id == Plan.id)
            .where(Order.id == order_id, User.telegram_id == tg_id)
        )
        row = (await session.execute(stmt)).first()
        if not row:
            await message.answer("سفارش یافت نشد.")
            return
        order, user, plan = row
        if order.provider_ref or order.receipt_file_path:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="تایید جایگزینی رسید", callback_data=f"ord:attach:confirm_replace:{order.id}")]]
            )
            await message.answer("برای این سفارش قبلاً رسید ثبت شده است. برای جایگزینی، دکمه زیر را بزنید.", reply_markup=kb)
            return
        order.provider_ref = ref
        if file_id:
            order.receipt_file_path = file_id
        order.updated_at = datetime.utcnow()
        await log_audit(session, actor="user", action="order_attach_media", target_type="order", target_id=order.id, meta=str({"file_id": file_id}))
        await session.commit()
        await message.answer("رسید ثبت شد و در صف بررسی ادمین قرار گرفت.")
