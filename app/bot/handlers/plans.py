from __future__ import annotations

import logging
import os
from datetime import datetime
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
    price_irr = int(p.price or 0)
    price_tmn = price_irr // 10
    price_str = f"{price_tmn:,} تومان" if price_irr > 0 else "قیمت‌گذاری نشده"
    return f"{p.title} (ID: {p.template_id}) | حجم: {limit_str} | مدت: {dur_str} | قیمت: {price_str}"


async def _send_plans_page(message: Message, page: int) -> None:
    async with session_scope() as session:
        all_plans = (await session.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.template_id))).scalars().all()
        if not all_plans:
            await message.answer("هیچ پلنی موجود نیست.")
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
            price_irr = int(p.price or 0)
            label_price = f" - {price_irr//10:,} تومان" if price_irr > 0 else " - قیمت‌گذاری نشده"
            btn_text = f"خرید {p.title}{label_price}"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"plan:buy:{p.template_id}")])
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
                await message.answer("هیچ پلن فعالی در دسترس نیست.")
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
    # Wallet-aware purchase
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
                balance=0,
            )
            session.add(db_user)
            await session.flush()
        price_irr = int(plan.price or 0)
        if price_irr <= 0:
            await cb.message.answer("قیمت این پلن هنوز تنظیم نشده است. لطفاً از ادمین بخواهید قیمت را مشخص کند.")
            await cb.answer("Price not set", show_alert=True)
            return
        balance_irr = int(db_user.balance or 0)
        if balance_irr < price_irr:
            await cb.message.answer(
                f"موجودی کافی نیست.\n"
                f"قیمت پلن: {price_irr//10:,} تومان\n"
                f"موجودی شما: {balance_irr//10:,} تومان\n"
                "از دکمه 💳 کیف پول برای شارژ استفاده کنید."
            )
            await cb.answer("Insufficient balance", show_alert=False)
            return
        # Enough balance → create order and auto-approve/provision
        from app.services import marzban_ops as ops
        from app.utils.username import tg_username as _tg
        try:
            # Create order record as paid/provisioned for traceability
            order = Order(
                user_id=db_user.id,
                plan_id=plan.id,
                status="paid",
                amount=price_irr,
                currency=plan.currency,
                provider="wallet",
            )
            session.add(order)
            # Deduct balance
            db_user.balance = balance_irr - price_irr
            await session.flush()
            # Provision
            info = await ops.provision_for_plan(db_user.marzban_username or _tg(tg_id), plan)
            order.status = "provisioned"
            order.paid_at = order.updated_at = order.provisioned_at = datetime.utcnow()
            await session.commit()
        except Exception:
            await cb.message.answer("خطا در فعال‌سازی پلن. لطفاً مجدداً تلاش کنید یا به ادمین اطلاع دهید.")
            await cb.answer()
            return
        # Notify
        try:
            sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
            token = None
            if isinstance(info, dict):
                sub_url = info.get("subscription_url", "")
                token = sub_url.rstrip("/").split("/")[-1] if sub_url else None
                if token:
                    db_user.subscription_token = token
            lines = [
                "خرید با موفقیت از کیف پول انجام شد.",
                f"پلن: {plan.title}",
                f"مبلغ کسرشده: {price_irr//10:,} تومان",
                f"موجودی جدید: {int((db_user.balance or 0))//10:,} تومان",
            ]
            if token and sub_domain:
                lines += [
                    f"لینک اشتراک: https://{sub_domain}/sub4me/{token}/",
                    f"v2ray: https://{sub_domain}/sub4me/{token}/v2ray",
                    f"JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json",
                ]
            await cb.message.answer("\n".join(lines))
        except Exception:
            pass
        await cb.answer("Purchased")
