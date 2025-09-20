from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from sqlalchemy import select, func

from app.db.session import session_scope
from app.db.models import Coupon
from app.services.security import is_admin_uid
from app.utils.intent_store import get_intent_json, set_intent_json, clear_intent

router = Router()

PAGE_SIZE = 5

# ============ Helpers ============ #

def _fmt_money(v: Optional[Decimal]) -> str:
    try:
        return f"{int(Decimal(str(v or 0))):,} ریال"
    except Exception:
        return "0 ریال"


def _fmt_coupon(c: Coupon) -> str:
    ty = "درصدی" if (c.type or "percent") == "percent" else "ثابت"
    if (c.type or "percent") == "percent":
        val = f"{int(Decimal(str(c.value or 0)))}%"
    else:
        val = _fmt_money(c.value)
    cap = _fmt_money(c.cap) if c.cap else "-"
    minv = _fmt_money(c.min_order_amount) if c.min_order_amount else "-"
    act = "✅ فعال" if c.active else "❌ غیرفعال"
    window = []
    if c.start_at:
        window.append(f"از {c.start_at:%Y-%m-%d}")
    if c.end_at:
        window.append(f"تا {c.end_at:%Y-%m-%d}")
    win = " | ".join(window) if window else "بدون بازه"
    return (
        f"🎟️ {c.code}\n"
        f"عنوان: {c.title or '-'}\n"
        f"نوع/مقدار: {ty} / {val}\n"
        f"حداکثر تخفیف: {cap}\n"
        f"حداقل مبلغ سفارش: {minv}\n"
        f"وضعیت: {act}\n"
        f"بازه: {win}"
    )


def _kb_list(page: int, total_pages: int, items: list[Coupon]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    # item actions: toggle/delete
    for c in items:
        row: list[InlineKeyboardButton] = []
        row.append(InlineKeyboardButton(text=("🔴 غیرفعال" if c.active else "🟢 فعال"), callback_data=f"cp:tg:{c.id}"))
        row.append(InlineKeyboardButton(text="🗑️ حذف", callback_data=f"cp:del:{c.id}"))
        rows.append(row)
    # nav
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cp:pg:{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cp:pg:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="➕ ایجاد کوپن", callback_data="cp:new")])
    rows.append([InlineKeyboardButton(text="🔄 بروزرسانی", callback_data=f"cp:pg:{page}")])
    rows.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="cp:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_list(msg: Message, page: int = 1) -> None:
    async with session_scope() as session:
        total = await session.scalar(select(func.count(Coupon.id)))
        total = int(total or 0)
        total_pages = max((total + PAGE_SIZE - 1)//PAGE_SIZE, 1)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * PAGE_SIZE
        rows = (await session.execute(select(Coupon).order_by(Coupon.id.desc()).offset(offset).limit(PAGE_SIZE))).scalars().all()
    if not rows:
        text = (
            "🎟️ کدهای تخف��ف\n\n"
            "هنوز کوپنی ثبت نشده است. از دکمه \"➕ ایجاد کوپن\" استفاده کنید."
        )
    else:
        parts = ["🎟️ کدهای تخفیف\n"]
        for c in rows:
            parts.append(_fmt_coupon(c))
            parts.append("")
        text = "\n".join(parts)
    try:
        await msg.edit_text(text, reply_markup=_kb_list(page, total_pages, rows))
    except Exception:
        await msg.answer(text, reply_markup=_kb_list(page, total_pages, rows))


# ============ Entry/Navigation ============ #

@router.message(F.text.regexp(r".*(?:ک|ك)دها(?:ی|ي)\s+تخف(?:ی|ي)ف.*"))
async def _admin_coupons_entry(message: Message) -> None:
    if not (message.from_user and is_admin_uid(message.from_user.id)):
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    await _render_list(message, 1)


@router.callback_query(F.data.startswith("cp:pg:"))
async def _cb_page(cb: CallbackQuery) -> None:
    if not (cb.from_user and is_admin_uid(cb.from_user.id)):
        await cb.answer("⛔️", show_alert=True)
        return
    try:
        page = int(cb.data.split(":")[2])
    except Exception:
        page = 1
    await _render_list(cb.message, page)
    await cb.answer()


@router.callback_query(F.data == "cp:back")
async def _cb_back(cb: CallbackQuery) -> None:
    await cb.answer("بازگشت")
    # بازگشت به «⚙️ تنظیمات ربات» توسط استارت هندلر انجام می‌شود


# ============ Toggle/Delete ============ #

@router.callback_query(F.data.startswith("cp:tg:"))
async def _cb_toggle(cb: CallbackQuery) -> None:
    if not (cb.from_user and is_admin_uid(cb.from_user.id)):
        await cb.answer("⛔️", show_alert=True)
        return
    try:
        cid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    async with session_scope() as session:
        c = await session.get(Coupon, cid)
        if not c:
            await cb.answer("یافت نشد", show_alert=True)
            return
        c.active = not bool(c.active)
        await session.commit()
    await _render_list(cb.message, 1)
    await cb.answer("تغییر وضعیت ذخیره شد")


@router.callback_query(F.data.startswith("cp:del:"))
async def _cb_del(cb: CallbackQuery) -> None:
    if not (cb.from_user and is_admin_uid(cb.from_user.id)):
        await cb.answer("⛔️", show_alert=True)
        return
    try:
        cid = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❗️ تایید حذف", callback_data=f"cp:del:confirm:{cid}")],
        [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="cp:pg:1")],
    ])
    await cb.message.edit_text("آیا از حذف این کوپن مطمئن هستید؟", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("cp:del:confirm:"))
