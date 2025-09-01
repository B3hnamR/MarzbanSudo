from __future__ import annotations

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, func, desc, distinct

from app.db.session import session_scope
from app.db.models import User, Order, Setting, Plan, WalletTopUp
from app.services.security import has_capability_async, CAP_WALLET_MODERATE
from app.services import marzban_ops as ops

router = Router()

PAGE_SIZE = 10

# intents: admin_id -> (op, user_id)
_USER_INTENTS: Dict[int, Tuple[str, int]] = {}
# search: admin_id -> True when awaiting search query
_SEARCH_INTENT: Dict[int, bool] = {}


def _admin_only() -> str:
    return "شما دسترسی ادمین ندارید."


def _kb_users_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 همه کاربران", callback_data="users:list:all:1"), InlineKeyboardButton(text="🛍️ خ��یداران", callback_data="users:list:buyers:1")],
        [InlineKeyboardButton(text="🔍 جستجو", callback_data="users:search")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="users:menu")],
    ])


async def _menu_summary_text() -> str:
    async with session_scope() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        buyers = (await session.execute(select(func.count(distinct(Order.user_id))))).scalar() or 0
        total_orders = (await session.execute(select(func.count(Order.id)))).scalar() or 0
        active_users = (await session.execute(select(func.count(User.id)).where(User.status == "active"))).scalar() or 0
        disabled_users = (await session.execute(select(func.count(User.id)).where(User.status == "disabled"))).scalar() or 0
        pending_topups = (await session.execute(select(func.count(WalletTopUp.id)).where(WalletTopUp.status == "pending"))).scalar() or 0
        approved_topups = (await session.execute(select(func.count(WalletTopUp.id)).where(WalletTopUp.status == "approved"))).scalar() or 0
    lines = [
        "👥 مدیریت کاربران",
        f"👥 کل کاربران: {int(total_users):,}",
        f"🛍️ کاربران دارای خرید: {int(buyers):,}",
        f"📦 ��جموع سفارش‌ها: {int(total_orders):,}",
        f"✅ وضعیت active: {int(active_users):,}",
        f"🚫 وضعیت disabled: {int(disabled_users):,}",
        f"💳⏳ درخواست‌های شارژ در انتظار: {int(pending_topups):,}",
        f"💳✅ شارژهای تاییدشده: {int(approved_topups):,}",
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
    for u, oc, phone in rows:
        tmn = int(Decimal(u.balance or 0) / Decimal("10"))
        mark = "✅" if oc > 0 else "—"
        lines.append(f"- {u.marzban_username} | tg:{u.telegram_id} | خرید: {oc} {mark} | موجودی: {tmn:,} تومان" + (f" | 📞 {phone}" if phone else ""))
    prefix = "users:list:buyers" if buyers_only else "users:list:all"
    nav = _kb_users_pagination(prefix, page_i, pages)
    kb_rows: List[List[InlineKeyboardButton]] = []
    for u, _, _ in rows:
        kb_rows.append([InlineKeyboardButton(text=f"مدیریت {u.marzban_username}", callback_data=f"users:view:{u.id}")])
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
    btns.append([InlineKeyboardButton(text="➕ افزایش حجم (GB)", callback_data=f"users:addgb:{u.id}"), InlineKeyboardButton(text="➕ افزایش روز", callback_data=f"users:extend:{u.id}")])
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
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
    if not u:
        await cb.answer("not found", show_alert=True)
        return
    text, kb = await _render_user_detail(u)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)
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
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        if not u:
            await cb.answer("not found", show_alert=True)
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
        await cb.message.bot.send_message(chat_id=u.telegram_id, text=("اکانت شما توسط ادمین غیرفعال شد." if new_status == "disabled" else "اکانت شما توسط ادمین فعال شد."))
    except Exception:
        pass
    text, kb = await _render_user_detail(u)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)
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
    _USER_INTENTS[cb.from_user.id] = ("extend_days", uid)
    await cb.message.answer("تعداد روزهای تمدید را ارسال کنید (عدد صحیح).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _USER_INTENTS and isinstance(getattr(m, "text", None), str) and not _SEARCH_INTENT.get(m.from_user.id, False))
async def admin_users_numeric_inputs(message: Message) -> None:
    admin_id = message.from_user.id
    op, uid = _USER_INTENTS.get(admin_id, ("", 0))
    if not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        _USER_INTENTS.pop(admin_id, None)
        await message.answer(_admin_only())
        return
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.id == uid))
        if not u:
            _USER_INTENTS.pop(admin_id, None)
            await message.answer("کاربر یافت نشد.")
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
                await message.bot.send_message(chat_id=u.telegram_id, text=f"✅ شارژ دستی ت��سط ادمین: +{toman:,} تومان\nموجودی جدید: {int(Decimal(u.balance or 0)/Decimal('10')):,} تومان")
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
                await message.bot.send_message(chat_id=u.telegram_id, text=f"به سرویس شما {gb}GB توسط ادمین اضافه شد.")
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
                await message.bot.send_message(chat_id=u.telegram_id, text=f"سرویس شما {days} روز توسط ادمین تمدید شد.")
            except Exception:
                pass
            await message.answer("تمدید انجام شد.")
            text, kb = await _render_user_detail(u)
            await message.answer(text, reply_markup=kb)
            return
    _USER_INTENTS.pop(admin_id, None)


