from __future__ import annotations

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from datetime import datetime
import re
import random
import string

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, func, desc, distinct

from app.db.session import session_scope
from app.db.models import User, Order, Setting, Plan, WalletTopUp, UserService
from app.services.security import has_capability_async, CAP_WALLET_MODERATE
from app.services import marzban_ops as ops
from app.marzban.client import get_client

router = Router()

PAGE_SIZE = 5

# intents: admin_id -> (op, user_id)
_USER_INTENTS: Dict[int, Tuple[str, int]] = {}
# search: admin_id -> True when awaiting search query
_SEARCH_INTENT: Dict[int, bool] = {}
# service intents: admin_id -> (op, user_id, service_id)
_SVC_INTENTS: Dict[int, Tuple[str, int, int]] = {}


def _admin_only() -> str:
    return "شما دسترسی ادمین ندارید."


def _kb_users_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 همه کاربران", callback_data="users:list:all:1")],
        [InlineKeyboardButton(text="🔍 جستجو", callback_data="users:search")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="users:menu")],
    ])


async def _menu_summary_text() -> str:
    async with session_scope() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        buyers = (await session.execute(select(func.count(distinct(Order.user_id))))).scalar() or 0
        total_orders = (await session.execute(select(func.count(Order.id)))).scalar() or 0
        # Service-level status counts
        service_active = (await session.execute(select(func.count(UserService.id)).where(UserService.status == "active"))).scalar() or 0
        service_disabled = (await session.execute(select(func.count(UserService.id)).where(UserService.status == "disabled"))).scalar() or 0
        pending_topups = (await session.execute(select(func.count(WalletTopUp.id)).where(WalletTopUp.status == "pending"))).scalar() or 0
        approved_topups = (await session.execute(select(func.count(WalletTopUp.id)).where(WalletTopUp.status == "approved"))).scalar() or 0
    lines = [
        "👥 مدیریت کاربران",
        f"👥 کل: {int(total_users):,} | 🛍️ خریدار: {int(buyers):,} | 📦 سفارش‌ها: {int(total_orders):,}",
        f"🔖 وضعیت سرویس‌ها — ✅ فعال: {int(service_active):,} | 🚫 غیرفعال: {int(service_disabled):,}",
        f"💳 تراکنش‌ها — ⏳ در انتظار: {int(pending_topups):,} | ✅ تایید: {int(approved_topups):,}",
    ]
    return "\n".join(lines)


async def _fetch_users(page: int, buyers_only: bool) -> Tuple[List[Tuple[User, int, Optional[str]]], int, int]:
    # Returns [(user, orders_count, phone)], page, total_pages
    async with session_scope() as session:
        q = select(User)
        if buyers_only:
            subq = select(distinct(Order.user_id))
            q = q.where(User.id.in_(subq))
        q = q.order_by(desc(User.created_at))
        rows = (await session.execute(q)).scalars().all()
        total = len(rows)
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE if total > 0 else 1
        page = max(1, min(page, pages))
        start = (page - 1) * PAGE_SIZE
        subset = rows[start:start+PAGE_SIZE]
        out: List[Tuple[User, int, Optional[str]]] = []
        for u in subset:
            oc = (await session.execute(select(func.count(Order.id)).where(Order.user_id == u.id))).scalar() or 0
            phone_row = await session.scalar(select(Setting).where(Setting.key == f"USER:{u.telegram_id}:PHONE"))
            phone = str(phone_row.value).strip() if phone_row else None
            out.append((u, int(oc), phone))
        return out, page, pages


def _kb_users_pagination(prefix: str, page: int, pages: int) -> List[InlineKeyboardButton]:
    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️ قبلی", callback_data=f"{prefix}:{page-1}"))
    if page < pages:
        nav.append(InlineKeyboardButton(text="بعدی ▶️", callback_data=f"{prefix}:{page+1}"))
    return nav


@router.message(F.text == "👥 مدیریت کاربران")
async def admin_users_menu(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer(_admin_only())
        return
    # Clear any pending intents for a clean session
    _USER_INTENTS.pop(message.from_user.id, None)
    _SEARCH_INTENT.pop(message.from_user.id, None)
    text = await _menu_summary_text()
    await message.answer(text, reply_markup=_kb_users_menu())


@router.callback_query(F.data == "users:menu")
async def cb_users_menu(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    _USER_INTENTS.pop(cb.from_user.id, None)
    _SEARCH_INTENT.pop(cb.from_user.id, None)
    text = await _menu_summary_text()
    try:
        await cb.message.edit_text(text, reply_markup=_kb_users_menu())
    except Exception:
        await cb.message.answer(text, reply_markup=_kb_users_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("users:list:"))
async def cb_users_list(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, which, page = cb.data.split(":")
        buyers_only = which == "buyers"
        page_i = int(page)
    except Exception:
        buyers_only = False
        page_i = 1
    rows, page_i, pages = await _fetch_users(page_i, buyers_only)
    if not rows:
        await cb.message.answer("کاربری یافت نشد.")
        await cb.answer()
        return
    lines: List[str] = []
    prefix = "users:list:buyers" if buyers_only else "users:list:all"
    nav = _kb_users_pagination(prefix, page_i, pages)
    kb_rows: List[List[InlineKeyboardButton]] = []
    # Fetch TG usernames from settings map for display
    async with session_scope() as session:
        settings_rows = (await session.execute(select(Setting).where(Setting.key.like("USER:%:TG_USERNAME")))).scalars().all()
        tg_map: Dict[int, str] = {}
        for r in settings_rows:
            try:
                tg_id = int(str(r.key).split(":")[1])
                tg_map[tg_id] = str(r.value).strip().lstrip("@")
            except Exception:
                pass
    for u, oc, phone in rows:
        handle = tg_map.get(u.telegram_id)
        handle_disp = f"@{handle}" if handle else "—"
        lines.append(f"- 🆔 tg:{u.telegram_id} | 👤 {handle_disp}")
    for u, _, _ in rows:
        handle = tg_map.get(u.telegram_id)
        handle_disp = f"@{handle}" if handle else "—"
        kb_rows.append([InlineKeyboardButton(text=f"مدیریت tg:{u.telegram_id} | {handle_disp}", callback_data=f"users:view:{u.id}")])
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="users:menu")])
    try:
        await cb.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    except Exception:
        await cb.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await cb.answer()


