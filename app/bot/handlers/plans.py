from __future__ import annotations

import logging
import os
import html
import re
import random
import string
from decimal import Decimal
from datetime import datetime
from typing import List, Tuple, Dict
from app.marzban.client import get_client

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select
from app.db.models import Setting

from app.db.session import session_scope
from app.db.models import Plan, User, Order, UserService
from app.services import marzban_ops as ops
from app.scripts.sync_plans import sync_templates_to_plans
from app.utils.username import tg_username


router = Router()

PAGE_SIZE = 5
# Purchase username selection state
_PURCHASE_SELECTION: Dict[int, Tuple[int, str]] = {}
_PURCHASE_CUSTOM_PENDING: Dict[int, int] = {}
# Multi-service purchase mode and selected service
# _PURCHASE_MODE[user_id] = (mode, tpl_id) where mode in {"new","extend"}
_PURCHASE_MODE: Dict[int, Tuple[str, int]] = {}
# _PURCHASE_EXT_SERVICE[user_id] = service_id to extend
_PURCHASE_EXT_SERVICE: Dict[int, int] = {}


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
            await message.answer("ℹ️ هیچ پلنی موجود نیست.")
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
                await message.answer("ℹ️ هیچ پلن فعالی در دسترس نیست.")
                return
            # send paginated list (page 1)
        await _send_plans_page(message, 1)
    except Exception as e:
        logging.exception("Failed to fetch plans from DB: %s", e)
        await message.answer("⚠️ خطا در دریافت پلن‌ها از سیستم. لطفاً کمی بعد تلاش کنید.")


@router.callback_query(F.data.startswith("plan:page:"))
async def cb_plan_page(cb: CallbackQuery) -> None:
    try:
        page = int(cb.data.split(":")[2]) if cb.data else 1
    except Exception:
        page = 1
    await _send_plans_page(cb.message, page)
    await cb.answer()


def _gen_username_random(tg_id: int) -> str:
    suffix = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(3))
    return f"tg{tg_id}{suffix}"


async def _present_final_confirm(cb: CallbackQuery, tpl_id: int, username_eff: str, plan: Plan) -> None:
    price_irr = Decimal(str(plan.price or 0))
    tmn = int(price_irr/Decimal('10')) if price_irr > 0 else 0
    gb_label = (f"{(plan.data_limit_bytes or 0) / (1024 ** 3):.0f}GB" if (plan.data_limit_bytes or 0) > 0 else "نامحدود")
    dur_label = (f"{plan.duration_days} روز" if (plan.duration_days or 0) > 0 else "بدون محدودیت")
    text = (
        "آیا از خرید پلن زیر اطمینان دارید؟\n\n"
        f"🧩 {plan.title}\n"
        f"⏳ مدت: {dur_label} | 📦 حجم: {gb_label}\n"
        f"👤 یوزرنیم سرویس: {username_eff}\n"
        f"💵 مبلغ: {tmn:,} تومان"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تایید ✅", callback_data=f"plan:final:{tpl_id}"), InlineKeyboardButton(text="انصراف ❌", callback_data="plan:cancel")]])
    await cb.message.answer(text, reply_markup=kb)


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
            # If cannot verify (bot not admin in channel), still enforce join UI
            join_url = f"https://t.me/{channel.lstrip('@')}"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 عضویت در کانال", url=join_url)],
                [InlineKeyboardButton(text="من عضو شدم ✅", callback_data="chk:chan")],
            ])
            await cb.message.answer("برای ادامه خرید، ابتدا در کانال عضو شوید و سپس دوباره تلاش کنید.", reply_markup=kb)
            await cb.answer()
            return
    # Stage 2: Phone verification gate
    try:
        pv_enabled = False
        async with session_scope() as session:
            from sqlalchemy import select as sa_select
            row = await session.scalar(sa_select(Setting).where(Setting.key == "PHONE_VERIFICATION_ENABLED"))
            if row:
                pv_enabled = str(row.value).strip() in {"1", "true", "True"}
            else:
                pv_enabled = os.getenv("PHONE_VERIFICATION_ENABLED", "0").strip() in {"1", "true", "True"}
            if pv_enabled and not is_admin_user:
                row_v = await session.scalar(sa_select(Setting).where(Setting.key == f"USER:{cb.from_user.id}:PHONE_VERIFIED_AT"))
                verified = bool(row_v and str(row_v.value).strip())
                if not verified:
                    rk = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 ارسال شماره من", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
                    await cb.message.answer("📱 برای ادامه خرید، لطفاً شماره تلگرام خود را ارسال کنید.", reply_markup=rk)
                    await cb.answer()
                    return
    except Exception:
        pass
    # Load plan and services to decide mode (new vs extend)
    async with session_scope() as session:
        plan = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
        urow = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        services = []
        if urow:
            services = (await session.execute(select(UserService).where(UserService.user_id == urow.id).order_by(UserService.created_at.desc()))).scalars().all()
        username_eff = tg_username(cb.from_user.id)
        if urow and getattr(urow, "marzban_username", None):
            username_eff = urow.marzban_username
    if not plan:
        await cb.answer("پلن یافت نشد", show_alert=True)
        return
    _PURCHASE_SELECTION.pop(cb.from_user.id, None)
    _PURCHASE_CUSTOM_PENDING.pop(cb.from_user.id, None)
    _PURCHASE_MODE.pop(cb.from_user.id, None)
    _PURCHASE_EXT_SERVICE.pop(cb.from_user.id, None)
    if not services:
        # No services yet → go to new service mode directly
        await cb_plan_mode_new(cb, tpl_id)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆕 اکانت جدید", callback_data=f"plan:mode:new:{tpl_id}")],
            [InlineKeyboardButton(text="🔁 تمدید اکانت", callback_data=f"plan:mode:ext:{tpl_id}")],
        ])
        await cb.message.answer("نوع خرید را انتخاب کنید:", reply_markup=kb)
        await cb.answer()


