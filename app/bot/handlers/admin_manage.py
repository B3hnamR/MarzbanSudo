from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple
import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, func

from app.utils.username import tg_username
from app.services import marzban_ops as ops
from app.db.session import session_scope
from app.db.models import Plan, Order
from app.services.security import (
    has_capability_async,
    CAP_PLANS_MANAGE,
    CAP_PLANS_CREATE,
    CAP_PLANS_EDIT,
    CAP_PLANS_DELETE,
    CAP_PLANS_SET_PRICE,
    CAP_PLANS_TOGGLE_ACTIVE,
)

router = Router()


# ========================
# Admin commands (slash)
# ========================


def _admin_ids() -> List[int]:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "").strip()
    out: List[int] = []
    for p in raw.split(','):
        p = p.strip()
        if p.isdigit():
            out.append(int(p))
    return out


@router.message(Command("admin_create"))
async def admin_create(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    username = parts[1].strip() if len(parts) == 2 else tg_username(message.from_user.id)
    await message.answer(f"در حال ایجاد کاربر {username}...")
    try:
        await ops.create_user_minimal(username, note="admin:create")
        await message.answer(f"ایجاد شد: {username}")
    except Exception as e:
        await message.answer(f"خطا در ایجاد: {e}")


@router.message(Command("admin_delete"))
async def admin_delete(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE)):
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
# intents
_APLANS_PRICE_INTENT: Dict[int, Tuple[int, int]] = {}
_APLANS_CREATE_INTENT: Dict[int, Dict[str, Any]] = {}
_APLANS_FIELD_INTENT: Dict[int, Tuple[str, int, int]] = {}  # (field, tpl_id, page)


def _fmt_plan_line(p: Plan) -> str:
    gb_str = f"{(p.data_limit_bytes or 0) // (1024**3)}GB" if (p.data_limit_bytes or 0) > 0 else "نامحدود"
    d_str = f"{p.duration_days}d" if (p.duration_days or 0) > 0 else "بدون محدودیت زمانی"
    tmn = (int(p.price or 0)) // 10
    price_str = f"{tmn:,} تومان" if tmn > 0 else "قیمت‌گذاری نشده"
    st = "فعال" if p.is_active else "غیرفعال"
    return f"#{p.template_id} — {p.title} | حجم: {gb_str} | مدت: {d_str} | قیمت: {price_str} | وضعیت: {st}"


async def admin_show_plans_menu(message: Message, page: int = 1, requester_id: int | None = None) -> None:
    uid = requester_id or (message.from_user.id if message.from_user else None)
    if not (uid and await has_capability_async(uid, CAP_PLANS_MANAGE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    async with session_scope() as session:
        rows = (await session.execute(select(Plan).order_by(Plan.template_id))).scalars().all()
    if not rows:
        await message.answer("هیچ پلنی ثبت نشده است. از «➕ ایجاد پلن جدید» استفاده کنید یا از همگام‌سازی Marzban بهره ببرید.")
        return
    total = len(rows)
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    subset = rows[start:start + PAGE_SIZE]
    lines = [f"مدیریت پلن‌ها (صفحه {page}/{pages})"]
    kb_rows: List[List[InlineKeyboardButton]] = []
    for p in subset:
        lines.append(_fmt_plan_line(p))
        row_btns: List[InlineKeyboardButton] = []
        row_btns.append(InlineKeyboardButton(text="💵 قیمت", callback_data=f"aplans:setprice:{p.template_id}:{page}"))
        row_btns.append(InlineKeyboardButton(text=("🔁 غیرفعال‌سازی" if p.is_active else "✅ فعال‌سازی"), callback_data=f"aplans:toggle:{p.template_id}:{page}"))
        row_btns.append(InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"aplans:edit:{p.template_id}:{page}"))
        row_btns.append(InlineKeyboardButton(text="🗑️ حذف", callback_data=f"aplans:delete:{p.template_id}:{page}"))
        kb_rows.append(row_btns)
    # Create new plan button
    kb_rows.append([InlineKeyboardButton(text="➕ ایجاد پلن جدید", callback_data=f"aplans:create:{page}")])
    # Pagination
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
    await admin_show_plans_menu(message, page=1, requester_id=message.from_user.id if message.from_user else None)


@router.callback_query(F.data.startswith("aplans:page:"))
async def cb_aplans_page(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_PLANS_MANAGE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        page = int(cb.data.split(":")[2])
    except Exception:
        page = 1
    await admin_show_plans_menu(cb.message, page=page, requester_id=cb.from_user.id if cb.from_user else None)
    await cb.answer()


@router.callback_query(F.data.startswith("aplans:toggle:"))
async def cb_aplans_toggle(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_PLANS_TOGGLE_ACTIVE)):
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
    if await has_capability_async(cb.from_user.id, CAP_PLANS_MANAGE):
        await admin_show_plans_menu(cb.message, page=page_num, requester_id=cb.from_user.id)
    await cb.answer("اعمال شد")


@router.callback_query(F.data.startswith("aplans:setprice:"))
async def cb_aplans_setprice(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_PLANS_SET_PRICE)):
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
    await cb.message.answer("مبلغ جدید را به تومان ارسال کنید (مثلاً 150000 برای ۱۵۰ هزار تومان)")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _APLANS_PRICE_INTENT and isinstance(getattr(m, "text", None), str) and re.match(r"^\d{3,10}$", m.text))