async def _render_user_detail(u: User) -> Tuple[str, InlineKeyboardMarkup]:
    async with session_scope() as session:
        oc = (await session.execute(select(func.count(Order.id)).where(Order.user_id == u.id))).scalar() or 0
        phone_row = await session.scalar(select(Setting).where(Setting.key == f"USER:{u.telegram_id}:PHONE"))
        phone = str(phone_row.value).strip() if phone_row else None
    tmn = int(Decimal(u.balance or 0) / Decimal("10"))
    text = (
        f"👤 {u.marzban_username}\n"
        f"🆔 tg:{u.telegram_id}\n"
        f"📦 سفارش‌ها: {int(oc)}\n"
        f"👛 موجودی: {tmn:,} تومان\n"
        f"📱 شماره: {phone or '—'}\n"
        f"🔖 وضعیت: {u.status}"
    )
    btns: List[List[InlineKeyboardButton]] = []
    btns.append([InlineKeyboardButton(text=("🚫 Ban" if u.status != "disabled" else "✅ Unban"), callback_data=f"users:ban:{u.id}")])
    btns.append([InlineKeyboardButton(text="➕ شارژ دستی (TMN)", callback_data=f"users:wadd:{u.id}")])
    # Per-service operations are available under service management view
    btns.append([InlineKeyboardButton(text="🛒 فعال‌سازی پلن", callback_data=f"users:grant:{u.id}:1")])
    btns.append([InlineKeyboardButton(text="♻️ Reset", callback_data=f"users:reset:{u.id}"), InlineKeyboardButton(text="🔗 Revoke", callback_data=f"users:revoke:{u.id}")])
    btns.append([InlineKeyboardButton(text="🗑️ حذف (Marzban)", callback_data=f"users:delete:{u.id}")])
    btns.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="users:menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=btns)


@router.callback_query(F.data.startswith("users:view:"))
async def cb_user_view(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    _USER_INTENTS.pop(cb.from_user.id, None)
    _SVC_INTENTS.pop(cb.from_user.id, None)
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        svcs = (await session.execute(select(UserService).where(UserService.user_id == uid).order_by(UserService.created_at.desc()))).scalars().all() if u else []
        banned_row = None
        if u:
            banned_row = await session.scalar(select(Setting).where(Setting.key == f"USER:{u.telegram_id}:BANNED"))
    if not u:
        await cb.answer("not found", show_alert=True)
        return
    # Render header + services
    header, _ = await _render_user_detail(u)
    lines = [header, "", "🧩 سرویس‌ها:"]
    kb_rows: List[List[InlineKeyboardButton]] = []
    is_banned = bool(banned_row and str(banned_row.value).strip().lower() in {"1", "true"})
    # Prevent ban button for admin users
    try:
        from app.services.security import get_admin_ids
        is_target_admin = u.telegram_id in set(get_admin_ids())
    except Exception:
        is_target_admin = False
    if not is_target_admin:
        kb_rows.append([InlineKeyboardButton(text=("✅ رفع بن کاربر" if is_banned else "⛔️ بن کاربر (ربات)"), callback_data=f"users:banbot:{uid}")])
    if svcs:
        for s in svcs:
            lines.append(f"- {s.username} | وضعیت: {s.status}")
            kb_rows.append([InlineKeyboardButton(text=f"مدیریت سرویس {s.username}", callback_data=f"users:svc:{uid}:{s.id}")])
    else:
        lines.append("— سرویسی ثبت نشده است.")
    kb_rows.append([InlineKeyboardButton(text="🛒 فعال‌سازی پلن", callback_data=f"users:grant:{uid}:1")])
    kb_rows.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="users:menu")])
    try:
        await cb.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    except Exception:
        await cb.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await cb.answer()


