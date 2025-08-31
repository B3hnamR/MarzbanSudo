from __future__ import annotations

import logging
import os
from decimal import Decimal
from datetime import datetime
from typing import List
from app.marzban.client import get_client

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select
from app.db.models import Setting

from app.db.session import session_scope
from app.db.models import Plan, User, Order
from app.scripts.sync_plans import sync_templates_to_plans
from app.utils.username import tg_username


router = Router()

PAGE_SIZE = 5


def _plan_text(p: Plan) -> str:
    # Human-friendly plan block with emojis
    if p.data_limit_bytes and p.data_limit_bytes > 0:
        gb = p.data_limit_bytes / (1024 ** 3)
        gb_label = f"{gb:.0f}GB"
    else:
        gb_label = "نامحدود"
    if p.duration_days and p.duration_days > 0:
        dur_label = f"{p.duration_days} روز"
    else:
        dur_label = "بدون محدودیت"
    price_irr = Decimal(str(p.price or 0))
    price_tmn = int(price_irr / Decimal("10")) if price_irr > 0 else 0
    price_label = f"{price_tmn:,} تومان" if price_irr > 0 else "قیمت‌گذاری نشده"
    lines = [
        f"#{p.template_id} — {p.title}",
        f"  ⏳ مدت: {dur_label} | 📦 حجم: {gb_label}",
        f"  💵 قیمت: {price_label}",
    ]
    return "\n".join(lines)


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
        lines = ["🛍️ پلن‌های موجود • صفحه {}/{}".format(page, pages)]
        buttons = []
        for p in subset:
            lines.append(_plan_text(p))
            price_irr = Decimal(str(p.price or 0))
            btn_text = (
                f"🛒 خرید {p.title} — {int(price_irr/Decimal('10')):,} تومان" if price_irr > 0 else f"🛒 خرید {p.title}"
            )
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
    await message.answer("⏳ در حال دریافت پلن‌ها...")
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
    # Gates: channel + phone; only show confirm if gates pass
    channel = os.getenv("REQUIRED_CHANNEL", "").strip()
    admin_ids_env = os.getenv("TELEGRAM_ADMIN_IDS", "")
    is_admin_user = False
    try:
        is_admin_user = cb.from_user.id in {int(x.strip()) for x in admin_ids_env.split(',') if x.strip().isdigit()}
    except Exception:
        is_admin_user = False
    if channel and not is_admin_user:
        try:
            member = await cb.message.bot.get_chat_member(chat_id=channel, user_id=cb.from_user.id)
            status = getattr(member, "status", None)
            if status not in {"member", "creator", "administrator"}:
                join_url = f"https://t.me/{channel.lstrip('@')}"
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 عضویت در کانال", url=join_url)],
                    [InlineKeyboardButton(text="من عضو شدم ✅", callback_data="chk:chan")],
                ])
                await cb.message.answer("برای ادامه خرید، ابتدا در کانال عضو شوید و سپس دوباره تلاش کنید.", reply_markup=kb)
                await cb.answer()
                return
        except Exception:
            pass
    # Stage 2: Phone verification gate
    try:
        pv_enabled = False
        async with session_scope() as session:
            from sqlalchemy import select as sa_select
            row = await session.scalar(sa_select(Setting).where(Setting.key == "PHONE_VERIFICATION_ENABLED"))
            if row and str(row.value).strip() in {"1", "true", "True"}:
                pv_enabled = True
            if pv_enabled and not is_admin_user:
                row_v = await session.scalar(sa_select(Setting).where(Setting.key == f"USER:{cb.from_user.id}:PHONE_VERIFIED_AT"))
                verified = bool(row_v and str(row_v.value).strip())
                if not verified:
                    rk = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 ارسال شماره من", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
                    await cb.message.answer("برای ادامه خرید، لطفاً شماره تلگرام خود را ارسال کنید.", reply_markup=rk)
                    await cb.answer()
                    return
    except Exception:
        pass
    # Show confirmation
    async with session_scope() as session:
        plan = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
    if not plan:
        await cb.answer("پلن یافت نشد", show_alert=True)
        return
    price_irr = Decimal(str(plan.price or 0))
    tmn = int(price_irr/Decimal('10')) if price_irr > 0 else 0
    text = f"آیا از خرید پلن زیر اطمینان دارید؟\n\n🧩 {plan.title}\n💵 مبلغ: {tmn:,} تومان"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تایید ✅", callback_data=f"plan:confirm:{tpl_id}"), InlineKeyboardButton(text="انصراف ❌", callback_data="plan:cancel")]])
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("plan:confirm:"))
async def cb_plan_confirm(cb: CallbackQuery) -> None:
    try:
        tpl_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    # Re-run gates quickly (in case state changed)
    channel = os.getenv("REQUIRED_CHANNEL", "").strip()
    admin_ids_env = os.getenv("TELEGRAM_ADMIN_IDS", "")
    is_admin_user = False
    try:
        is_admin_user = cb.from_user and (cb.from_user.id in {int(x.strip()) for x in admin_ids_env.split(',') if x.strip().isdigit()})
    except Exception:
        is_admin_user = False
    if channel and not is_admin_user:
        try:
            member = await cb.message.bot.get_chat_member(chat_id=channel, user_id=cb.from_user.id)
            if getattr(member, "status", None) not in {"member", "creator", "administrator"}:
                await cb.answer("ابتدا در کا��ال عضو شوید.", show_alert=True)
                return
        except Exception:
            pass
    try:
        from sqlalchemy import select as sa_select
        async with session_scope() as session:
            row = await session.scalar(sa_select(Setting).where(Setting.key == "PHONE_VERIFICATION_ENABLED"))
            if row and str(row.value).strip() in {"1", "true", "True"} and not is_admin_user:
                row_v = await session.scalar(sa_select(Setting).where(Setting.key == f"USER:{cb.from_user.id}:PHONE_VERIFIED_AT"))
                if not (row_v and str(row_v.value).strip()):
                    await cb.answer("ابتدا شماره خود را تایید کنید.", show_alert=True)
                    return
    except Exception:
        pass
    # Proceed with purchase
    await _do_purchase(cb, tpl_id)