async def admin_plan_price_input(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_PLANS_SET_PRICE)):
        return
    uid = message.from_user.id
    tpl_id, page_num = _APLANS_PRICE_INTENT.pop(uid)
    try:
        toman = int(message.text)
        if toman <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. دوباره ارسال کنید یا عملیات را از ابتدا انجام دهید.")
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
    if await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE):
        await admin_show_plans_menu(message, page=page_num, requester_id=message.from_user.id)


# Create Plan flow (step-by-step)
@router.callback_query(F.data.startswith("aplans:create:"))
async def cb_aplans_create(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_PLANS_CREATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        page_num = int(cb.data.split(":")[2])
    except Exception:
        page_num = 1
    _APLANS_CREATE_INTENT[cb.from_user.id] = {"page": page_num, "step": "title", "title": None, "gb": None, "days": None, "price_tmn": None}
    await cb.message.answer("عنوان پلن را ارسال کنید (مثلاً 30D-20GB)")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _APLANS_CREATE_INTENT and isinstance(getattr(m, "text", None), str))
async def admin_plan_create_steps(message: Message) -> None:
    uid = message.from_user.id if message.from_user else None
    # Capability check on every step
    if not await has_capability_async(uid, CAP_PLANS_CREATE):
        _APLANS_CREATE_INTENT.pop(uid, None)
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    ctx = _APLANS_CREATE_INTENT[uid]
    step = ctx.get("step")
    if step == "title":
        title = message.text.strip()
        if not title:
            await message.answer("عنوان نامعتبر است. دوباره ارسال کنید.")
            return
        ctx["title"] = title
        ctx["step"] = "gb"
        await message.answer("حجم را به گیگابایت ارسال کنید (عدد صحیح؛ 0 برای نامحدود)")
        return
    if step == "gb":
        try:
            gb = int(message.text.strip())
            if gb < 0:
                raise ValueError
        except Exception:
            await message.answer("مقدار حجم نامعتبر است. یک عدد صحیح یا 0 ارسال کنید.")
            return
        ctx["gb"] = gb
        ctx["step"] = "days"
        await message.answer("مدت را به روز ارسال کنید (عدد صحیح؛ 0 برای بدون محدودیت)")
        return
    if step == "days":
        try:
            days = int(message.text.strip())
            if days < 0:
                raise ValueError
        except Exception:
            await message.answer("مقدار مدت نامعتبر است. یک عدد صحیح یا 0 ارسال کنید.")
            return
        ctx["days"] = days
        ctx["step"] = "price"
        await message.answer("قیمت را به تومان ارسال کنید (عدد صحیح؛ مثلاً 150000)")
        return
    if step == "price":
        try:
            tmn = int(message.text.strip())
            if tmn <= 0:
                raise ValueError
        except Exception:
            await message.answer("مبلغ نامعتبر است. یک عدد صحیح ارسال کنید.")
            return
        ctx["price_tmn"] = tmn
        # Create record
        title = ctx["title"]
        gb = int(ctx["gb"]) or 0
        days = int(ctx["days"]) or 0
        irr = tmn * 10
        page = int(ctx["page"]) or 1
        bytes_limit = gb * (1024 ** 3) if gb > 0 else 0
        async with session_scope() as session:
            # Pick next available template_id
            rows = (await session.execute(select(Plan.template_id).order_by(Plan.template_id.desc()))).scalars().all()
            next_tpl = (rows[0] + 1) if rows else 1
            p = Plan(
                template_id=next_tpl,
                title=title,
                price=irr,
                currency="IRR",
                duration_days=days,
                data_limit_bytes=bytes_limit,
                description=None,
                is_active=True,
            )
            session.add(p)
            await session.commit()
        _APLANS_CREATE_INTENT.pop(uid, None)
        await message.answer("پلن جدید ایجاد شد.")
        await admin_show_plans_menu(message, page=page, requester_id=message.from_user.id if message.from_user else None)
        return


# Edit/Delete
@router.callback_query(F.data.startswith("aplans:edit:"))
async def cb_aplans_edit(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_PLANS_EDIT)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        _, _, tpl, page = cb.data.split(":")
        tpl_id = int(tpl)
        page_num = int(page)
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="عنوان", callback_data=f"aplans:editfield:title:{tpl_id}:{page_num}")],
        [InlineKeyboardButton(text="حجم (GB)", callback_data=f"aplans:editfield:gb:{tpl_id}:{page_num}")],
        [InlineKeyboardButton(text="مدت (روز)", callback_data=f"aplans:editfield:days:{tpl_id}:{page_num}")],
        [InlineKeyboardButton(text="قیمت (تومان)", callback_data=f"aplans:editfield:price:{tpl_id}:{page_num}")],
    ])
    await cb.message.answer("کدام فیلد را می‌خواهید ویرایش کنید؟", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("aplans:editfield:"))