@router.callback_query(F.data.startswith("users:ban:"))
async def cb_user_ban(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    # Prevent banning admin users
    try:
        from app.services.security import get_admin_ids
        admin_ids = set(get_admin_ids())
    except Exception:
        admin_ids = set()
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        if not u:
            await cb.answer("not found", show_alert=True)
            return
        if u.telegram_id in admin_ids:
            await cb.answer("⛔️ امکان بن کردن ادمین وجود ندارد.", show_alert=True)
            return
        new_status = "disabled" if u.status != "disabled" else "active"
        try:
            await ops.set_status(u.marzban_username, new_status)
            u.status = new_status
            await session.commit()
        except Exception:
            await cb.answer("ops error", show_alert=True)
            return
    # notify user
    try:
        if new_status == "disabled":
            await cb.message.bot.send_message(chat_id=u.telegram_id, text="⛔️ حساب شما در ربات بن شد و تمامی سرویس‌ها غیرفعال شدند.")
        else:
            await cb.message.bot.send_message(chat_id=u.telegram_id, text="✅ حساب شما در ربات رفع بن شد و سرویس‌ها فعال شدند.")
    except Exception:
        pass
    text, kb = await _render_user_detail(u)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer("updated")


@router.callback_query(F.data.startswith("users:banbot:"))
async def cb_user_banbot(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        if not u:
            await cb.answer("not found", show_alert=True)
            return
        # Guard: do not allow ban for admin users
        try:
            from app.services.security import get_admin_ids
            if u.telegram_id in set(get_admin_ids()):
                await cb.answer("⛔️ امکان بن کردن ادمین وجود ندارد.", show_alert=True)
                return
        except Exception:
            pass
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{u.telegram_id}:BANNED"))
        currently_banned = bool(row and str(row.value).strip().lower() in {"1", "true"})
        # Toggle state
        if currently_banned:
            # Unban
            if row:
                # Clear or set to 0
                row.value = "0"
            u.status = "active"
            # Clear RBK_SENT so that future bans can send keyboard removal again
            try:
                rbk = await session.scalar(select(Setting).where(Setting.key == f"USER:{u.telegram_id}:RBK_SENT"))
                if rbk:
                    await session.delete(rbk)
            except Exception:
                pass
            await session.commit()
        else:
            if not row:
                session.add(Setting(key=f"USER:{u.telegram_id}:BANNED", value="1"))
            else:
                row.value = "1"
            u.status = "disabled"
            await session.commit()
    # Apply status to all services
    try:
        # Reload services
        async with session_scope() as session:
            svcs = (await session.execute(select(UserService).where(UserService.user_id == uid))).scalars().all()
            usernames = [s.username for s in svcs]
        from app.services import marzban_ops as ops
        target_status = "active" if currently_banned else "disabled"
        for un in usernames:
            try:
                await ops.set_status(un, target_status)
            except Exception:
                pass
    except Exception:
        pass
    # Notify user
    try:
        if currently_banned:
            await cb.message.bot.send_message(chat_id=u.telegram_id, text="✅ حساب شما در ربات رفع بن شد و سرویس‌ها فعال شدند.")
        else:
            await cb.message.bot.send_message(chat_id=u.telegram_id, text="⛔️ حساب شما در ربات بن شد و تمامی سرویس‌ها غیرفعال شدند.")
    except Exception:
        pass
    # Refresh view
    try:
        async with session_scope() as session:
            u2 = await session.scalar(select(User).where(User.id == uid))
            svcs2 = (await session.execute(select(UserService).where(UserService.user_id == uid).order_by(UserService.created_at.desc()))).scalars().all() if u2 else []
            banned_row = await session.scalar(select(Setting).where(Setting.key == f"USER:{u2.telegram_id}:BANNED")) if u2 else None
        header, _ = await _render_user_detail(u2)
        lines = [header, "", "🧩 سرویس‌ها:"]
        kb_rows: List[List[InlineKeyboardButton]] = []
        is_banned = bool(banned_row and str(banned_row.value).strip().lower() in {"1", "true"})
        kb_rows.append([InlineKeyboardButton(text=("✅ رفع بن کاربر" if is_banned else "⛔️ بن کاربر (ربات)"), callback_data=f"users:banbot:{uid}")])
        if svcs2:
            for s in svcs2:
                lines.append(f"- {s.username} | وضعیت: {s.status}")
                kb_rows.append([InlineKeyboardButton(text=f"مدیریت سرویس {s.username}", callback_data=f"users:svc:{uid}:{s.id}")])
        else:
            lines.append("— سرویسی ثبت نشده است.")
        kb_rows.append([InlineKeyboardButton(text="🛒 فعال‌سازی پلن", callback_data=f"users:grant:{uid}:1")])
        kb_rows.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="users:menu")])
        try:
            await cb.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
        except Exception:
            await cb.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    except Exception:
        pass
    await cb.answer("updated")