@router.callback_query(F.data.startswith("users:reset:"))
async def cb_user_reset(cb: CallbackQuery) -> None:
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
        await ops.reset_user(u.marzban_username)
    except Exception:
        await cb.answer("ops error", show_alert=True)
        return
    try:
        await cb.message.bot.send_message(chat_id=u.telegram_id, text="اکانت شما توسط ادمین Reset شد.")
    except Exception:
        pass
    await cb.answer("reset")


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
    query = message.text.strip()
    async with session_scope() as session:
        results: List[User] = []
        # Search by username (LIKE)
        results = (await session.execute(select(User).where(User.marzban_username.like(f"%{query}%")).order_by(desc(User.created_at)).limit(20))).scalars().all()
        # If digits and no results: try telegram id or phone tail match
        if not results and query.replace("+", "").replace(" ", "").lstrip("0").isdigit():
            # Try tg_id
            u = await session.scalar(select(User).where(User.telegram_id == int(query.replace(" ", "")) ))
            if u:
                results = [u]
            else:
                # phone search in settings
                rows = (await session.execute(select(Setting).where(Setting.key.like("USER:%:PHONE")).limit(2000))).scalars().all()
                matched: List[int] = []
                qn = query.replace(" ", "")
                for r in rows:
                    try:
                        if str(r.value).strip().endswith(qn):
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
        lines.append(f"- {u.marzban_username} | tg:{u.telegram_id}")
        kb_rows.append([InlineKeyboardButton(text=f"مدیریت {u.marzban_username}", callback_data=f"users:view:{u.id}")])
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
    # Provision via UI-safe flow; record order with amount=0 (admin grant)
    try:
        info = await ops.provision_for_plan(u.marzban_username, p)
    except Exception:
        await cb.answer("provision error", show_alert=True)
        return
    # Persist order and token
    async with session_scope() as session:
        u2 = await session.scalar(select(User).where(User.id == uid))
        # Create order snapshot with amount=0
        o = Order(
            user_id=u2.id,
            plan_id=p.id,
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
        # Extract token if available
        token = None
        try:
            sub_url = info.get("subscription_url", "") if isinstance(info, dict) else ""
            token = sub_url.rstrip("/").split("/")[-1] if sub_url else None
        except Exception:
            token = None
        if token:
            u2.subscription_token = token
        await session.commit()
    # Notify user with links
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
        await cb.message.bot.send_message(chat_id=u.telegram_id, text="\n".join(msg_lines))
    except Exception:
        pass
    await cb.answer("granted")


async def _get_sub_domain() -> str:
    import os
    return os.getenv("SUB_DOMAIN_PREFERRED", "")