async def _cb_del_confirm(cb: CallbackQuery) -> None:
    if not (cb.from_user and is_admin_uid(cb.from_user.id)):
        await cb.answer("⛔️", show_alert=True)
        return
    try:
        cid = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    async with session_scope() as session:
        c = await session.get(Coupon, cid)
        if c:
            await session.delete(c)
            await session.commit()
    await _render_list(cb.message, 1)
    await cb.answer("حذف شد")


# ============ Create Wizard ============ #
# مراحل: await_code -> (type via inline) -> await_value -> await_cap -> await_min -> await_title -> await_active (inline) -> save

@router.callback_query(F.data == "cp:new")
async def _cb_new(cb: CallbackQuery) -> None:
    if not (cb.from_user and is_admin_uid(cb.from_user.id)):
        await cb.answer("⛔️", show_alert=True)
        return
    uid = cb.from_user.id
    await set_intent_json(f"INTENT:CPW:{uid}", {"stage": "await_code"})
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="لغو", callback_data="cp:w:cancel")]])
    await cb.message.edit_text("🎟️ ایجاد کوپن جدید\n\nلطفاً کد کوپن را وارد کنید (حروف/اعداد/خط تیره/زیرخط، 3 تا 64 کاراکتر).", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "cp:w:cancel")
async def _cb_w_cancel(cb: CallbackQuery) -> None:
    if cb.from_user:
        await clear_intent(f"INTENT:CPW:{cb.from_user.id}")
    await _render_list(cb.message, 1)
    await cb.answer("لغو شد")


@router.message(lambda m: getattr(m, "from_user", None) and is_admin_uid(m.from_user.id))
async def _msg_wizard_capture(message: Message) -> None:
    uid = message.from_user.id
    payload = await get_intent_json(f"INTENT:CPW:{uid}")
    if not payload:
        return
    stage = str(payload.get("stage") or "")
    txt = (message.text or "").strip()
    # مرحله: کد
    if stage == "await_code":
        import re
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,64}", txt):
            await message.answer("❌ کد نامعتبر است. فقط حروف/اعداد/خط‌تیره/زیرخط، 3 تا 64 کاراکتر.")
            return
        await set_intent_json(f"INTENT:CPW:{uid}", {**payload, "code": txt, "stage": "await_type"})
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="٪ درصدی", callback_data="cp:w:type:percent"), InlineKeyboardButton(text="💰 ثابت", callback_data="cp:w:type:fixed")], [InlineKeyboardButton(text="لغو", callback_data="cp:w:cancel")]])
        await message.answer("نوع تخفیف را انتخاب کنید:", reply_markup=kb)
        return
    # مقدار
    if stage == "await_value":
        try:
            val = Decimal(txt)
            if str(payload.get("type")) == "percent":
                if val <= 0 or val > 100:
                    raise ValueError
            else:
                if val <= 0:
                    raise ValueError
        except Exception:
            await message.answer("❌ مقدار نامعتبر است. برای درصد، عدد 1..100؛ برای ثابت، عدد ریالی > 0")
            return
        await set_intent_json(f"INTENT:CPW:{uid}", {**payload, "value": str(val), "stage": "await_cap"})
        await message.answer("🔢 سقف تخفیف (ریال) را وارد کنید (یا 0 برای بدون سقف).")
        return
    # سقف
    if stage == "await_cap":
        try:
            cap = Decimal(txt)
            if cap < 0:
                raise ValueError
        except Exception:
            await message.answer("❌ عدد معتبر وارد کنید (0 برای بدون سقف).")
            return
        cap_str = None if cap == 0 else str(cap)
        await set_intent_json(f"INTENT:CPW:{uid}", {**payload, "cap": cap_str, "stage": "await_min"})
        await message.answer("💵 حداقل مبلغ سفارش (ریال) را وارد کنید (یا 0 برای بدون حداقل).")
        return
    # حداقل مبلغ
    if stage == "await_min":
        try:
            mn = Decimal(txt)
            if mn < 0:
                raise ValueError
        except Exception:
            await message.answer("❌ عدد معتبر وارد کنید (0 برای بدون حداقل).")
            return
        min_str = None if mn == 0 else str(mn)
        await set_intent_json(f"INTENT:CPW:{uid}", {**payload, "min": min_str, "stage": "await_title"})
        await message.answer("📝 یک عنوان کوتاه برای کوپن وارد کنید (یا '-' برای خالی).")
        return
    # عنوان
    if stage == "await_title":
        title = None if txt == "-" else txt[:191]
        await set_intent_json(f"INTENT:CPW:{uid}", {**payload, "title": title, "stage": "await_active"})
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ فعال", callback_data="cp:w:active:1"), InlineKeyboardButton(text="❌ غیرفعال", callback_data="cp:w:active:0")], [InlineKeyboardButton(text="لغو", callback_data="cp:w:cancel")]])
        await message.answer("وضعیت اولیه را انتخاب کنید:", reply_markup=kb)
        return


