from __future__ import annotations

import os
from datetime import datetime
from typing import List, Tuple

from aiogram import Router, F
import httpx
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, func

from app.db.session import session_scope
from app.db.models import User, Order
from app.marzban.client import get_client
from app.services.marzban_ops import revoke_sub as marz_revoke_sub
from app.utils.username import tg_username

router = Router()


def _fmt_gb2(v: int) -> str:
    if v <= 0:
        return "نامحدود"
    return f"{v / (1024**3):.2f}GB"


def _acct_kb(has_token: bool, has_links: bool) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    rows.append([InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="acct:refresh")])
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
    username = tg_username(tg_id)
    # Load DB info
    reg_date_txt = "—"
    orders_count = 0
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if user:
            reg_date_txt = user.created_at.strftime('%Y-%m-%d %H:%M:%S') + " UTC"
            res = await session.execute(select(func.count(Order.id)).where(Order.user_id == user.id))
            orders_count = int(res.scalar() or 0)
    # Load Marzban info
    client = await get_client()
    try:
        data = await client.get_user(username)
    finally:
        await client.aclose()
    token = data.get("subscription_token") or (data.get("subscription_url", "").split("/")[-1] if data.get("subscription_url") else None)
    expire_ts = int(data.get("expire") or 0)
    data_limit = int(data.get("data_limit") or 0)
    used_traffic = int(data.get("used_traffic") or 0)
    remaining = max(data_limit - used_traffic, 0)
    links: List[str] = list(map(str, data.get("links") or []))
    # Emoji-rich header
    lines = [
        f"👤 نام کاربری: {username}",
        f"🆔 شناسه تلگرام: {tg_id}",
        f"🗓️ تاریخ ثبت‌نام: {reg_date_txt}",
        f"🧾 تعداد خریدها: {orders_count}",
        f"📦 حجم کل: {_fmt_gb2(data_limit)}",
        f"📉 مصرف‌شده: {_fmt_gb2(used_traffic)}",
        f"📈 باقی‌مانده: {_fmt_gb2(remaining)}",
    ]
    if expire_ts > 0:
        lines.append(f"⏳ انقضا: {datetime.utcfromtimestamp(expire_ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
    if token and sub_domain:
        lines.append("")
        lines.append(f"🔗 لینک اشتراک: https://{sub_domain}/sub4me/{token}/")
        lines.append(f"🛰️ v2ray: https://{sub_domain}/sub4me/{token}/v2ray")
        lines.append(f"🧰 JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json")
    # Inline text configs section (separated by blank lines, truncated to avoid Telegram limits)
    if links:
        lines.append("")
        lines.append("🧩 کانفیگ‌های متنی:")
        max_len = 3500
        cur_len = 0
        for s in links:
            s = s.strip()
            if not s:
                continue
            add = ("\n" if (lines and lines[-1] != "") else "") + s + "\n"
            if cur_len + len(add) > max_len:
                lines.append("… (برای مشاهده همه، دکمه \"📋 کپی همه\" را بزنید)")
                break
            lines.append(s)
            lines.append("")
            cur_len += len(add)
    return "\n".join(lines), token, links


@router.message(Command("account"))
async def handle_account(message: Message) -> None:
    if not message.from_user:
        return
    await message.answer("در حال دریافت اطلاعات اکانت...")
    try:
        text, token, links = await _render_account_text(message.from_user.id)
        await message.answer(text, reply_markup=_acct_kb(bool(token), bool(links)))
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 404:
            await message.answer(
                "ا��انت شما در پنل یافت نشد. برای ساخت اکانت جدید یکی از پلن‌ها را خریداری کنید یا در صورت فعال بودن، از تریال استفاده کنید."
            )
        else:
            await message.answer("خطا در دریافت اطلاعات اکانت. لطفاً بعداً تلاش کنید.")
    except Exception:
        await message.answer("اکانت شما در سیستم یافت نشد یا در حال حاضر اطلاعات قابل دریافت نیست.")


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


@router.callback_query(F.data == "acct:links")
async def cb_account_links(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    username = tg_username(cb.from_user.id)
    client = await get_client()
    try:
        data = await client.get_user(username)
        links = data.get("links") or []
    finally:
        await client.aclose()
    if not links:
        await cb.message.answer("هیچ کانفیگ مستقیمی از پنل دریافت نشد.")
        await cb.answer()
        return
    # Send links in chunks, separated with blank lines for easy copy
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
        await cb.message.answer("\n\n".join(chunk))
    await cb.answer("Sent")


@router.callback_query(F.data == "acct:revoke")
async def cb_account_revoke(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    username = tg_username(cb.from_user.id)
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


@router.callback_query(F.data == "acct:qr")
async def cb_account_qr(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    username = tg_username(cb.from_user.id)
    client = await get_client()
    try:
        data = await client.get_user(username)
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


@router.callback_query(F.data == "acct:copyall")
async def cb_account_copy_all(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    username = tg_username(cb.from_user.id)
    client = await get_client()
    try:
        data = await client.get_user(username)
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
    text = "\n\n".join(parts)
    await cb.message.answer(text)
    await cb.answer("Ready to copy")
