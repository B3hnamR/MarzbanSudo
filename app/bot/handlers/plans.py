from __future__ import annotations

import logging
from typing import List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Plan, User, Order
from app.scripts.sync_plans import sync_templates_to_plans
from app.utils.username import tg_username


router = Router()

PAGE_SIZE = 5


def _plan_text(p: Plan) -> str:
    if p.data_limit_bytes and p.data_limit_bytes > 0:
        gb = p.data_limit_bytes / (1024 ** 3)
        limit_str = f"{gb:.0f}GB"
    else:
        limit_str = "نامحدود"
    dur_str = f"{p.duration_days}d" if p.duration_days and p.duration_days > 0 else "بدون محدودیت زمانی"
    return f"{p.title} (ID: {p.template_id}) | حجم: {limit_str} | مدت: {dur_str}"


async def _send_plans_page(message: Message, page: int) -> None:
    async with session_scope() as session:
        all_plans = (await session.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.template_id))).scalars().all()
        if not all_plans:
            await message.answer("هیچ پلن�� موجود نیست.")
            return
        total = len(all_plans)
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = max(1, min(page, pages))
        start = (page - 1) * PAGE_SIZE
        subset = all_plans[start:start + PAGE_SIZE]
        lines = ["پلن‌های موجود (صفحه {}/{}):".format(page, pages)]
        buttons = []
        for p in subset:
            lines.append("- " + _plan_text(p))
            buttons.append([InlineKeyboardButton(text=f"خرید {p.template_id}", callback_data=f"plan:buy:{p.template_id}")])
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(text="◀️ قبلی", callback_data=f"plan:page:{page-1}"))
        if page < pages:
            nav.append(InlineKeyboardButton(text="بعدی ▶️", callback_data=f"plan:page:{page+1}"))
        if nav:
            buttons.append(nav)
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("\n".join(lines), reply_markup=kb)


@router.message(Command("plans"))
async def handle_plans(message: Message) -> None:
    await message.answer("در حال دریافت پلن‌ها...")
    try:
        async with session_scope() as session:
            rows = (await session.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.template_id))).scalars().all()
            if not rows:
                await message.answer("هیچ پلنی در پایگاه‌داده ثبت نشده است. در حال همگام‌سازی از Marzban...")
                changed = await sync_templates_to_plans(session)
                if not changed:
                    await message.answer("همگام‌سازی انجام شد اما پلنی یافت نشد. لطفاً در Marzban حداقل یک Template فعال ایجاد کنید.")
                    return
            # send paginated list (page 1)
        await _send_plans_page(message, 1)
    except Exception as e:
        logging.exception("Failed to fetch plans from DB: %s", e)
        await message.answer("خطا در دریافت پلن‌ها از سیستم. لطفاً کمی بعد تلاش کنید.")


@router.callback_query(F.data.startswith("plan:page:"))
async def cb_plan_page(cb: CallbackQuery) -> None:
    try:
        page = int(cb.data.split(":")[2]) if cb.data else 1
    except Exception:
        page = 1
    await _send_plans_page(cb.message, page)
    await cb.answer()


@router.callback_query(F.data.startswith("plan:buy:"))
async def cb_plan_buy(cb: CallbackQuery) -> None:
    try:
        tpl_id = int(cb.data.split(":")[2]) if cb.data else 0
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    if not cb.from_user:
        await cb.answer()
        return
    # Create order directly (same as /buy)
    async with session_scope() as session:
        plan = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
        if not plan:
            await cb.answer("پلن یافت نشد", show_alert=True)
            return
        tg_id = cb.from_user.id
        username = tg_username(tg_id)
        db_user = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalars().first()
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
        order = Order(
            user_id=db_user.id,
            plan_id=plan.id,
            status="pending",
            amount=plan.price or 0,
            currency=plan.currency,
            provider="manual_transfer",
        )
        session.add(order)
        await session.commit()
        await cb.message.answer(
            f"سفارش شما ایجاد شد. شناسه سفارش: #{order.id}\n"
            f"پلن: {plan.title}\n"
            f"مبلغ: {order.amount} {order.currency}\n"
            "برای ثبت رسید، شماره پیگیری/توضیح را با فرمان زیر ارسال کنید:\n"
            f"/attach {order.id} <ref>"
        )
    await cb.answer("ثبت شد")