@router.callback_query(F.data.startswith("cp:w:type:"))
async def _cb_w_type(cb: CallbackQuery) -> None:
    if not (cb.from_user and is_admin_uid(cb.from_user.id)):
        await cb.answer("⛔️", show_alert=True)
        return
    uid = cb.from_user.id
    payload = await get_intent_json(f"INTENT:CPW:{uid}") or {}
    tp = (cb.data.split(":")[3] or "percent").strip()
    if tp not in {"percent", "fixed"}:
        await cb.answer("نوع نامعتبر", show_alert=True)
        return
    await set_intent_json(f"INTENT:CPW:{uid}", {**payload, "type": tp, "stage": "await_value"})
    if tp == "percent":
        await cb.message.edit_text("٪ مقدار درصد را وارد کنید (عدد 1..100).", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="لغو", callback_data="cp:w:cancel")]]))
    else:
        await cb.message.edit_text("💰 مقدار ثابت را به ریال وارد کنید.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="لغو", callback_data="cp:w:cancel")]]))
    await cb.answer()


@router.callback_query(F.data.startswith("cp:w:active:"))
async def _cb_w_active(cb: CallbackQuery) -> None:
    if not (cb.from_user and is_admin_uid(cb.from_user.id)):
        await cb.answer("⛔️", show_alert=True)
        return
    uid = cb.from_user.id
    payload = await get_intent_json(f"INTENT:CPW:{uid}") or {}
    act = (cb.data.split(":")[3] or "1").strip() == "1"
    await set_intent_json(f"INTENT:CPW:{uid}", {**payload, "active": act, "stage": "confirm"})
    # خلاصه
    code = payload.get("code")
    ty = payload.get("type")
    val = payload.get("value")
    cap = payload.get("cap")
    mn = payload.get("min")
    title = payload.get("title")
    ty_txt = "درصدی" if ty == "percent" else "ثابت"
    val_txt = (f"{val}%" if ty == "percent" else _fmt_money(Decimal(val or "0")))
    cap_txt = _fmt_money(Decimal(cap)) if cap else "-"
    mn_txt = _fmt_money(Decimal(mn)) if mn else "-"
    act_txt = "✅ فعال" if act else "❌ غیرفعال"
    summary = (
        "خلاصه کوپن:\n\n"
        f"کد: {code}\n"
        f"نوع/مقدار: {ty_txt} / {val_txt}\n"
        f"حداکثر تخفیف: {cap_txt}\n"
        f"حداقل مبلغ سفارش: {mn_txt}\n"
        f"عنوان: {title or '-'}\n"
        f"وضعیت: {act_txt}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💾 ثبت", callback_data="cp:w:save"), InlineKeyboardButton(text="لغو", callback_data="cp:w:cancel")]])
    await cb.message.edit_text(summary, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "cp:w:save")
async def _cb_w_save(cb: CallbackQuery) -> None:
    if not (cb.from_user and is_admin_uid(cb.from_user.id)):
        await cb.answer("⛔️", show_alert=True)
        return
    uid = cb.from_user.id
    p = await get_intent_json(f"INTENT:CPW:{uid}") or {}
    code = (p.get("code") or "").strip()
    ty = (p.get("type") or "percent").strip()
    val = Decimal(str(p.get("value") or "0"))
    cap = p.get("cap")
    cap_dec = Decimal(str(cap)) if cap else None
    mn = p.get("min")
    mn_dec = Decimal(str(mn)) if mn else None
    title = p.get("title")
    act = bool(p.get("active"))
    async with session_scope() as session:
        # unique code check
        exists = await session.scalar(select(func.count(Coupon.id)).where(Coupon.code == code))
        if (exists or 0) > 0:
            await cb.answer("کد تکراری است", show_alert=True)
            return
        c = Coupon(
            code=code,
            title=title,
            description=None,
            type=ty,
            value=val,
            cap=cap_dec,
            currency="IRR",
            active=act,
            start_at=None,
            end_at=None,
            min_order_amount=mn_dec,
            max_uses=None,
            max_uses_per_user=None,
            is_stackable=False,
            priority=0,
        )
        session.add(c)
        await session.commit()
    await clear_intent(f"INTENT:CPW:{uid}")
    await _render_list(cb.message, 1)
    await cb.answer("✅ کوپن ایجاد شد")
