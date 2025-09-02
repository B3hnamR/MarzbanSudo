from __future__ import annotations

import os
import html
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
from decimal import Decimal

from aiogram import Router, F
import httpx
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, func

from app.db.session import session_scope
from app.db.models import User, Order, Setting, UserService
from app.marzban.client import get_client
from app.services.marzban_ops import revoke_sub as marz_revoke_sub
from app.services.marzban_ops import replace_user_username as ops_replace_username
from app.utils.username import tg_username
from app.services.security import is_admin_uid

# Optional Jalali date support
try:
    import jdatetime  # type: ignore
except Exception:  # pragma: no cover
    jdatetime = None

router = Router()

# Rename intents/state
_RENAME_CUSTOM_PENDING: Dict[int, bool] = {}


def _fmt_gb2(v: int) -> str:
    if v <= 0:
        return "نامحدود"
    return f"{v / (1024**3):.2f}GB"


def _acct_kb(has_token: bool, has_links: bool) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    rows.append([InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="acct:refresh")])
    rows.append([InlineKeyboardButton(text="✏️ تغییر یوزرنیم", callback_data="acct:rename")])
    if has_links:
        rows.append([
            InlineKeyboardButton(text="📄 کانفیگ‌ها (متنی)", callback_data="acct:links"),
            InlineKeyboardButton(text="📋 کپی همه", callback_data="acct:copyall"),
        ])
    if has_token:
        rows.append([
            InlineKeyboardButton(text="🔗 بروزرسانی لینک", callback_data="acct:revoke"),
            InlineKeyboardButton(text="🔳 QR اشتراک", callback_data="acct:qr"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_account_text(tg_id: int) -> Tuple[str, str | None, List[str]]:
    username_default = tg_username(tg_id)
    # Load DB info
    reg_date_txt = "—"
    orders_count = 0
    username_eff = username_default
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if user:
            reg_date_txt = user.created_at.strftime('%Y-%m-%d %H:%M:%S') + " UTC"
            res = await session.execute(select(func.count(Order.id)).where(Order.user_id == user.id))
            orders_count = int(res.scalar() or 0)
            if getattr(user, "marzban_username", None):
                username_eff = user.marzban_username
    # Load Marzban info
    client = await get_client()
    try:
        data = await client.get_user(username_eff)
    finally:
        await client.aclose()
    status = str(data.get("status") or "")
    is_disabled = status.lower() == "disabled"
    token = None if is_disabled else (data.get("subscription_token") or (data.get("subscription_url", "").split("/")[-1] if data.get("subscription_url") else None))
    expire_ts = 0 if is_disabled else int(data.get("expire") or 0)
    data_limit = 0 if is_disabled else int(data.get("data_limit") or 0)
    used_traffic = 0 if is_disabled else int(data.get("used_traffic") or 0)
    remaining = max(data_limit - used_traffic, 0)
    links: List[str] = list(map(str, data.get("links") or []))
    lrm = "\u200E"
    # Emoji-rich header
    lines = [
        f"👤 نام کاربری: {username_eff}",
        f"🆔 شناسه تلگرام: {lrm}{tg_id}",
        f"🗓️ تاریخ ثبت‌نام: {reg_date_txt}",
        f"🧾 تعداد خریدها: {orders_count}",
        f"📦 حجم کل: {_fmt_gb2(data_limit)}",
        f"📉 مصرف‌شده: {_fmt_gb2(used_traffic)}",
        f"📈 باقی‌مانده: {_fmt_gb2(remaining)}",
    ]
    if expire_ts > 0 and not is_disabled:
        try:
            if jdatetime:
                dt_utc = datetime.utcfromtimestamp(expire_ts)
                jd = jdatetime.datetime.fromgregorian(datetime=dt_utc)
                lines.append(f"⏳ انقضا: {jd.strftime('%Y/%m/%d %H:%M')}")
            else:
                lines.append(f"⏳ انقضا: {datetime.utcfromtimestamp(expire_ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        except Exception:
            lines.append(f"⏳ انقضا: {datetime.utcfromtimestamp(expire_ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
    if is_disabled:
        lines.append("")
        lines.append("🚫 اکانت شما در حال حاضر غیرفعال است. برای فعال‌سازی با پشتیبانی تماس بگیرید.")
    elif token and sub_domain:
        lines.append("")
        lines.append(f"🔗 لینک اشتراک: https://{sub_domain}/sub4me/{token}/")
        lines.append(f"🛰️ v2ray: https://{sub_domain}/sub4me/{token}/v2ray")
        lines.append(f"🧰 JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json")
    # Inline text configs removed from summary; they will be sent as code blocks in a separate message for one-tap copy.
    # Remove links if disabled
    if is_disabled:
        links = []
    return "\n".join(lines), token, links


@router.message(Command("account"))
async def handle_account(message: Message) -> None:
    if not message.from_user:
        return
    # Multi-service: list services first
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        svcs = []
        if u:
            svcs = (await session.execute(select(UserService).where(UserService.user_id == u.id).order_by(UserService.created_at.desc()))).scalars().all()
    if not svcs:
        # Fallback to single summary when no services exist yet
        await message.answer("در حال دریافت اطلاعات اکانت...")
        try:
            text, token, links = await _render_account_text(message.from_user.id)
            await message.answer(text, reply_markup=_acct_kb(bool(token), bool(links)))
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 404:
                await message.answer(
                    "اکانت شما در پنل یافت نشد. برای ساخت اکانت جدید یکی از پلن‌ها را خریداری کنید یا در صورت فعال بودن، از تریال استفاده کنید."
                )
            else:
                await message.answer("خطا در دریافت اطلاعات اکانت. لطفاً بعداً تلاش کنید.")
        except Exception:
            await message.answer("اکانت شما در سیستم یافت نشد یا در حال حاضر اطلاعات قابل دریافت نیست.")
        return
    # Render account summary + services list
    # Load phone from settings
    phone_txt = "—"
    async with session_scope() as session:
        row_p = await session.scalar(select(Setting).where(Setting.key == f"USER:{message.from_user.id}:PHONE"))
        if row_p and str(row_p.value).strip():
            phone_txt = str(row_p.value).strip()
    total = len(svcs)
    active_cnt = sum(1 for s in svcs if str(s.status or '').lower() == 'active')
    disabled_cnt = sum(1 for s in svcs if str(s.status or '').lower() == 'disabled')
    lines = [
        "🔎 اطلاعات حساب کاربری شما:",
        f"👤 آیدی عددی: {message.from_user.id}",
        f"📱 شماره: {phone_txt}",
        f"🧩 تعداد سرویس‌ها: {total} | ✅ فعال: {active_cnt} | 🚫 غیرفعال: {disabled_cnt}",
        "",
        "👤 سرویس‌های شما:",
    ]
    kb_rows: List[List[InlineKeyboardButton]] = []
    for s in svcs:
        lines.append(f"- {s.username} | وضعیت: {s.status}")
        kb_rows.append([InlineKeyboardButton(text=f"مدیریت {s.username}", callback_data=f"acct:svc:{s.id}")])
    if is_admin_uid(message.from_user.id):
        kb_rows.insert(0, [InlineKeyboardButton(text="⚙️ قیمت هر GB", callback_data="acct:pricegb:cfg")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data == "acct:refresh")
async def cb_account_refresh(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        text, token, links = await _render_account_text(cb.from_user.id)
        try:
            await cb.message.edit_text(text, reply_markup=_acct_kb(bool(token), bool(links)))
        except Exception:
            await cb.message.answer(text, reply_markup=_acct_kb(bool(token), bool(links)))
        await cb.answer("Updated")
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 404:
            await cb.message.answer(
                "اکانت شما در پنل یافت نشد. برای ساخت اکانت جدید یکی از پلن‌ها را خریداری کنید یا در صورت فعال بودن، از تریال استفاده کنید."
            )
        else:
            await cb.message.answer("خطا در دریافت اطلاعات اکانت. لطفاً بعداً تلاش کنید.")
        await cb.answer()
    except Exception:
        await cb.message.answer("اکانت شما در سیستم یافت نشد یا در حال حاضر اطلاعات قابل دریافت نیست.")
        await cb.answer()


@router.callback_query(F.data.startswith("acct:svc:"))
async def cb_account_service_view(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        sid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    async with session_scope() as session:
        s = await session.scalar(select(UserService).where(UserService.id == sid))
    if not s:
        await cb.answer("not found", show_alert=True)
        return
    # Render details for this service username
    try:
        client = await get_client()
        data = await client.get_user(s.username)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            await cb.message.answer("اکانت این سرویس در پنل یافت نشد.")
        else:
            await cb.message.answer("خطا در دریافت اطلاعات سرویس.")
        await cb.answer()
        return
    finally:
        try:
            await client.aclose()
        except Exception:
            pass
    status = str(data.get("status") or "")
    is_disabled = status.lower() == "disabled"
    token = None if is_disabled else (data.get("subscription_token") or (data.get("subscription_url", "").split("/")[-1] if data.get("subscription_url") else None))
    expire_ts = 0 if is_disabled else int(data.get("expire") or 0)
    data_limit = 0 if is_disabled else int(data.get("data_limit") or 0)
    used_traffic = 0 if is_disabled else int(data.get("used_traffic") or 0)
    remaining = max(data_limit - used_traffic, 0)
    lrm = "\u200E"
    lines = [
        f"👤 نام کاربری: {s.username}",
        f"📦 حجم کل: {_fmt_gb2(data_limit)}",
        f"📉 مصرف‌شده: {_fmt_gb2(used_traffic)}",
        f"📈 باقی‌مانده: {_fmt_gb2(remaining)}",
    ]
    if expire_ts > 0 and not is_disabled:
        try:
            if jdatetime:
                # Convert to Jalali date, Tehran time
                import pytz  # type: ignore
                tehran = pytz.timezone('Asia/Tehran')
                dt = datetime.fromtimestamp(expire_ts, tehran)
                jd = jdatetime.datetime.fromgregorian(datetime=dt)
                lines.append(f"⏳ انقضا: {jd.strftime('%Y/%m/%d %H:%M')} 🇮🇷")
            else:
                lines.append(f"⏳ انقضا: {datetime.utcfromtimestamp(expire_ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        except Exception:
            lines.append(f"⏳ انقضا: {datetime.utcfromtimestamp(expire_ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
    if is_disabled:
        lines.append("")
        lines.append("🚫 این سرویس در حال حاضر غیرفعال است.")
    elif token and sub_domain:
        lines.append("")
        lines.append(f"🔗 لینک اشتراک: https://{sub_domain}/sub4me/{token}/")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 کانفیگ‌ها (متنی)", callback_data=f"acct:links:svc:{s.id}"), InlineKeyboardButton(text="📋 کپی همه", callback_data=f"acct:copyall:svc:{s.id}")],
        [InlineKeyboardButton(text="🔳 QR اشتراک", callback_data=f"acct:qr:svc:{s.id}")],
        [InlineKeyboardButton(text="➕ خرید حجم اضافه", callback_data=f"acct:buygb:svc:{s.id}")],
    ])
    await cb.message.answer("\n".join(lines), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "acct:links")
async def cb_account_links(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    # Resolve username from DB if exists
    username = tg_username(cb.from_user.id)
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if u and getattr(u, "marzban_username", None):
            username = u.marzban_username
    client = await get_client()
    try:
        data = await client.get_user(username)
        if str(data.get("status") or "").lower() == "disabled":
            await cb.message.answer("🚫 اکانت شما در حال حاضر غیرفعال است.")
            await cb.answer()
            return
        links = list(map(str, data.get("links") or []))
    finally:
        await client.aclose()
    if not links:
        await cb.message.answer("هیچ کانفیگ مستقیمی از پنل دریافت نشد.")
        await cb.answer()
        return
    encoded = [html.escape(s.strip()) for s in links if s and s.strip()]
    blocks = [f"<pre>{s}</pre>" for s in encoded]
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📋 کپی همه", callback_data="acct:copyall")]])
    body = "\n\n".join(blocks)
    if len(body) <= 3500 and len(body) > 0:
        await cb.message.answer(body, reply_markup=kb, parse_mode="HTML")
    else:
        chunk: List[str] = []
        size = 0
        for b in blocks:
            entry = ("\n\n" if chunk else "") + b
            if size + len(entry) > 3500:
                await cb.message.answer("\n\n".join(chunk), parse_mode="HTML")
                chunk = [b]
                size = len(b)
                continue
            chunk.append(b)
            size += len(entry)
        if chunk:
            await cb.message.answer("\n\n".join(chunk), reply_markup=kb, parse_mode="HTML")
    await cb.answer("Sent")


@router.callback_query(F.data == "acct:revoke")
async def cb_account_revoke(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    username = tg_username(cb.from_user.id)
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if u and getattr(u, "marzban_username", None):
            username = u.marzban_username
    try:
        await marz_revoke_sub(username)
    except Exception:
        await cb.answer("خطا در بروزرسانی لینک", show_alert=True)
        return
    # Refresh text
    text, token, links = await _render_account_text(cb.from_user.id)
    try:
        await cb.message.edit_text(text, reply_markup=_acct_kb(bool(token), bool(links)))
    except Exception:
        await cb.message.answer(text, reply_markup=_acct_kb(bool(token), bool(links)))
    await cb.answer("Link rotated")


@router.callback_query(F.data.startswith("acct:links:svc:"))
async def cb_account_links_svc(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        sid = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    async with session_scope() as session:
        s = await session.scalar(select(UserService).where(UserService.id == sid))
    if not s:
        await cb.answer("not found", show_alert=True)
        return
    client = await get_client()
    try:
        data = await client.get_user(s.username)
        if str(data.get("status") or "").lower() == "disabled":
            await cb.message.answer("🚫 سرویس غیرفعال است.")
            await cb.answer()
            return
        links = list(map(str, data.get("links") or []))
    finally:
        await client.aclose()
    if not links:
        await cb.message.answer("هیچ کانفیگ مستقیمی از پنل دریافت نشد.")
        await cb.answer()
        return
    encoded = [html.escape(ss.strip()) for ss in links if ss and ss.strip()]
    blocks = [f"<pre>{s}</pre>" for s in encoded]
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📋 کپی همه", callback_data=f"acct:copyall:svc:{sid}")]])
    body = "\n\n".join(blocks)
    if len(body) <= 3500 and len(body) > 0:
        await cb.message.answer(body, reply_markup=kb, parse_mode="HTML")
    else:
        chunk: List[str] = []
        size = 0
        for b in blocks:
            entry = ("\n\n" if chunk else "") + b
            if size + len(entry) > 3500:
                await cb.message.answer("\n\n".join(chunk), parse_mode="HTML")
                chunk = [b]
                size = len(b)
                continue
            chunk.append(b)
            size += len(entry)
        if chunk:
            await cb.message.answer("\n\n".join(chunk), reply_markup=kb, parse_mode="HTML")
    await cb.answer("Sent")


@router.callback_query(F.data == "acct:qr")
async def cb_account_qr(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    username = tg_username(cb.from_user.id)
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if u and getattr(u, "marzban_username", None):
            username = u.marzban_username
    client = await get_client()
    try:
        data = await client.get_user(username)
        if str(data.get("status") or "").lower() == "disabled":
            await cb.answer("غیرفعال است", show_alert=True)
            return
        token = data.get("subscription_token") or (data.get("subscription_url", "").split("/")[-1] if data.get("subscription_url") else None)
    finally:
        await client.aclose()
    if not token:
        await cb.answer("لینک اشتراک یافت نشد.", show_alert=True)
        return
    sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
    url = f"https://{sub_domain}/sub4me/{token}/" if sub_domain else (data.get("subscription_url") or "")
    if not url:
        await cb.answer("URL اشتراک نامعتبر است.", show_alert=True)
        return
    # Use a simple QR generation service URL (Telegram fetches by URL)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={url}"
    try:
        await cb.message.answer_photo(qr_url, caption="QR اشتراک شما")
    except Exception:
        await cb.message.answer(url)
    await cb.answer()


def _get_extra_gb_price_tmn() -> int:
    # Try settings; fallback to ENV; else default
    import os
    try:
        # Note: synchronous helper; called inside handlers
        # Will read from DB in async contexts where needed
        val_env = os.getenv("EXTRA_GB_PRICE_TMN", "20000").strip()
        return int(val_env) if val_env.isdigit() else 20000
    except Exception:
        return 20000

# Pending map: user_id -> (service_id, gb)
_EXTRA_GB_PENDING: Dict[int, Tuple[int, Decimal]] = {}
# Admin price pending: admin_id -> True
_ADMIN_PRICE_PENDING: Dict[int, bool] = {}


@router.callback_query(F.data.startswith("acct:buygb:svc:"))
async def cb_account_buy_gb_svc(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        sid = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    # Read price from settings if exists
    price_tmn = _get_extra_gb_price_tmn()
    try:
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "EXTRA_GB_PRICE_TMN"))
            if row and str(row.value).strip().isdigit():
                price_tmn = int(str(row.value).strip())
    except Exception:
        pass
    _EXTRA_GB_PENDING[cb.from_user.id] = (sid, Decimal(0))
    await cb.message.answer(f"لطفاً میزان حجم اضافه (به GB) را وارد کنید.\n💵 قیمت هر GB: {price_tmn:,} تومان")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _EXTRA_GB_PENDING and isinstance(getattr(m, "text", None), str))
async def msg_account_buy_gb_amount(message: Message) -> None:
    user_id = message.from_user.id
    txt = (message.text or "").strip().replace(",", ".")
    try:
        gb = Decimal(txt)
        if gb <= 0:
            raise ValueError
    except Exception:
        await message.answer("مقدار نامعتبر است. یک عدد مثبت (مثلاً 1.5) ارسال کنید.")
        return
    tup = _EXTRA_GB_PENDING.get(user_id)
    if not tup:
        await message.answer("درخواست نامعتبر.")
        return
    sid, _ = tup
    # Load price
    price_tmn = _get_extra_gb_price_tmn()
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == "EXTRA_GB_PRICE_TMN"))
        if row and str(row.value).strip().isdigit():
            price_tmn = int(str(row.value).strip())
    cost_tmn = int((Decimal(price_tmn) * gb))
    _EXTRA_GB_PENDING[user_id] = (sid, gb)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تایید ✅", callback_data="acct:buygb:ok"), InlineKeyboardButton(text="انصراف ❌", callback_data="acct:buygb:cancel")]])
    await message.answer(f"آیا از خرید {gb}GB حجم اضافه اطمینان دارید؟\n💵 هزینه: {cost_tmn:,} تومان", reply_markup=kb)


@router.callback_query(F.data == "acct:buygb:cancel")
async def cb_account_buy_gb_cancel(cb: CallbackQuery) -> None:
    _EXTRA_GB_PENDING.pop(cb.from_user.id, None)
    await cb.answer("لغو شد")


@router.callback_query(F.data == "acct:buygb:ok")
async def cb_account_buy_gb_ok(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    tup = _EXTRA_GB_PENDING.get(cb.from_user.id)
    if not tup:
        await cb.answer("منقضی شده", show_alert=True)
        return
    sid, gb = tup
    # Load service, user and price
    async with session_scope() as session:
        s = await session.scalar(select(UserService).where(UserService.id == sid))
        u = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if not (s and u):
            _EXTRA_GB_PENDING.pop(cb.from_user.id, None)
            await cb.answer("یافت نشد", show_alert=True)
            return
        price_tmn = _get_extra_gb_price_tmn()
        row = await session.scalar(select(Setting).where(Setting.key == "EXTRA_GB_PRICE_TMN"))
        if row and str(row.value).strip().isdigit():
            price_tmn = int(str(row.value).strip())
        cost_irr = (Decimal(price_tmn) * Decimal(10)) * gb
        balance = Decimal(str(u.balance or 0))
        if balance < cost_irr:
            _EXTRA_GB_PENDING.pop(cb.from_user.id, None)
            await cb.answer("موجودی کافی نیست", show_alert=True)
            await cb.message.answer(
                "موجودی کیف پول شما کافی نیست. ابتدا شارژ کنید.\n"
                f"💵 هزینه: {int(cost_irr/Decimal('10')):,} تومان"
            )
            return
        # Deduct
        u.balance = balance - cost_irr
        await session.commit()
    # Apply add GB
    try:
        from app.services import marzban_ops as ops
        await ops.add_data_gb(s.username, float(gb))
    except Exception:
        await cb.message.answer("خطا در افزودن حجم.")
        await cb.answer()
        return
    _EXTRA_GB_PENDING.pop(cb.from_user.id, None)
    await cb.message.answer(
        f"✅ {gb}GB به سرویس {s.username} افزوده شد.\n💳 مبلغ کسر شده: {int((Decimal(price_tmn)*Decimal(10)*gb)/Decimal('10')):,} تومان"
    )
    await cb.answer("OK")


@router.callback_query(F.data.startswith("acct:qr:svc:"))
async def cb_account_qr_svc(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        sid = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    async with session_scope() as session:
        s = await session.scalar(select(UserService).where(UserService.id == sid))
    if not s:
        await cb.answer("not found", show_alert=True)
        return
    client = await get_client()
    try:
        data = await client.get_user(s.username)
        if str(data.get("status") or "").lower() == "disabled":
            await cb.answer("غیرفعال است", show_alert=True)
            return
        token = data.get("subscription_token") or (data.get("subscription_url", "").split("/")[-1] if data.get("subscription_url") else None)
    finally:
        await client.aclose()
    if not token:
        await cb.answer("لینک اشتراک یافت نشد.", show_alert=True)
        return
    sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
    url = f"https://{sub_domain}/sub4me/{token}/" if sub_domain else (data.get("subscription_url") or "")
    if not url:
        await cb.answer("URL اشتراک نامعتبر است.", show_alert=True)
        return
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={url}"
    try:
        await cb.message.answer_photo(qr_url, caption="QR اشتراک سرویس")
    except Exception:
        await cb.message.answer(url)
    await cb.answer()


@router.callback_query(F.data.startswith("acct:copyall:svc:"))
async def cb_account_copy_all_svc(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        sid = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("bad id", show_alert=True)
        return
    async with session_scope() as session:
        s = await session.scalar(select(UserService).where(UserService.id == sid))
    if not s:
        await cb.answer("not found", show_alert=True)
        return
    client = await get_client()
    try:
        data = await client.get_user(s.username)
        if str(data.get("status") or "").lower() == "disabled":
            await cb.answer("غیرفعال است", show_alert=True)
            return
        token = data.get("subscription_token") or (data.get("subscription_url", "").split("/")[-1] if data.get("subscription_url") else None)
        links = list(map(str, data.get("links") or []))
        sub_url = data.get("subscription_url") or ""
    finally:
        await client.aclose()
    sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
    url = f"https://{sub_domain}/sub4me/{token}/" if (token and sub_domain) else sub_url
    parts: List[str] = []
    if url:
        parts.append(url)
        parts.append(f"{url}v2ray")
        parts.append(f"{url}v2ray-json")
    for s2 in links:
        ss = s2.strip()
        if ss:
            parts.append(ss)
    if not parts:
        await cb.answer("محتوایی برای کپی وجود ندارد.", show_alert=True)
        return
    encoded = [html.escape(p) for p in parts]
    blocks = [f"<pre>{e}</pre>" for e in encoded]
    header = "🧩 کانفیگ‌های متنی:\n\n"
    body = header + "\n\n".join(blocks)
    if len(body) <= 3500:
        await cb.message.answer(body, parse_mode="HTML")
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
            await cb.message.answer((header if first else "") + "\n\n".join(chunk), parse_mode="HTML")
    await cb.answer("Ready to copy")

@router.callback_query(F.data == "acct:pricegb:cfg")
async def cb_account_price_gb_cfg(cb: CallbackQuery) -> None:
    if not cb.from_user or not is_admin_uid(cb.from_user.id):
        await cb.answer("No access", show_alert=True)
        return
    price_tmn = _get_extra_gb_price_tmn()
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == "EXTRA_GB_PRICE_TMN"))
        if row and str(row.value).strip().isdigit():
            price_tmn = int(str(row.value).strip())
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تغییر قیمت ✏️", callback_data="acct:pricegb:set")]])
    await cb.message.answer(f"⚙️ قیمت هر GB حجم اضافه: {price_tmn:,} تومان", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "acct:pricegb:set")
async def cb_account_price_gb_set(cb: CallbackQuery) -> None:
    if not cb.from_user or not is_admin_uid(cb.from_user.id):
        await cb.answer("No access", show_alert=True)
        return
    _ADMIN_PRICE_PENDING[cb.from_user.id] = True
    await cb.message.answer("مبلغ هر GB را به تومان ارسال کنید (عدد صحیح).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and _ADMIN_PRICE_PENDING.get(m.from_user.id, False) and isinstance(getattr(m, "text", None), str))
async def msg_account_price_gb_set(message: Message) -> None:
    admin_id = message.from_user.id
    if not is_admin_uid(admin_id):
        _ADMIN_PRICE_PENDING.pop(admin_id, None)
        return
    txt = (message.text or "").strip()
    if not txt.isdigit():
        await message.answer("عدد صحیح به تومان ارسال کنید (مثلاً 20000).")
        return
    val = int(txt)
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == "EXTRA_GB_PRICE_TMN"))
        if not row:
            session.add(Setting(key="EXTRA_GB_PRICE_TMN", value=str(val)))
        else:
            row.value = str(val)
        await session.commit()
    _ADMIN_PRICE_PENDING.pop(admin_id, None)
    await message.answer(f"ذخیره شد. قیمت هر GB: {val:,} تومان")


@router.callback_query(F.data == "acct:copyall")
async def cb_account_copy_all(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    username = tg_username(cb.from_user.id)
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if u and getattr(u, "marzban_username", None):
            username = u.marzban_username
    client = await get_client()
    try:
        data = await client.get_user(username)
        if str(data.get("status") or "").lower() == "disabled":
            await cb.answer("غیرفعال است", show_alert=True)
            return
        token = data.get("subscription_token") or (data.get("subscription_url", "").split("/")[-1] if data.get("subscription_url") else None)
        links = list(map(str, data.get("links") or []))
        sub_url = data.get("subscription_url") or ""
    finally:
        await client.aclose()
    sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
    url = f"https://{sub_domain}/sub4me/{token}/" if (token and sub_domain) else sub_url
    parts: List[str] = []
    if url:
        parts.append(url)
        parts.append(f"{url}v2ray")
        parts.append(f"{url}v2ray-json")
    for s in links:
        ss = s.strip()
        if ss:
            parts.append(ss)
    if not parts:
        await cb.answer("محتوایی برای کپی وجود ندارد.", show_alert=True)
        return
    # Send as header + code blocks for easy copying
    encoded = [html.escape(p) for p in parts]
    blocks = [f"<pre>{e}</pre>" for e in encoded]
    header = "🧩 کانفیگ‌های متنی:\n\n"
    body = header + "\n\n".join(blocks)
    if len(body) <= 3500:
        await cb.message.answer(body, parse_mode="HTML")
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
            await cb.message.answer((header if first else "") + "\n\n".join(chunk), parse_mode="HTML")
    await cb.answer("Ready to copy")


# ===== Username rename flow (weekly limit) =====

def _gen_username_random(tg_id: int) -> str:
    import random, string
    suffix = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(3))
    return f"tg{tg_id}{suffix}"


async def _can_rename_now(tg_id: int) -> Tuple[bool, str | None]:
    # Returns (allowed, msg_if_blocked)
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:LAST_RENAME_AT"))
    if not row:
        return True, None
    try:
        last = datetime.fromisoformat(str(row.value))
    except Exception:
        return True, None
    delta = datetime.utcnow() - last
    if delta >= timedelta(days=7):
        return True, None
    remain = timedelta(days=7) - delta
    days = remain.days
    hours = remain.seconds // 3600
    return False, f"⏳ امکان تغییر یوزرنیم هر ۷ روز یک‌بار است. زمان باقی‌مانده: {days} روز و {hours} ساعت."


@router.callback_query(F.data == "acct:rename")
async def cb_account_rename(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    allowed, msg = await _can_rename_now(cb.from_user.id)
    if not allowed:
        await cb.message.answer(msg or "فعلاً امکان تغییر یوزرنیم ندارید.")
        await cb.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ساخت یوزرنیم رندوم", callback_data="acct:rn:rnd")],
        [InlineKeyboardButton(text="یوزرنیم دلخواه ✏️", callback_data="acct:rn:cst")],
        [InlineKeyboardButton(text="انصراف ❌", callback_data="acct:rn:cancel")],
    ])
    await cb.message.answer("لطفاً روش تغییر یوزرنیم را انتخاب کنید:", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "acct:rn:cancel")
async def cb_account_rename_cancel(cb: CallbackQuery) -> None:
    _RENAME_CUSTOM_PENDING.pop(cb.from_user.id, None)
    await cb.answer("لغو شد")


@router.callback_query(F.data == "acct:rn:rnd")
async def cb_account_rename_random(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    candidate = _gen_username_random(cb.from_user.id)
    # ensure uniqueness vs DB
    async with session_scope() as session:
        exists = await session.scalar(select(User.id).where(User.marzban_username == candidate))
        if exists:
            candidate = _gen_username_random(cb.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تایید ✅", callback_data=f"acct:rn:fin:{candidate}")],
        [InlineKeyboardButton(text="انصراف ❌", callback_data="acct:rn:cancel")],
    ])
    await cb.message.answer(f"آیا از تغییر یوزرنیم به «{candidate}» اطمینان دارید؟", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "acct:rn:cst")
async def cb_account_rename_custom(cb: CallbackQuery) -> None:
    _RENAME_CUSTOM_PENDING[cb.from_user.id] = True
    await cb.message.answer("یوزرنیم جدید را ارسال کنید (فقط حروف کوچک و ارقام، حداقل ۶ کاراکتر).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _RENAME_CUSTOM_PENDING and isinstance(getattr(m, "text", None), str))
async def msg_account_rename_custom(message: Message) -> None:
    user_id = message.from_user.id
    txt = (message.text or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9]{6,}", txt):
        await message.answer("فرمت نامعتبر است. فقط حروف کوچک و ارقام، حداقل ۶ کاراکتر.")
        return
    async with session_scope() as session:
        exists = await session.scalar(select(User.id).where(User.marzban_username == txt))
        if exists:
            await message.answer("این یوزرنیم قبلاً استفاده شده است. مورد دیگری ارسال کنید.")
            return
        u = await session.scalar(select(User).where(User.telegram_id == user_id))
        old = u.marzban_username if u else tg_username(user_id)
    if txt == old:
        await message.answer("یوزرنیم جدید با قبلی یکسان است.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تایید ✅", callback_data=f"acct:rn:fin:{txt}")],
        [InlineKeyboardButton(text="انصراف ❌", callback_data="acct:rn:cancel")],
    ])
    await message.answer(f"آیا از تغییر یوزرنیم به «{txt}» اطمینان دارید؟", reply_markup=kb)


@router.callback_query(F.data.startswith("acct:rn:fin:"))
async def cb_account_rename_finish(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        new_un = cb.data.split(":")[3]
    except Exception:
        await cb.answer("شناسه نامعتبر است", show_alert=True)
        return
    allowed, msg = await _can_rename_now(cb.from_user.id)
    if not allowed:
        await cb.message.answer(msg or "فعلاً امکان تغییر یوزرنیم ندارید.")
        await cb.answer()
        return
    async with session_scope() as session:
        u = await session.scalar(select(User).where(User.telegram_id == cb.from_user.id))
        if not u:
            await cb.answer("ابتدا /start را بزنید.", show_alert=True)
            return
        old = u.marzban_username or tg_username(cb.from_user.id)
        if new_un == old:
            await cb.answer("بدون تغییر", show_alert=True)
            return
        u.marzban_username = new_un
        # Save last rename time
        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{cb.from_user.id}:LAST_RENAME_AT"))
        now_iso = datetime.utcnow().isoformat()
        if not row:
            session.add(Setting(key=f"USER:{cb.from_user.id}:LAST_RENAME_AT", value=now_iso))
        else:
            row.value = now_iso
        await session.commit()
    try:
        await ops_replace_username(old, new_un, note="user rename")
    except Exception:
        await cb.message.answer("خطا در تغییر یوزرنیم در پنل.")
        await cb.answer()
        return
    _RENAME_CUSTOM_PENDING.pop(cb.from_user.id, None)
    await cb.message.answer("✅ یوزرنیم با موفقیت تغییر کرد.")
    # Refresh view
    try:
        text, token, links = await _render_account_text(cb.from_user.id)
        await cb.message.answer(text, reply_markup=_acct_kb(bool(token), bool(links)))
    except Exception:
        pass
    await cb.answer("Renamed")
