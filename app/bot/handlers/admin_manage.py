from __future__ import annotations

import os
from typing import Dict, List, Tuple

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, update

from app.utils.username import tg_username
from app.services import marzban_ops as ops
from app.db.session import session_scope
from app.db.models import Plan

router = Router()


def _get_admin_ids() -> List[int]:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "").strip()
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            pass
    return ids


def _require_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in _get_admin_ids())


# ========================
# Admin commands (slash)
# ========================

@router.message(Command("admin_create"))
async def admin_create(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    username = parts[1].strip() if len(parts) == 2 else tg_username(message.from_user.id)  # default to caller
    await message.answer(f"در حال ایجاد کاربر {username}...")
    try:
        await ops.create_user_minimal(username, note="admin:create")
        await message.answer(f"ایجاد شد: {username}")
    except Exception as e:
        await message.answer(f"خطا در ایجاد: {e}")


@router.message(Command("admin_delete"))
async def admin_delete(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("فرمت: /admin_delete <username>")
        return
    username = parts[1].strip()
    await message.answer(f"حذف کاربر {username}...")
    try:
        await ops.delete_user(username)
        await message.answer("حذف شد.")
    except Exception as e:
        await message.answer(f"خطا در حذف: {e}")


@router.message(Command("admin_reset"))
async def admin_reset(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("فرمت: /admin_reset <username>")
        return
    username = parts[1].strip()
    try:
        await ops.reset_user(username)
        await message.answer("reset انجام شد.")
    except Exception as e:
        await message.answer(f"خطا در reset: {e}")


@router.message(Command("admin_revoke"))
async def admin_revoke(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("فرمت: /admin_revoke <username>")
        return
    username = parts[1].strip()
    try:
        await ops.revoke_sub(username)
        await message.answer("revoke_sub انجام شد.")
    except Exception as e:
        await message.answer(f"خطا در revoke: {e}")


@router.message(Command("admin_set"))
async def admin_set(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    # Format: /admin_set <username> <gb> <days>
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("فرمت: /admin_set <username> <GB> <DAYS>")
        return
    username = parts[1].strip()
    try:
        gb = float(parts[2])
        days = int(parts[3])
    except ValueError:
        await message.answer("مقادیر GB و DAYS نامعتبر است.")
        return
    await message.answer(f"تنظیم محدودیت برای {username}: {gb}GB / {days}d ...")
    try:
        await ops.update_user_limits(username, gb, days)
        await message.answer("اعمال شد.")
    except Exception as e:
        await message.answer(f"خطا در admin_set: {e}")


@router.message(Command("admin_get"))
async def admin_get(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("فرمت: /admin_get <username>")
        return
    username = parts[1].strip()
    try:
        info = await ops.get_user_summary(username)
        await message.answer(info["summary_text"])
        if info.get("subscription_url"):
            await message.answer(info["subscription_url"])
    except Exception as e:
        await message.answer(f"خطا در admin_get: {e}")


@router.message(Command("admin_status"))
async def admin_status(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("فرمت: /admin_status <username> <active|disabled|on_hold>")
        return
    username = parts[1].strip()
    status = parts[2].strip()
    try:
        await ops.set_status(username, status)
        await message.answer("اعمال شد.")
    except Exception as e:
        await message.answer(f"خطا در admin_status: {e}")


@router.message(Command("admin_addgb"))
async def admin_addgb(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("فرمت: /admin_addgb <username> <GB>")
        return
    username = parts[1].strip()
    try:
        gb = float(parts[2])
    except ValueError:
        await message.answer("مقدار GB نامعتبر است.")
        return
    try:
        await ops.add_data_gb(username, gb)
        await message.answer("اعمال شد.")
    except Exception as e:
        await message.answer(f"خطا در admin_addgb: {e}")


@router.message(Command("admin_extend"))
async def admin_extend(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("فرمت: /admin_extend <username> <DAYS>")
        return
    username = parts[1].strip()
    try:
        days = int(parts[2])
    except ValueError:
        await message.answer("مقدار DAYS نامعتبر است.")
        return
    try:
        await ops.extend_expire(username, days)
        await message.answer("اعمال شد.")
    except Exception as e:
        await message.answer(f"خطا در admin_extend: {e}")


@router.message(Command("admin_list_expired"))
async def admin_list_expired(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        rows = await ops.list_expired()
        if not rows:
            await message.answer("موردی یافت نشد.")
            return
        lines = []
        for r in rows[:20]:
            lines.append(f"- {r.get('username')} | status={r.get('status')} | expire={r.get('expire')}")
        await message.answer("Expired users (first 20):\n" + "\n".join(lines))
    except Exception as e:
        await message.answer(f"خطا در admin_list_expired: {e}")


@router.message(Command("admin_delete_expired"))
async def admin_delete_expired(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        res = await ops.delete_expired()
        await message.answer(f"Deleted expired: {res}")
    except Exception as e:
        await message.answer(f"خطا در admin_delete_expired: {e}")


# ========================
# Admin Plans Management (Buttons UI)
# ========================

PAGE_SIZE = 5
# price intent: admin_user_id -> (template_id, page)
_APLANS_PRICE_INTENT: Dict[int, Tuple[int, int]] = {}


def _fmt_plan_line(p: Plan) -> str:
    if p.data_limit_bytes and p.data_limit_bytes > 0:
        gb = p.data_limit_bytes / (1024 ** 3)
        limit_str = f"{gb:.0f}GB"
    else:
        limit_str = "نامحدود"
    dur_str = f"{p.duration_days}d" if p.duration_days and p.duration_days > 0 else "بدون محدودیت زمانی"
    price_irr = int(p.price or 0)
    price_tmn = price_irr // 10
    price_str = f"{price_tmn:,} تومان" if price_irr > 0 else "قیمت‌گذاری نشده"
    active_str = "فعال" if p.is_active else "غیرفعال"
    return f"{p.title} (ID: {p.template_id}) | حجم: {limit_str} | مدت: {dur_str} | قیمت: {price_str} | وضعیت: {active_str}"


async def admin_show_plans_menu(message: Message, page: int = 1) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    async with session_scope() as session:
        rows = (await session.execute(select(Plan).order_by(Plan.template_id))).scalars().all()
    if not rows:
        await message.answer("هیچ پلنی ثبت نشده است. ابتدا از همگام‌سازی با Marzban استفاده کنید.")
        return
    total = len(rows)
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    subset = rows[start:start + PAGE_SIZE]
    lines = [f"مدیریت پلن‌ها (صفحه {page}/{pages}):"]
    kb_rows: List[List[InlineKeyboardButton]] = []
    for p in subset:
        lines.append("- " + _fmt_plan_line(p))
        toggle_text = "🔁 غیرفعال‌سازی" if p.is_active else "✅ فعال‌سازی"
        kb_rows.append([
            InlineKeyboardButton(text="💵 قیمت", callback_data=f"aplans:setprice:{p.template_id}:{page}"),
            InlineKeyboardButton(text=toggle_text, callback_data=f"aplans:toggle:{p.template_id}:{page}"),
        ])
    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️ قبلی", callback_data=f"aplans:page:{page-1}"))
    if page < pages:
        nav.append(InlineKeyboardButton(text="بعدی ▶️", callback_data=f"aplans:page:{page+1}"))
    if nav:
        kb_rows.append(nav)
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.message(F.text == "⚙️ مدیریت پلن‌ها")
async def _btn_admin_plans(message: Message) -> None:
    await admin_show_plans_menu(message, page=1)


@router.callback_query(F.data.startswith("aplans:page:"))
async def cb_aplans_page(cb: CallbackQuery) -> None:
    if not cb.from_user or cb.from_user.id not in _get_admin_ids():
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        page = int(cb.data.split(":")[2])
    except Exception:
        page = 1
    await admin_show_plans_menu(cb.message, page=page)
    await cb.answer()


@router.callback_query(F.data.startswith("aplans:toggle:"))
async def cb_aplans_toggle(cb: CallbackQuery) -> None:
    if not cb.from_user or cb.from_user.id not in _get_admin_ids():
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        _, _, tpl, page = cb.data.split(":")
        tpl_id = int(tpl)
        page_num = int(page)
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    async with session_scope() as session:
        row = await session.scalar(select(Plan).where(Plan.template_id == tpl_id))
        if not row:
            await cb.answer("پلن یافت نشد", show_alert=True)
            return
        row.is_active = not bool(row.is_active)
        await session.commit()
    await admin_show_plans_menu(cb.message, page=page_num)
    await cb.answer("اعمال شد")


@router.callback_query(F.data.startswith("aplans:setprice:"))
async def cb_aplans_setprice(cb: CallbackQuery) -> None:
    if not cb.from_user or cb.from_user.id not in _get_admin_ids():
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        _, _, tpl, page = cb.data.split(":")
        tpl_id = int(tpl)
        page_num = int(page)
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    _APLANS_PRICE_INTENT[cb.from_user.id] = (tpl_id, page_num)
    await cb.message.answer("مب��غ جدید را به تومان ارسال کنید (مثلاً 150000 برای ۱۵۰ هزار تومان)")
    await cb.answer()


@router.message(F.text.regexp(r"^\d{3,10}$"))
async def admin_plan_price_input(message: Message) -> None:
    if not _require_admin(message):
        return
    uid = message.from_user.id if message.from_user else None
    if not uid or uid not in _APLANS_PRICE_INTENT:
        return
    tpl_id, page_num = _APLANS_PRICE_INTENT.pop(uid)
    try:
        toman = int(message.text)
        if toman <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. دوباره ارسال کنید یا دستور را تکرار کنید.")
        return
    irr = toman * 10
    async with session_scope() as session:
        row = await session.scalar(select(Plan).where(Plan.template_id == tpl_id))
        if not row:
            await message.answer("پلن یافت نشد.")
            return
        row.price = irr
        await session.commit()
    await message.answer(f"قیمت پلن تنظیم شد: {toman:,} تومان")
    # Re-show menu
    await admin_show_plans_menu(message, page=page_num)