@router.callback_query(F.data.startswith("plan:uname:use:"))
async def cb_plan_uname_use(cb: CallbackQuery) -> None:
    try:
        tpl_id = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    async with session_scope() as session:
        plan = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
        username_eff = tg_username(cb.from_user.id)
        urow = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if urow and getattr(urow, "marzban_username", None):
            username_eff = urow.marzban_username
    if not plan:
        await cb.answer("پلن یافت نشد", show_alert=True)
        return
    _PURCHASE_SELECTION[cb.from_user.id] = (tpl_id, username_eff)
    await _present_final_confirm(cb, tpl_id, username_eff, plan)
    await cb.answer()


@router.callback_query(F.data.startswith("plan:uname:rnd:"))
async def cb_plan_uname_rnd(cb: CallbackQuery) -> None:
    try:
        tpl_id = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    # generate candidate unique vs DB users
    async with session_scope() as session:
        urow = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if not urow:
            # Auto-register user to allow purchase without requiring /start
            urow = User(
                telegram_id=cb.from_user.id,
                marzban_username=tg_username(cb.from_user.id),
                subscription_token=None,
                status="active",
                data_limit_bytes=0,
                balance=0,
            )
            session.add(urow)
            await session.flush()
            await session.commit()
        candidate = None
        for _ in range(10):
            cand = _gen_username_random(cb.from_user.id)
            exists = await session.scalar(select(User.id).where(User.marzban_username == cand))
            if not exists:
                candidate = cand
                break
        if not candidate:
            await cb.answer("عدم امکان ساخت نام کاربری رندوم", show_alert=True)
            return
        plan = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
    if not plan:
        await cb.answer("پلن یافت نشد", show_alert=True)
        return
    _PURCHASE_SELECTION[cb.from_user.id] = (tpl_id, candidate)
    await _present_final_confirm(cb, tpl_id, candidate, plan)
    await cb.answer()


@router.callback_query(F.data.startswith("plan:uname:cst:"))
async def cb_plan_uname_cst(cb: CallbackQuery) -> None:
    try:
        tpl_id = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    _PURCHASE_CUSTOM_PENDING[cb.from_user.id] = tpl_id
    await cb.message.answer("یوزرنیم دلخواه را ارسال کنید (فقط حروف کوچک و ارقام، حداقل ۶ کاراکتر).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _PURCHASE_CUSTOM_PENDING and isinstance(getattr(m, "text", None), str))
async def msg_plan_uname_custom(message: Message) -> None:
    user_id = message.from_user.id
    tpl_id = _PURCHASE_CUSTOM_PENDING.pop(user_id)
    uname = (message.text or "").strip()
    if not re.fullmatch(r"[a-z0-9]{6,}", uname):
        await message.answer("فرمت نامعتبر است. فقط حروف کوچک و ارقام، حداقل ۶ کاراکتر.")
        _PURCHASE_CUSTOM_PENDING[user_id] = tpl_id
        return
    async with session_scope() as session:
        exists = await session.scalar(select(User.id).where(User.marzban_username == uname))
        if exists:
            await message.answer("این یوزرنیم قبلاً استفاده شده است. مورد دیگری ارسال کنید.")
            _PURCHASE_CUSTOM_PENDING[user_id] = tpl_id
            return
        plan = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
    if not plan:
        await message.answer("⚠️ پلن یافت نشد.")
        return
    _PURCHASE_SELECTION[user_id] = (tpl_id, uname)
    # Use a fake cb wrapper for uniform rendering
    class _Cb:
        def __init__(self, m): self.message = m
    await _present_final_confirm(_Cb(message), tpl_id, uname, plan)


@router.callback_query(F.data.startswith("plan:mode:new:"))
async def cb_plan_mode_new(cb: CallbackQuery, tpl_id: int | None = None) -> None:
    try:
        t = tpl_id if tpl_id is not None else int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    _PURCHASE_MODE[cb.from_user.id] = ("new", t)
    # Proceed to username selection UI (existing flow)
    async with session_scope() as session:
        plan = (await session.execute(select(Plan).where(Plan.template_id == t, Plan.is_active == True))).scalars().first()
        username_eff = tg_username(cb.from_user.id)
        urow = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if urow and getattr(urow, "marzban_username", None):
            username_eff = urow.marzban_username
    if not plan:
        await cb.answer("پلن یافت نشد", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(text="ساخت یوزرنیم رندوم", callback_data=f"plan:uname:rnd:{t}")],
        [InlineKeyboardButton(text="یوزرنیم دلخواه ✏️", callback_data=f"plan:uname:cst:{t}")],
    ])
    await cb.message.answer("🧩 لطفاً روش انتخاب یوزرنیم را انتخاب کنید:", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("plan:mode:ext:"))