async def cb_aplans_edit_field(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_PLANS_EDIT)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        _, _, field, tpl, page = cb.data.split(":")
        tpl_id = int(tpl)
        page_num = int(page)
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    _APLANS_FIELD_INTENT[cb.from_user.id] = (field, tpl_id, page_num)
    prompts = {
        "title": "عنوان جدید را ارسال کنید",
        "gb": "حجم جدید را به گیگابایت ارسال کنید (عدد صحیح؛ 0 برای نامحدود)",
        "days": "مدت جدید را به روز ارسال کنید (عدد صحیح؛ 0 برای بدون محدودیت)",
        "price": "قیمت جدید را به تومان ارسال کنید (عدد صحیح)",
    }
    await cb.message.answer(prompts.get(field, "ورودی را ارسال کنید"))
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _APLANS_FIELD_INTENT and isinstance(getattr(m, "text", None), str))
async def admin_plan_edit_steps(message: Message) -> None:
    uid = message.from_user.id if message.from_user else None
    if not await has_capability_async(uid, CAP_PLANS_EDIT):
        _APLANS_FIELD_INTENT.pop(uid, None)
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    field, tpl_id, page_num = _APLANS_FIELD_INTENT.pop(uid)
    async with session_scope() as session:
        row = await session.scalar(select(Plan).where(Plan.template_id == tpl_id))
        if not row:
            await message.answer("پلن یافت نشد.")
            return
        try:
            if field == "title":
                val = message.text.strip()
                if not val:
                    raise ValueError
                row.title = val
            elif field == "gb":
                gb = int(message.text.strip())
                if gb < 0:
                    raise ValueError
                row.data_limit_bytes = gb * (1024 ** 3) if gb > 0 else 0
            elif field == "days":
                days = int(message.text.strip())
                if days < 0:
                    raise ValueError
                row.duration_days = days
            elif field == "price":
                tmn = int(message.text.strip())
                if tmn <= 0:
                    raise ValueError
                row.price = tmn * 10
            else:
                await message.answer("فیلد نامعتبر است.")
                return
            await session.commit()
        except Exception:
            await message.answer("ورودی نامعتبر است. عملیات لغو شد.")
            return
    await message.answer("ویرایش انجام شد.")
    if await has_capability_async(message.from_user.id, CAP_PLANS_MANAGE):
        await admin_show_plans_menu(message, page=page_num, requester_id=message.from_user.id)


@router.callback_query(F.data.startswith("aplans:delete:"))
async def cb_aplans_delete(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_PLANS_DELETE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        _, _, tpl, page = cb.data.split(":")
        tpl_id = int(tpl)
        page_num = int(page)
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="بله، حذف شود", callback_data=f"aplans:delconf:yes:{tpl_id}:{page_num}")],
        [InlineKeyboardButton(text="خیر، انصراف", callback_data=f"aplans:delconf:no:{tpl_id}:{page_num}")],
    ])
    await cb.message.answer("آیا از حذف این پلن مطمئن هستید؟", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("aplans:delconf:"))
async def cb_aplans_del_confirm(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_PLANS_DELETE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        _, _, decision, tpl, page = cb.data.split(":")
        tpl_id = int(tpl)
        page_num = int(page)
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    if decision == "no":
        try:
            await cb.message.edit_text((cb.message.text or "عملیات حذف") + "\n\nلغو شد ❌")
        except Exception:
            pass
        await cb.answer("لغو شد")
        return
    async with session_scope() as session:
        row = await session.scalar(select(Plan).where(Plan.template_id == tpl_id))
        if not row:
            await cb.answer("پلن یافت نشد", show_alert=True)
            return
        # Prevent delete when orders reference this plan
        cnt = await session.scalar(select(func.count()).select_from(Order).where(Order.plan_id == row.id))
        if cnt and int(cnt) > 0:
            try:
                await cb.message.edit_text((cb.message.text or "حذف پلن") + "\n\nحذف ممکن نیست: به این پلن سفارش مرتبط وجود دارد. لطفاً به‌جای حذف، پلن را غیرفعال کنید.")
            except Exception:
                pass
            await cb.answer("دارای سفارش فعال/قدیمی", show_alert=True)
            return
        await session.delete(row)
        await session.commit()
    try:
        await cb.message.edit_text((cb.message.text or "حذف پلن") + "\n\nحذف شد ✅")
    except Exception:
        pass
    if await has_capability_async(cb.from_user.id, CAP_PLANS_MANAGE):
        await admin_show_plans_menu(cb.message, page=page_num, requester_id=cb.from_user.id)
    await cb.answer("حذف شد")
