from __future__ import annotations

import decimal
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import User, Plan, Order
from app.utils.username import tg_username

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
        await session.commit()
        await message.answer(
            f"سفارش شما ایجاد شد. شناسه سفارش: #{order.id}\n"
            f"پلن: {plan.title}\n"
            f"مبلغ: {amount} {plan.currency}\n"
            "لطفاً رسید پرداخت را برای ادمین ارسال کنید تا تایید و سرویس شما آماده شود."
        )