@router.callback_query(F.data.startswith("users:wadd:"))
async def cb_user_wallet_add_prompt(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    # cancel any other intent
    _SEARCH_INTENT.pop(cb.from_user.id, None)
    _USER_INTENTS[cb.from_user.id] = ("wallet_add_tmn", uid)
    await cb.message.answer("مبلغ را به تومان ارسال کنید (عدد صحیح).")
    await cb.answer()


@router.callback_query(F.data.startswith("users:addgb:"))
async def cb_user_addgb_prompt(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    _SEARCH_INTENT.pop(cb.from_user.id, None)
    _USER_INTENTS[cb.from_user.id] = ("add_gb", uid)
    await cb.message.answer("مقدار حجم را به گیگابایت ارسال کنید (مثلاً 5 یا 1.5).")
    await cb.answer()


@router.callback_query(F.data.startswith("users:extend:"))
async def cb_user_extend_prompt(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    _SEARCH_INTENT.pop(cb.from_user.id, None)
    _USER_INTENTS[cb.from_user.id] = ("extend_days", uid)
    await cb.message.answer("تعداد روزهای تمدید را ارسال کنید (عدد صحیح).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and (m.from_user.id in _USER_INTENTS or m.from_user.id in _SVC_INTENTS) and isinstance(getattr(m, "text", None), str) and not _SEARCH_INTENT.get(m.from_user.id, False))
async def admin_users_numeric_inputs(message: Message) -> None:
    admin_id = message.from_user.id
    op, uid = _USER_INTENTS.get(admin_id, ("", 0))
    svc_intent = _SVC_INTENTS.get(admin_id)
    if not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        _USER_INTENTS.pop(admin_id, None)
        await message.answer(_admin_only())
        return
    async with session_scope() as session:
        if not svc_intent:
            u = await session.scalar(select(User).where(User.id == uid))
            if not u:
                _USER_INTENTS.pop(admin_id, None)
                await message.answer("کاربر یافت نشد.")
                return
        if svc_intent:
            # Service-specific numeric intents
            sop, suid, sid = svc_intent
            s = await session.scalar(select(UserService).where(UserService.id == sid, UserService.user_id == suid))
            if not s:
                _SVC_INTENTS.pop(admin_id, None)
                await message.answer("سرویس یافت نشد.")
                return
            if sop == "add_gb_svc":
                try:
                    gb = float(message.text.strip())
                    if gb <= 0:
                        raise ValueError
                except Exception:
                    await message.answer("مقدار نامعتبر است. یک عدد مثبت (مثلاً 1.5) ارسال کنید.")
                    return
                try:
                    await ops.add_data_gb(s.username, gb)
                except Exception:
                    await message.answer("خطا در اعمال حجم.")
                    return
                _SVC_INTENTS.pop(admin_id, None)
                await message.answer(f"📈 به سرویس {s.username} {gb}GB اضافه شد.")
                return
            if sop == "extend_days_svc":
                try:
                    days = int(message.text.strip())
                    if days <= 0:
                        raise ValueError
                except Exception:
                    await message.answer("تعداد روز نامعتبر است. یک عدد صحیح مثبت ارسال کنید.")
                    return
                try:
                    await ops.extend_expire(s.username, days)
                except Exception:
                    await message.answer("خطا در تمدید.")
                    return
                _SVC_INTENTS.pop(admin_id, None)
                await message.answer(f"⏳ سرویس {s.username} به مدت {days} روز تمدید شد.")
                return
        if op == "wallet_add_tmn":
            try:
                toman = int(message.text.strip())
                if toman <= 0:
                    raise ValueError
            except Exception:
                await message.answer("مبلغ نامعتبر است. یک عدد صحیح مثبت ارسال کنید.")
                return
            irr = Decimal(toman) * Decimal('10')
            u.balance = (Decimal(u.balance or 0) + irr)
            await session.commit()
            _USER_INTENTS.pop(admin_id, None)
            # notify user
            try:
                await message.bot.send_message(chat_id=u.telegram_id, text=f"✅💳 شارژ دستی توسط ادمین: +{toman:,} تومان\n👛 موجودی جدید: {int(Decimal(u.balance or 0)/Decimal('10')):,} تومان")
            except Exception:
                pass
            # refresh detail
            text, kb = await _render_user_detail(u)
            await message.answer(text, reply_markup=kb)
            return
        if op == "add_gb":
            try:
                gb = float(message.text.strip())
                if gb <= 0:
                    raise ValueError
            except Exception:
                await message.answer("مقدار نامعتبر است. یک عدد مثبت (مثلاً 1.5) ارسال کنید.")
                return
            try:
                await ops.add_data_gb(u.marzban_username, gb)
            except Exception:
                await message.answer("خطا در اعمال حجم.")
                return
            _USER_INTENTS.pop(admin_id, None)
            # notify user
            try:
                await message.bot.send_message(chat_id=u.telegram_id, text=f"📈 به سرویس شما {gb}GB توسط ادمین اضافه شد.")
            except Exception:
                pass
            text, kb = await _render_user_detail(u)
            await message.answer("افزایش حجم اعمال شد.")
            await message.answer(text, reply_markup=kb)
            return
        if op == "extend_days":
            try:
                days = int(message.text.strip())
                if days <= 0:
                    raise ValueError
            except Exception:
                await message.answer("تعداد روز نامعتبر است. یک عدد صحیح مثبت ارسال کنید.")
                return
            try:
                await ops.extend_expire(u.marzban_username, days)
            except Exception:
                await message.answer("خطا در تمدید.")
                return
            _USER_INTENTS.pop(admin_id, None)
            # notify user
            try:
                await message.bot.send_message(chat_id=u.telegram_id, text=f"⏳ سرویس شما {days} روز توسط ادمین تمدید شد.")
            except Exception:
                pass
            await message.answer("تمدید انجام شد.")
            text, kb = await _render_user_detail(u)
            await message.answer(text, reply_markup=kb)
            return
    _USER_INTENTS.pop(admin_id, None)


@router.callback_query(F.data.startswith("users:svc:"))
async def cb_users_service_view(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, sid_str = cb.data.split(":")
        uid = int(uid_str)
        sid = int(sid_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        s = await session.scalar(select(UserService).where(UserService.id == sid, UserService.user_id == uid))
    if not (u and s):
        await cb.answer("not found", show_alert=True)
        return
    text = (
        f"👤 سرویس: {s.username}\n"
        f"🆔 tg:{u.telegram_id}\n"
        f"🔖 وضعیت: {s.status}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 افزایش حجم (GB)", callback_data=f"users:addgbsvc:{uid}:{sid}"), InlineKeyboardButton(text="⏳ افزایش روز", callback_data=f"users:extendsvc:{uid}:{sid}")],
        [InlineKeyboardButton(text="♻️ Reset", callback_data=f"users:svcrst:{uid}:{sid}"), InlineKeyboardButton(text="🔗 Revoke", callback_data=f"users:svcrvk:{uid}:{sid}")],
        [InlineKeyboardButton(text="🗑️ حذف سرویس", callback_data=f"users:svcdel:{uid}:{sid}")],
        [InlineKeyboardButton(text="⬅️ بازگشت", callback_data=f"users:view:{uid}")],
    ])
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("users:addgbsvc:"))
async def cb_users_addgb_service(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, sid_str = cb.data.split(":")
        uid = int(uid_str)
        sid = int(sid_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    _SEARCH_INTENT.pop(cb.from_user.id, None)
    _SVC_INTENTS[cb.from_user.id] = ("add_gb_svc", uid, sid)
    await cb.message.answer("مقدار حجم را به گیگابایت ارسال کنید (مثلاً 5 یا 1.5).")
    await cb.answer()


@router.callback_query(F.data.startswith("users:extendsvc:"))
async def cb_users_extend_service(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, sid_str = cb.data.split(":")
        uid = int(uid_str)
        sid = int(sid_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    _SEARCH_INTENT.pop(cb.from_user.id, None)
    _SVC_INTENTS[cb.from_user.id] = ("extend_days_svc", uid, sid)
    await cb.message.answer("تعداد روزهای تمدید را ارسال کنید (عدد صحیح).")
    await cb.answer()


@router.callback_query(F.data.startswith("users:svcrst:"))
async def cb_users_reset_service(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, sid_str = cb.data.split(":")
        uid = int(uid_str)
        sid = int(sid_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    async with session_scope() as session:
        s = await session.scalar(select(UserService).where(UserService.id == sid, UserService.user_id == uid))
    if not s:
        await cb.answer("not found", show_alert=True)
        return
    try:
        await ops.reset_user(s.username)
    except Exception:
        await cb.answer("ops error", show_alert=True)
        return
    await cb.answer("reset")


@router.callback_query(F.data.startswith("users:svcrvk:"))
async def cb_users_revoke_service(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, sid_str = cb.data.split(":")
        uid = int(uid_str)
        sid = int(sid_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    async with session_scope() as session:
        s = await session.scalar(select(UserService).where(UserService.id == sid, UserService.user_id == uid))
    if not s:
        await cb.answer("not found", show_alert=True)
        return
    try:
        await ops.revoke_sub(s.username)
    except Exception:
        await cb.answer("ops error", show_alert=True)
        return
    await cb.answer("revoked")


@router.callback_query(F.data.startswith("users:svcdel:"))
async def cb_users_delete_service(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, sid_str = cb.data.split(":")
        uid = int(uid_str)
        sid = int(sid_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    async with session_scope() as session:
        s = await session.scalar(select(UserService).where(UserService.id == sid, UserService.user_id == uid))
        if not s:
            await cb.answer("not found", show_alert=True)
            return
        username = s.username
    try:
        await ops.delete_user(username)
    except Exception:
        await cb.answer("ops error", show_alert=True)
        return
    # Remove from DB
    async with session_scope() as session:
        s2 = await session.scalar(select(UserService).where(UserService.id == sid, UserService.user_id == uid))
        if s2:
            from sqlalchemy import delete as sa_delete
            await session.execute(sa_delete(UserService).where(UserService.id == sid))
            await session.commit()
    await cb.message.answer("سرویس حذف شد.")
    await cb.answer("deleted")


@router.callback_query(F.data.startswith("users:reset:"))
async def cb_user_reset_prompt(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    async with session_scope() as session:
        svcs = (await session.execute(select(UserService).where(UserService.user_id == uid).order_by(UserService.created_at.desc()))).scalars().all()
    if not svcs:
        await cb.message.answer("برای این کاربر سرویسی یافت نشد.")
        await cb.answer()
        return
    lines = ["♻️ یک سرویس را برای Reset انتخاب کنید:"]
    kb_rows: List[List[InlineKeyboardButton]] = []
    for s in svcs:
        lines.append(f"- {s.username} | وضعیت: {s.status}")
        kb_rows.append([InlineKeyboardButton(text=f"Reset {s.username}", callback_data=f"users:svcrst:{uid}:{s.id}")])
    try:
        await cb.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    except Exception:
        await cb.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await cb.answer()


@router.callback_query(F.data.startswith("users:revoke:"))
async def cb_user_revoke(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
    if not u:
        await cb.answer("not found", show_alert=True)
        return
    try:
        await ops.revoke_sub(u.marzban_username)
    except Exception:
        await cb.answer("ops error", show_alert=True)
        return
    try:
        await cb.message.bot.send_message(chat_id=u.telegram_id, text="لینک اشتراک شما توسط ادمین بروزرسانی شد.")
    except Exception:
        pass
    await cb.answer("revoked")


@router.callback_query(F.data.startswith("users:delete:"))
async def cb_user_delete(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        uid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
    if not u:
        await cb.answer("not found", show_alert=True)
        return
    try:
        await ops.delete_user(u.marzban_username)
    except Exception:
        await cb.answer("ops error", show_alert=True)
        return
    try:
        await cb.message.bot.send_message(chat_id=u.telegram_id, text="اکانت شما در پنل توسط ادمین حذف شد.")
    except Exception:
        pass
    await cb.answer("deleted")


# Search flow
@router.callback_query(F.data == "users:search")
async def cb_users_search_prompt(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    # Cancel any numeric intent to avoid capturing digits as admin ops
    _USER_INTENTS.pop(cb.from_user.id, None)
    _SEARCH_INTENT[cb.from_user.id] = True
    await cb.message.answer("عبارت جستجو را ارسال کنید (username یا tg_id یا شماره تماس).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and _SEARCH_INTENT.get(m.from_user.id, False) and isinstance(getattr(m, "text", None), str))
async def admin_users_search(message: Message) -> None:
    admin_id = message.from_user.id
    if not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        _SEARCH_INTENT.pop(admin_id, None)
        await message.answer(_admin_only())
        return
    raw = message.text or ""
    query = raw.strip()
    # Remove RTL markers and normalize
    query_marks_clean = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", query)
    normalized = query_marks_clean.strip().lower().lstrip("@")
    async with session_scope() as session:
        results: List[User] = []
        # Search by Marzban username (LIKE)
        results = (await session.execute(select(User).where(User.marzban_username.like(f"%{normalized}%")).order_by(desc(User.created_at)).limit(20))).scalars().all()
        # If digits-like: try telegram id
        digits_clean = re.sub(r"[\u200e\u200f\u202a-\u202e\s\-\+]", "", normalized)
        if not results and digits_clean.isdigit():
            u = await session.scalar(select(User).where(User.telegram_id == int(digits_clean)))
            if u:
                results = [u]
        # If not found, try Telegram username from settings
        if not results:
            rows = (await session.execute(select(Setting).where(Setting.key.like("USER:%:TG_USERNAME")).limit(5000))).scalars().all()
            matched: List[int] = []
            for r in rows:
                try:
                    if str(r.value).strip().lower() == normalized:
                        tg_id = int(str(r.key).split(":")[1])
                        matched.append(tg_id)
                except Exception:
                    pass
            if matched:
                results = (await session.execute(select(User).where(User.telegram_id.in_(matched)))).scalars().all()
        # Phone tail search as last resort
        if not results and digits_clean.isdigit():
            rows = (await session.execute(select(Setting).where(Setting.key.like("USER:%:PHONE")).limit(2000))).scalars().all()
            matched: List[int] = []
            for r in rows:
                try:
                    if str(r.value).strip().replace(" ", "").replace("-", "").endswith(digits_clean):
                        tg_id = int(str(r.key).split(":")[1])
                        matched.append(tg_id)
                except Exception:
                    pass
            if matched:
                results = (await session.execute(select(User).where(User.telegram_id.in_(matched)))).scalars().all()
    _SEARCH_INTENT.pop(admin_id, None)
    if not results:
        await message.answer("نتیجه‌ای یافت نشد.")
        return
    kb_rows: List[List[InlineKeyboardButton]] = []
    lines: List[str] = []
    for u in results:
        lines.append(f"- 🆔 tg:{u.telegram_id} | 👤 {u.marzban_username or '-'}")
        kb_rows.append([InlineKeyboardButton(text=f"مدیریت tg:{u.telegram_id} | {u.marzban_username or '-'}", callback_data=f"users:view:{u.id}")])
    kb_rows.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="users:menu")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


# Grant plan flow (admin activates plan for user)
@router.callback_query(F.data.startswith("users:grant:"))
async def cb_users_grant_plan_page(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, page_str = cb.data.split(":")
        uid = int(uid_str)
        page = int(page_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        plans = (await session.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.template_id))).scalars().all()
    if not u:
        await cb.answer("user not found", show_alert=True)
        return
    if not plans:
        await cb.message.answer("هیچ پلن فعالی موجود نیست.")
        await cb.answer()
        return
    total = len(plans)
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    subset = plans[start:start+PAGE_SIZE]
    lines = [f"🛒 انتخاب پلن برای {u.marzban_username} — صفحه {page}/{pages}"]
    kb_rows: List[List[InlineKeyboardButton]] = []
    for p in subset:
        tmn = int(Decimal(str(p.price or 0)) / Decimal('10')) if p.price else 0
        lines.append(f"#{p.template_id} — {p.title} | 💵 {tmn:,} تومان")
        kb_rows.append([InlineKeyboardButton(text=f"فعال‌سازی {p.title}", callback_data=f"users:grantconf:{uid}:{p.template_id}")])
    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️ قبلی", callback_data=f"users:grant:{uid}:{page-1}"))
    if page < pages:
        nav.append(InlineKeyboardButton(text="بعدی ▶️", callback_data=f"users:grant:{uid}:{page+1}"))
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data=f"users:view:{u.id}")])
    try:
        await cb.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    except Exception:
        await cb.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await cb.answer()


@router.callback_query(F.data.startswith("users:grantconf:"))
async def cb_users_grant_confirm(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, tpl_str = cb.data.split(":")
        uid = int(uid_str)
        tpl_id = int(tpl_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        p = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
    if not (u and p):
        await cb.answer("not found", show_alert=True)
        return
    # Ask for username selection method
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"استفاده از یوزرنیم فعلی: {u.marzban_username}", callback_data=f"users:grantuse:{uid}:{tpl_id}")],
        [InlineKeyboardButton(text="ساخت یوزرنیم رندوم", callback_data=f"users:grantrnd:{uid}:{tpl_id}")],
        [InlineKeyboardButton(text="یوزرنیم دلخواه ✏️", callback_data=f"users:grantcust:{uid}:{tpl_id}")],
        [InlineKeyboardButton(text="⬅️ بازگشت", callback_data=f"users:grant:{uid}:1")],
    ])
    try:
        await cb.message.answer("لطفاً روش انتخاب یوزرنیم را انتخاب کنید:", reply_markup=kb)
    except Exception:
        await cb.message.answer("لطفاً روش انتخاب یوزرنیم را انتخاب کنید:", reply_markup=kb)
    await cb.answer()


async def _get_sub_domain() -> str:
    import os
    return os.getenv("SUB_DOMAIN_PREFERRED", "")

# ===== Username selection and provisioning helpers =====
_GRANT_CUSTOM_INTENT: Dict[int, Tuple[int, int]] = {}


def _gen_username_random(tg_id: int) -> str:
    suffix = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(3))
    return f"tg{tg_id}{suffix}"


async def _provision_and_record(uid: int, tpl_id: int) -> Tuple[bool, str]:
    # Returns (ok, error_message)
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        p = (await session.execute(select(Plan).where(Plan.template_id == tpl_id, Plan.is_active == True))).scalars().first()
    if not (u and p):
        return False, "not found"
    username = u.marzban_username
    try:
        info = await ops.provision_for_plan(username, p)
    except Exception:
        return False, "provision error"
    # Persist order, link to UserService, and token
    async with session_scope() as session:
        u2 = await session.scalar(select(User).where(User.id == uid))
        # Upsert UserService for this username
        usvc = await session.scalar(select(UserService).where(UserService.user_id == u2.id, UserService.username == username))
        if not usvc:
            usvc = UserService(user_id=u2.id, username=username, status="active")
            session.add(usvc)
            await session.flush()
        # Extract token
        token = None
        try:
            sub_url = info.get("subscription_url", "") if isinstance(info, dict) else ""
            token = sub_url.rstrip("/").split("/")[-1] if sub_url else None
        except Exception:
            token = None
        if token:
            usvc.last_token = token
            u2.subscription_token = token  # backward-compat
        # Create order linked to the service
        o = Order(
            user_id=u2.id,
            plan_id=p.id,
            user_service_id=usvc.id,
            plan_template_id=p.template_id,
            plan_title=p.title,
            plan_price=Decimal('0'),
            plan_currency=p.currency,
            plan_duration_days=p.duration_days,
            plan_data_limit_bytes=p.data_limit_bytes,
            status="provisioned",
            amount=Decimal('0'),
            currency=p.currency,
            provider="admin_grant",
            provider_ref=None,
            receipt_file_path=None,
            admin_note="granted by admin",
            idempotency_key=None,
            paid_at=datetime.utcnow(),
            provisioned_at=datetime.utcnow(),
        )
        session.add(o)
        await session.commit()
    # Notify user + deliver manage buttons and fail-safe QR/configs
    try:
        sub_domain = (await _get_sub_domain())
        msg_lines = [
            "✅ سرویس برای شما توسط ادمین فعال شد.",
            f"🧩 پلن: {p.title}",
        ]
        if token and sub_domain:
            msg_lines += [
                f"🔗 لینک اشتراک: https://{sub_domain}/sub4me/{token}/",
                f"🛰️ v2ray: https://{sub_domain}/sub4me/{token}/v2ray",
                f"🧰 JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json",
            ]
        await router.bot.send_message(chat_id=u2.telegram_id, text="\n".join(msg_lines))
        # Fetch latest user info to build delivery
        links: list[str] = []
        sub_url = ""
        token2 = token
        try:
            client = await get_client()
            info2 = await client.get_user(username)
            links = list(map(str, (info2.get("links") or [])))
            sub_url = str(info2.get("subscription_url") or "")
            if not token2 and sub_url:
                token2 = sub_url.rstrip("/").split("/")[-1]
        except Exception:
            links = []
            sub_url = ""
        finally:
            try:
                await client.aclose()  # type: ignore
            except Exception:
                pass
        # Manage/Copy buttons (service-specific)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton  # local import to avoid top changes
        manage_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 مدیریت سرویس", callback_data=f"acct:svc:{usvc.id}"), InlineKeyboardButton(text="📋 کپی همه", callback_data=f"acct:copyall:svc:{usvc.id}")]])
        # If links exist, send them in chunks; otherwise, at least send QR/subscription URL
        if links:
            chunk: list[str] = []
            size = 0
            for ln in links:
                s = str(ln).strip()
                if not s:
                    continue
                entry = ("\n\n" if chunk else "") + s
                if size + len(entry) > 3500:
                    await router.bot.send_message(chat_id=u2.telegram_id, text="\n\n".join(chunk))
                    chunk = [s]
                    size = len(s)
                    continue
                chunk.append(s)
                size += len(entry)
            if chunk:
                await router.bot.send_message(chat_id=u2.telegram_id, text="\n\n".join(chunk), reply_markup=manage_kb)
        else:
            # Fail-safe: send QR or subscription URL
            disp_url = ""
            if sub_domain and token2:
                disp_url = f"https://{sub_domain}/sub4me/{token2}/"
            elif sub_url:
                disp_url = sub_url
            if disp_url:
                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={disp_url}"
                try:
                    await router.bot.send_photo(chat_id=u2.telegram_id, photo=qr_url, caption="🔳 QR اشتراک", reply_markup=manage_kb)
                except Exception:
                    await router.bot.send_message(chat_id=u2.telegram_id, text=disp_url, reply_markup=manage_kb)
            else:
                # As a last resort, send only manage buttons
                await router.bot.send_message(chat_id=u2.telegram_id, text="برای مدیریت سرویس از دکمه‌های زیر استفاده کنید.", reply_markup=manage_kb)
    except Exception:
        pass
    return True, ""

async def _apply_username_change_and_provision(uid: int, tpl_id: int, new_username: str) -> Tuple[bool, str]:
    # Update DB username first, then replace on server to avoid duplicates
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        if not u:
            return False, "user not found"
        old = u.marzban_username
        u.marzban_username = new_username
        await session.commit()
    try:
        await ops.replace_user_username(old, new_username, note=f"grant tpl:{tpl_id}")
    except Exception:
        return False, "rename error"
    # Ensure a UserService row is present for the new username before provisioning record
    async with session_scope() as session:
        u2 = await session.scalar(select(User).where(User.id == uid))
        usvc = await session.scalar(select(UserService).where(UserService.user_id == u2.id, UserService.username == new_username))
        if not usvc:
            usvc = UserService(user_id=u2.id, username=new_username, status="active")
            session.add(usvc)
            await session.commit()
    return await _provision_and_record(uid, tpl_id)


@router.callback_query(F.data.startswith("users:grantuse:"))
async def cb_users_grant_use(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, tpl_str = cb.data.split(":")
        uid = int(uid_str)
        tpl_id = int(tpl_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    ok, err = await _provision_and_record(uid, tpl_id)
    if not ok:
        await cb.answer(err, show_alert=True)
        return
    await cb.answer("granted")


@router.callback_query(F.data.startswith("users:grantrnd:"))
async def cb_users_grant_random(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, tpl_str = cb.data.split(":")
        uid = int(uid_str)
        tpl_id = int(tpl_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    # Generate random candidate including tg_id and ensure uniqueness in DB
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        if not u:
            await cb.answer("user not found", show_alert=True)
            return
        candidate = None
        for _ in range(10):
            cand = _gen_username_random(u.telegram_id)
            exists = await session.scalar(select(User.id).where(User.marzban_username == cand))
            if not exists:
                candidate = cand
                break
        if not candidate:
            await cb.answer("failed to generate username", show_alert=True)
            return
    ok, err = await _apply_username_change_and_provision(uid, tpl_id, candidate)
    if not ok:
        await cb.answer(err, show_alert=True)
        return
    await cb.answer("granted")


@router.callback_query(F.data.startswith("users:grantcust:"))
async def cb_users_grant_custom_prompt(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("No access", show_alert=True)
        return
    try:
        _, _, uid_str, tpl_str = cb.data.split(":")
        uid = int(uid_str)
        tpl_id = int(tpl_str)
    except Exception:
        await cb.answer("bad args", show_alert=True)
        return
    _GRANT_CUSTOM_INTENT[cb.from_user.id] = (uid, tpl_id)
    await cb.message.answer("یوزرنیم دلخواه را ارسال کنید (فقط حروف کوچک و ارقام، حداقل ۶ کاراکتر).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _GRANT_CUSTOM_INTENT and isinstance(getattr(m, "text", None), str))
async def admin_users_grant_custom_username(message: Message) -> None:
    admin_id = message.from_user.id
    if not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        _GRANT_CUSTOM_INTENT.pop(admin_id, None)
        await message.answer(_admin_only())
        return
    text = (message.text or "").strip()
    if not re.fullmatch(r"[a-z0-9]{6,}", text):
        await message.answer("فرمت نامعتبر است. فقط حروف کوچک و ارقام، حداقل ۶ کاراکتر.")
        return
    uid, tpl_id = _GRANT_CUSTOM_INTENT.pop(admin_id)
    async with session_scope() as session:
        exists = await session.scalar(select(User.id).where(User.marzban_username == text))
        if exists:
            await message.answer("این یوزرنیم قبلاً استفاده شده است. مورد دیگری ارسال کنید.")
            return
        u = await session.scalar(select(User).where(User.id == uid))
        if not u:
            await message.answer("کاربر یافت نشد.")
            return
    ok, err = await _apply_username_change_and_provision(uid, tpl_id, text)
    if not ok:
        await message.answer(f"خطا: {err}")
        return
    await message.answer("سرویس با یوزرنیم دلخواه فعال شد.")