@router.callback_query(F.data == "plan:cancel")
async def cb_plan_cancel(cb: CallbackQuery) -> None:
    await cb.answer("انصراف شد")
    try:
        await cb.message.edit_text("خرید لغو شد ❌")
    except Exception:
        pass


async def _do_purchase(cb: CallbackQuery, tpl_id: int) -> None:
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
        price_irr = Decimal(str(plan.price or 0))
        if price_irr <= 0:
            await cb.message.answer("قیمت این پلن هنوز تنظیم نشده است. لطفاً از ادمین بخواهید قیمت را مشخص کند.")
            await cb.answer("Price not set", show_alert=True)
            return
        balance_irr = Decimal(str(db_user.balance or 0))
        if balance_irr < price_irr:
            await cb.message.answer(
                f"موجودی کافی نیست.\n"
                f"قیمت پلن: {int(price_irr/Decimal('10')):,} تومان\n"
                f"موجودی شما: {int(balance_irr/Decimal('10')):,} تومان\n"
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
            # Extract and persist subscription token if available
            token = None
            if isinstance(info, dict):
                sub_url = info.get("subscription_url", "")
                token = sub_url.rstrip("/").split("/")[-1] if sub_url else None
                if token:
                    db_user.subscription_token = token
            # Commit all changes atomically
            await session.commit()
        except Exception:
            await cb.message.answer("خطا در فعال‌سازی پلن. لطفاً مجدداً تلاش کنید یا به ادمین اطلاع دهید.")
            await cb.answer()
            return
        # Notify
        try:
            sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
            lines = [
                "✅ خرید با موفقیت از کیف پول انجام شد.",
                f"🧩 پلن: {plan.title}",
                f"💳 مبلغ کسرشده: {int(price_irr/Decimal('10')):,} تومان",
                f"👛 موجودی جدید: {int(Decimal(str(db_user.balance or 0))/Decimal('10')):,} تومان",
            ]
            if token and sub_domain:
                lines += [
                    f"🔗 لینک اشتراک: https://{sub_domain}/sub4me/{token}/",
                    f"🛰️ v2ray: https://{sub_domain}/sub4me/{token}/v2ray",
                    f"🧰 JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json",
                ]
            await cb.message.answer("\n".join(lines))
        except Exception:
            pass
        # Post-purchase delivery: direct configs, copy-all, QR, manage account
        try:
            client = await get_client()
            info2 = await client.get_user(db_user.marzban_username or username)
        except Exception:
            info2 = {}
        finally:
            try:
                await client.aclose()
            except Exception:
                pass
        links = info2.get("links") or []
        sub_url = info2.get("subscription_url") or ""
        token2 = token or (sub_url.rstrip("/").split("/")[-1] if sub_url else None)
        # Manage/Copy buttons
        manage_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 مدیریت اکانت", callback_data="acct:refresh"), InlineKeyboardButton(text="📋 کپی همه", callback_data="acct:copyall")]])
        # Send text configs (chunked, with blank lines)
        if links:
            chunk: List[str] = []
            size = 0
            for ln in links:
                s = str(ln).strip()
                if not s:
                    continue
                entry = ("\n\n" if chunk else "") + s
                if size + len(entry) > 3500:
                    await cb.message.answer("\n\n".join(chunk))
                    chunk = [s]
                    size = len(s)
                    continue
                chunk.append(s)
                size += len(entry)
            if chunk:
                await cb.message.answer("\n\n".join(chunk), reply_markup=manage_kb)
        else:
            # If no direct configs, still show manage button for user to fetch
            await cb.message.answer("برای مدیریت و دریافت کانفیگ‌ها از دکمه زیر استفاده کنید.", reply_markup=manage_kb)
        # Send QR for subscription
        disp_url = ""
        if sub_domain and token2:
            disp_url = f"https://{sub_domain}/sub4me/{token2}/"
        elif sub_url:
            disp_url = sub_url
        if disp_url:
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={disp_url}"
            try:
                await cb.message.answer_photo(qr_url, caption="🔳 QR اشتراک")
            except Exception:
                await cb.message.answer(disp_url)
        await cb.answer("Purchased")