async def cb_plan_mode_ext(cb: CallbackQuery) -> None:
    try:
        tpl_id = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    _PURCHASE_MODE[cb.from_user.id] = ("extend", tpl_id)
    # List services to extend
    async with session_scope() as session:
        urow = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if not urow:
            # Auto-register user to proceed with extend flow
            urow = User(
                telegram_id=cb.from_user.id,
                marzban_username=tg_username(cb.from_user.id),
                subscription_token=None,
                status="active",
                data_limit_bytes=0,
                balance=0,
            )
            session.add(urow)
            await session.flush()
            await session.commit()
        services = (await session.execute(select(UserService).where(UserService.user_id == urow.id).order_by(UserService.created_at.desc()))).scalars().all()
    if not services:
        await cb.message.answer("ℹ️ هیچ سرویسی برای تمدید یافت نشد. لطفاً 'اکانت جدید' را انتخاب کنید.")
        await cb.answer()
        return
    lines = ["🔁 انتخاب سرویس برای تمدید:"]
    kb_rows: List[List[InlineKeyboardButton]] = []
    for s in services:
        lines.append(f"- {s.username} | وضعیت: {s.status}")
        kb_rows.append([InlineKeyboardButton(text=f"تمدید {s.username}", callback_data=f"plan:extsel:{tpl_id}:{s.id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await cb.message.answer("\n".join(lines), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("plan:extsel:"))
async def cb_plan_extend_select(cb: CallbackQuery) -> None:
    try:
        _, _, tpl_id_str, sid_str = cb.data.split(":")
        tpl_id = int(tpl_id_str)
        sid = int(sid_str)
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    _PURCHASE_EXT_SERVICE[cb.from_user.id] = sid
    # Show final confirmation with the service username
    async with session_scope() as session:
        plan = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
        s = await session.scalar(select(UserService).where(UserService.id == sid))
    if not (plan and s):
        await cb.answer("یافت نشد", show_alert=True)
        return
    await _present_final_confirm(cb, tpl_id, s.username, plan)
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
                await cb.answer("ابتدا در کانال عضو شوید.", show_alert=True)
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
    # Ensure username selection applied (rename if changed) then proceed
    # Ensure DB user exists; do not rename here (multi-service)
    sel = _PURCHASE_SELECTION.get(cb.from_user.id)
    if sel and sel[0] == tpl_id:
        async with session_scope() as session:
            db_user = (await session.execute(select(User).where(User.telegram_id == cb.from_user.id))).scalars().first()
            if not db_user:
                from app.utils.username import tg_username as _tg
                db_user = User(
                    telegram_id=cb.from_user.id,
                    marzban_username=sel[1] or _tg(cb.from_user.id),
                    subscription_token=None,
                    status="active",
                    data_limit_bytes=0,
                    balance=0,
                )
                session.add(db_user)
                await session.flush()
    # Proceed with purchase
    await _do_purchase(cb, tpl_id)


@router.callback_query(F.data.startswith("plan:final:"))
async def cb_plan_final(cb: CallbackQuery) -> None:
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
                await cb.answer("ابتدا در کانال عضو شوید.", show_alert=True)
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
    # Ensure username selection applied (rename if changed) then proceed
    # Ensure DB user exists; do not rename here (multi-service)
    sel = _PURCHASE_SELECTION.get(cb.from_user.id)
    if sel and sel[0] == tpl_id:
        async with session_scope() as session:
            db_user = (await session.execute(select(User).where(User.telegram_id == cb.from_user.id))).scalars().first()
            if not db_user:
                from app.utils.username import tg_username as _tg
                db_user = User(
                    telegram_id=cb.from_user.id,
                    marzban_username=sel[1] or _tg(cb.from_user.id),
                    subscription_token=None,
                    status="active",
                    data_limit_bytes=0,
                    balance=0,
                )
                session.add(db_user)
                await session.flush()
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
        username_default = tg_username(tg_id)
        db_user = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalars().first()
        if not db_user:
            db_user = User(
                telegram_id=tg_id,
                marzban_username=username_default,
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
        # Enough balance → create order and provision
        from app.services import marzban_ops as ops
        from app.utils.username import tg_username as _tg
        mode_tpl = _PURCHASE_MODE.get(cb.from_user.id)
        mode = mode_tpl[0] if mode_tpl and mode_tpl[1] == tpl_id else "new"
        try:
            # Create order record as paid for traceability
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
            token = None
            if mode == "extend":
                sid = _PURCHASE_EXT_SERVICE.get(cb.from_user.id)
                usvc = await session.scalar(select(UserService).where(UserService.id == sid, UserService.user_id == db_user.id))
                if not usvc:
                    await cb.message.answer("⚠️ سرویس انتخابی یافت نشد.")
                    await cb.answer()
                    return
                info = await ops.provision_for_plan(usvc.username, plan)
                order.user_service_id = usvc.id
                if isinstance(info, dict):
                    sub_url = info.get("subscription_url", "")
                    token = sub_url.rstrip("/").split("/")[-1] if sub_url else None
                    if token:
                        usvc.last_token = token
            else:
                # new service: use selected username or fallback
                chosen = _PURCHASE_SELECTION.get(cb.from_user.id)
                username_eff = (chosen[1] if chosen and chosen[0] == tpl_id else (db_user.marzban_username or _tg(tg_id)))
                info = await ops.provision_for_plan(username_eff, plan)
                # upsert user_service by username
                usvc = await session.scalar(select(UserService).where(UserService.user_id == db_user.id, UserService.username == username_eff))
                if not usvc:
                    usvc = UserService(user_id=db_user.id, username=username_eff, status="active")
                    session.add(usvc)
                    await session.flush()
                order.user_service_id = usvc.id
                if isinstance(info, dict):
                    sub_url = info.get("subscription_url", "")
                    token = sub_url.rstrip("/").split("/")[-1] if sub_url else None
                    if token:
                        usvc.last_token = token
            # Capture delivery target (service)
            deliver_username = usvc.username
            deliver_sid = usvc.id
            # Mark order provisioned
            order.status = "provisioned"
            order.paid_at = order.updated_at = order.provisioned_at = datetime.utcnow()
            await session.commit()
        except Exception:
            await cb.message.answer("❌ خطا در فعال‌سازی پلن. لطفاً مجدداً تلاش کنید یا به ادمین اطلاع دهید.")
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
            info2 = await client.get_user(deliver_username)
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
        manage_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 مدیریت سرویس", callback_data=f"acct:svc:{deliver_sid}"), InlineKeyboardButton(text="📋 کپی همه", callback_data=f"acct:copyall:svc:{deliver_sid}")]])
        # Send textual configs as headered code blocks (HTML), chunked safely
        if links:
            encoded = [html.escape(str(ln).strip()) for ln in links if str(ln).strip()]
            blocks = [f"<pre>{e}</pre>" for e in encoded]
            header = "🧩 کانفیگ‌های متنی:\n\n"
            body = header + "\n\n".join(blocks)
            if len(body) <= 3500:
                await cb.message.answer(body, reply_markup=manage_kb, parse_mode="HTML")
            else:
                chunk: List[str] = []
                size = 0
                first = True
                for b in blocks:
                    entry = ("" if first else "\n\n") + b
                    addition = (header + entry) if first else entry
                    if size + len(addition) > 3500:
                        await cb.message.answer((header if first else "") + "\n\n".join(chunk), parse_mode="HTML")
                        chunk = [b]
                        size = len(header) + len(b)
                        first = False
                        continue
                    chunk.append(b)
                    size += len(addition)
                    first = False
                if chunk:
                    await cb.message.answer((header if first else "") + "\n\n".join(chunk), reply_markup=manage_kb, parse_mode="HTML")
        else:
            # If no direct configs, still show manage button for user to fetch
            await cb.message.answer("ℹ️ برای مدیریت و دریافت کانفیگ‌ها از دکمه زیر استفاده کنید.", reply_markup=manage_kb)
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
