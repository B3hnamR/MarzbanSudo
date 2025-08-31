from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Tuple

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, update, desc

from app.db.session import session_scope
from app.db.models import User, WalletTopUp, Setting
from app.services.audit import log_audit
from app.services.security import has_capability_async, CAP_WALLET_MODERATE

router = Router()

# ===== Admin Manual Wallet Add (UI flow) =====
# Per-admin state: { admin_id: { 'stage': 'await_ref'|'await_unit'|'await_amount',
#                                'user_id': int|None, 'unit': 'IRR'|'TMN'|None } }
_WALLET_MANUAL_ADD_INTENT: Dict[int, Dict[str, object]] = {}


@router.message(F.text == "➕ شارژ دستی")
async def admin_wallet_manual_add_start(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    admin_id = message.from_user.id
    _WALLET_MANUAL_ADD_INTENT[admin_id] = {"stage": "await_ref", "user_id": None, "unit": None}
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="لغو", callback_data="walletadm:add:cancel")]])
    await message.answer("👤 لطفاً شناسه کاربر را ارسال کنید (نام‌کاربری یا 🆔 تلگرام).", reply_markup=kb)


@router.callback_query(F.data == "walletadm:add:cancel")
async def cb_admin_wallet_manual_add_cancel(cb: CallbackQuery) -> None:
    uid = cb.from_user.id if cb.from_user else None
    _WALLET_MANUAL_ADD_INTENT.pop(uid, None)
    await cb.answer("لغو شد")
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _WALLET_MANUAL_ADD_INTENT and _WALLET_MANUAL_ADD_INTENT.get(m.from_user.id, {}).get("stage") == "await_ref" and isinstance(getattr(m, "text", None), str))
async def admin_wallet_manual_add_ref(message: Message) -> None:
    admin_id = message.from_user.id
    if not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        _WALLET_MANUAL_ADD_INTENT.pop(admin_id, None)
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    ref = message.text.strip()
    async with session_scope() as session:
        user = None
        if ref.isdigit():
            user = await session.scalar(select(User).where(User.telegram_id == int(ref)))
        else:
            user = await session.scalar(select(User).where(User.marzban_username == ref))
        if not user:
            await message.answer("کاربر یافت نشد. مجدد شناسه صحیح را ارسال کنید یا لغو کنید.")
            return
        _WALLET_MANUAL_ADD_INTENT[admin_id] = {"stage": "await_unit", "user_id": user.id, "unit": None}
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ورود مبلغ به تومان", callback_data="walletadm:add:unit:TMN"), InlineKeyboardButton(text="ورود مبلغ به ریال", callback_data="walletadm:add:unit:IRR")]])
    await message.answer("واحد مبلغ را انتخاب کنید:", reply_markup=kb)


@router.callback_query(F.data.startswith("walletadm:add:unit:"))
async def cb_admin_wallet_manual_add_unit(cb: CallbackQuery) -> None:
    uid = cb.from_user.id if cb.from_user else None
    state = _WALLET_MANUAL_ADD_INTENT.get(uid)
    if not state or state.get("stage") != "await_unit":
        await cb.answer()
        return
    if not await has_capability_async(uid, CAP_WALLET_MODERATE):
        _WALLET_MANUAL_ADD_INTENT.pop(uid, None)
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    unit = cb.data.split(":")[-1]
    if unit not in {"TMN", "IRR"}:
        await cb.answer("واحد نامعتبر", show_alert=True)
        return
    state["unit"] = unit
    state["stage"] = "await_amount"
    await cb.message.answer("مبلغ را به صورت عدد ارسال کنید.")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and m.from_user.id in _WALLET_MANUAL_ADD_INTENT and _WALLET_MANUAL_ADD_INTENT.get(m.from_user.id, {}).get("stage") == "await_amount" and isinstance(getattr(m, "text", None), str))
async def admin_wallet_manual_add_amount(message: Message) -> None:
    admin_id = message.from_user.id
    state = _WALLET_MANUAL_ADD_INTENT.get(admin_id)
    if not state or not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        _WALLET_MANUAL_ADD_INTENT.pop(admin_id, None)
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        val = Decimal(message.text.strip())
        if val <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. یک عدد مثبت ارسال کنید یا لغو کنید.")
        return
    unit = state.get("unit")
    user_id = state.get("user_id")
    if unit not in {"TMN", "IRR"} or not user_id:
        _WALLET_MANUAL_ADD_INTENT.pop(admin_id, None)
        await message.answer("وضعیت نامعتبر. از ابتدا تلاش کنید.")
        return
    irr = val * Decimal('10') if unit == "TMN" else val
    tmn_add = int((irr/Decimal('10')).to_integral_value())
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.id == int(user_id)))
        if not user:
            _WALLET_MANUAL_ADD_INTENT.pop(admin_id, None)
            await message.answer("کاربر یافت نشد.")
            return
        user.balance = (Decimal(user.balance or 0) + irr)
        await log_audit(session, actor="admin", action="wallet_manual_add", target_type="user", target_id=user.id, meta=str({"amount": str(irr)}))
        await session.commit()
        new_tmn = int((Decimal(user.balance or 0)/Decimal('10')).to_integral_value())
        target_tg = user.telegram_id
        target_username = user.marzban_username
    # notify user
    try:
        await message.bot.send_message(chat_id=target_tg, text=f"✅ شارژ دستی توسط ادمین: +{tmn_add:,} تومان\nموجودی جدید: {new_tmn:,} تومان")
    except Exception:
        pass
    _WALLET_MANUAL_ADD_INTENT.pop(admin_id, None)
    await message.answer(f"انجام شد. موجودی جدید {target_username}: {new_tmn:,} تومان")


@router.message(F.text == "💳 درخواست‌های شارژ")
async def admin_wallet_pending_topups(message: Message) -> None:
    # List up to 9 pending wallet top-ups with Approve/Reject buttons
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(WalletTopUp, User)
                .join(User, WalletTopUp.user_id == User.id)
                .where(WalletTopUp.status == "pending")
                .order_by(desc(WalletTopUp.created_at))
                .limit(9)
            )
        ).all()
    if not rows:
        await message.answer("درخواستی برای بررسی موجود نیست.")
        return
    for topup, user in rows:
        tmn = int((Decimal(topup.amount or 0) / Decimal("10")).to_integral_value())
        caption = (
            "💳 درخواست شارژ کیف پول\n"
            f"ID: {topup.id} | وضعیت: {topup.status}\n"
            f"کاربر: {user.marzban_username} (tg:{user.telegram_id})\n"
            f"مبلغ: {tmn:,} تومان\n"
            f"ثبت: {topup.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Approve ✅", callback_data=f"wallet:approve:{topup.id}"), InlineKeyboardButton(text="Reject ❌", callback_data=f"wallet:reject:{topup.id}"), InlineKeyboardButton(text="رد با دلیل 📝", callback_data=f"wallet:rejectr:{topup.id}")]])
        # Try to show original receipt media; fallback to text if sending media fails
        try:
            await message.bot.send_photo(chat_id=message.chat.id, photo=topup.receipt_file_id, caption=caption, reply_markup=kb)
        except Exception:
            try:
                await message.bot.send_document(chat_id=message.chat.id, document=topup.receipt_file_id, caption=caption, reply_markup=kb)
            except Exception:
                await message.answer(caption, reply_markup=kb)


def _admin_ids() -> set[int]:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "")
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}


def _is_admin_user_id(uid: int | None) -> bool:
    return bool(uid and uid in _admin_ids())

# In-memory intent storage (per-process)
_TOPUP_INTENT: Dict[int, Decimal] = {}
# Admin intent for setting minimum top-up (awaiting amount input)
_WALLET_ADMIN_MIN_INTENT: Dict[int, bool] = {}
# Admin intent for setting maximum top-up (awaiting amount input)
_WALLET_ADMIN_MAX_INTENT: Dict[int, bool] = {}
# Admin intent for reject-with-reason: admin_id -> topup_id
_WALLET_REJECT_REASON_INTENT: Dict[int, int] = {}
# Context to edit original admin message: admin_id -> (chat_id, message_id, original_content, kind['caption'|'text'])
_WALLET_REJECT_REASON_CTX: Dict[int, Tuple[int, int, str, str]] = {}


def _amount_options(min_amount: Decimal | None) -> List[Decimal]:
    base = min_amount or Decimal("100000")
    return [base, base * 2, base * 5]


async def _get_min_topup(session) -> Decimal:
    row = await session.scalar(select(Setting).where(Setting.key == "MIN_TOPUP_IRR"))
    if row:
        try:
            return Decimal(str(row.value))
        except Exception:
            return Decimal("100000")
    return Decimal("100000")


async def _get_max_topup(session) -> Decimal | None:
    row = await session.scalar(select(Setting).where(Setting.key == "MAX_TOPUP_IRR"))
    if row and str(row.value).strip():
        try:
            val = Decimal(str(row.value))
            return val if val > 0 else None
        except Exception:
            return None
    return None


@router.message(F.text == "💳 کیف پول")
async def wallet_menu(message: Message) -> None:
    if not message.from_user:
        return
    tg_id = message.from_user.id
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if not user:
            await message.answer("ابتدا یک سفارش ایجاد کنید تا حساب کاربری ساخته شود.")
            return
        bal = Decimal(user.balance or 0)
        min_amt = await _get_min_topup(session)
        options = _amount_options(min_amt)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"شارژ {int(a/10):,} تومان", callback_data=f"wallet:amt:{int(a)}")] for a in options
        ] + [[InlineKeyboardButton(text="مبلغ دلخواه", callback_data="wallet:custom")]])
        await message.answer(
            f"موجودی کیف پول شما: {int(bal/10):,} تومان\nیکی از مبالغ زیر را انتخاب کنید یا مبلغ دلخواه را وارد کنید.",
            reply_markup=kb,
        )


@router.callback_query(F.data == "wallet:custom")
async def cb_wallet_custom(cb: CallbackQuery) -> None:
    await cb.message.answer("مبلغ دلخواه را به تومان ارسال کنید (مثلاً 76000 برای ۷۶۰۰۰ تومان).")
    _TOPUP_INTENT[cb.from_user.id] = Decimal("-1")
    await cb.answer()


# Dedicated handler for admin numeric inputs (min/max intents)
@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and ( _WALLET_ADMIN_MIN_INTENT.get(m.from_user.id, False) or _WALLET_ADMIN_MAX_INTENT.get(m.from_user.id, False) ) and isinstance(getattr(m, "text", None), str) and __import__("re").match(r"^\d{1,10}$", m.text))
async def admin_wallet_limits_numeric_input(message: Message) -> None:
    uid = message.from_user.id if message.from_user else None
    if not await has_capability_async(uid, CAP_WALLET_MODERATE):
        _WALLET_ADMIN_MIN_INTENT.pop(uid, None)
        _WALLET_ADMIN_MAX_INTENT.pop(uid, None)
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        toman_val = int(message.text.strip())
    except Exception:
        await message.answer("مبلغ نامعتبر است. یک عدد صحیح ارسال کنید.")
        return
    # MIN intent
    if _WALLET_ADMIN_MIN_INTENT.pop(uid, False):
        if toman_val <= 0:
            await message.answer("مبلغ نامعتبر است. یک عدد صحیح ارسال کنید.")
            return
        irr = toman_val * 10
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "MIN_TOPUP_IRR"))
            if not row:
                row = Setting(key="MIN_TOPUP_IRR", value=str(int(irr)))
                session.add(row)
            else:
                row.value = str(int(irr))
            await session.commit()
        await message.answer(f"حداقل مبلغ شارژ تنظیم شد: {toman_val:,} تومان")
        await admin_wallet_settings_menu(message)
        return
    # MAX intent
    if _WALLET_ADMIN_MAX_INTENT.pop(uid, False):
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "MAX_TOPUP_IRR"))
            if toman_val == 0:
                if row:
                    await session.delete(row)
            else:
                irr = toman_val * 10
                if not row:
                    row = Setting(key="MAX_TOPUP_IRR", value=str(int(irr)))
                    session.add(row)
                else:
                    row.value = str(int(irr))
            await session.commit()
        await message.answer("سقف حداکثر شارژ به‌روزرسانی شد.")
        await admin_wallet_settings_menu(message)
        return

@router.message(F.text.regexp(r"^\d{1,10}$"))
async def handle_wallet_custom_amount(message: Message) -> None:
    if not message.from_user:
        return
    uid = message.from_user.id
    # Admin intents (set min/max) take precedence over user top-up intent
    if _WALLET_ADMIN_MIN_INTENT.get(uid, False) or _WALLET_ADMIN_MAX_INTENT.get(uid, False):
        if not await has_capability_async(uid, CAP_WALLET_MODERATE):
            _WALLET_ADMIN_MIN_INTENT.pop(uid, None)
            _WALLET_ADMIN_MAX_INTENT.pop(uid, None)
            await message.answer("شما دسترسی ادمین ندارید.")
            return
        # Parse integer Toman
        try:
            toman_val = int(message.text.strip())
        except Exception:
            await message.answer("مبلغ نامعتبر است. یک عدد صحیح ارسال کنید.")
            return
        # Handle MIN intent
        if _WALLET_ADMIN_MIN_INTENT.pop(uid, False):
            if toman_val <= 0:
                await message.answer("مبلغ نامعتبر است. یک عدد صحیح ارسال کنید.")
                return
            irr = toman_val * 10
            async with session_scope() as session:
                row = await session.scalar(select(Setting).where(Setting.key == "MIN_TOPUP_IRR"))
                if not row:
                    row = Setting(key="MIN_TOPUP_IRR", value=str(int(irr)))
                    session.add(row)
                else:
                    row.value = str(int(irr))
                await session.commit()
            await message.answer(f"حداقل مبلغ شارژ تنظیم شد: {toman_val:,} تومان")
            await admin_wallet_settings_menu(message)
            return
        # Handle MAX intent
        if _WALLET_ADMIN_MAX_INTENT.pop(uid, False):
            async with session_scope() as session:
                row = await session.scalar(select(Setting).where(Setting.key == "MAX_TOPUP_IRR"))
                if toman_val == 0:
                    if row:
                        await session.delete(row)
                else:
                    irr = toman_val * 10
                    if not row:
                        row = Setting(key="MAX_TOPUP_IRR", value=str(int(irr)))
                        session.add(row)
                    else:
                        row.value = str(int(irr))
                await session.commit()
            await message.answer("سقف حداکثر شارژ به‌روزرسانی شد.")
            await admin_wallet_settings_menu(message)
            return
    # User top-up custom amount path (requires prior intent marker)
    if uid not in _TOPUP_INTENT or _TOPUP_INTENT[uid] != Decimal("-1"):
        return
    try:
        toman = Decimal(message.text)
        if toman <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. دوباره ارسال کنید.")
        return
    rial = toman * Decimal("10")
    async with session_scope() as session:
        min_irr = await _get_min_topup(session)
        max_irr = await _get_max_topup(session)
    if rial < min_irr:
        await message.answer(
            f"حداقل مبلغ شارژ {int(min_irr/Decimal('10')):,} تومان است. لطفاً مبلغ بیشتری وارد کنید."
        )
        _TOPUP_INTENT[uid] = Decimal("-1")
        return
    if max_irr is not None and rial > max_irr:
        await message.answer(
            f"حداکثر مبلغ شارژ {int(max_irr/Decimal('10')):,} تومان است. لطفاً مبلغ کمتری وارد کنید."
        )
        _TOPUP_INTENT[uid] = Decimal("-1")
        return
    _TOPUP_INTENT[uid] = rial
    await message.answer(f"مبلغ {int(toman):,} تومان انتخاب شد. لطفاً عکس رسید پرداخت را ارسال کنید.")


@router.callback_query(F.data.startswith("wallet:amt:"))
async def cb_wallet_amount(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        amount = Decimal(cb.data.split(":")[2])
    except Exception:
        await cb.answer("مبلغ نامعتبر", show_alert=True)
        return
    async with session_scope() as session:
        min_irr = await _get_min_topup(session)
        max_irr = await _get_max_topup(session)
    if amount < min_irr:
        await cb.answer(
            f"حداقل مبلغ شارژ {int(min_irr/Decimal('10')):,} تومان است.", show_alert=True
        )
        return
    if max_irr is not None and amount > max_irr:
        await cb.answer(
            f"حداکثر مبلغ شارژ {int(max_irr/Decimal('10')):,} تومان است.", show_alert=True
        )
        return
    _TOPUP_INTENT[cb.from_user.id] = amount
    await cb.message.answer(
        f"مبلغ {int(amount/10):,} تومان انتخاب شد.\nلطفاً عکس رسید پرداخت را ارسال کنید (بدون نیاز به متن)."
    )
    await cb.answer()


@router.message(F.photo | F.document)
async def handle_wallet_photo(message: Message) -> None:
    # Only process as top-up if user has an active intent; otherwise ignore here
    if not message.from_user:
        return
    tg_id = message.from_user.id
    if tg_id not in _TOPUP_INTENT:
        return
    amount = _TOPUP_INTENT.pop(tg_id)
    file_id = None
    is_photo = False
    if message.photo:
        file_id = message.photo[-1].file_id
        is_photo = True
    elif message.document:
        file_id = message.document.file_id
    if not file_id:
        return
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if not user:
            await message.answer("حساب کاربری یافت نشد.")
            return
        min_irr = await _get_min_topup(session)
        max_irr = await _get_max_topup(session)
        if amount < min_irr:
            await message.answer(
                f"مبلغ انتخاب‌شده کمتر از حداقل مجاز است ({int(min_irr/Decimal('10')):,} تومان). لطفاً از منوی کیف پول دوباره اقدام کنید."
            )
            return
        if max_irr is not None and amount > max_irr:
            await message.answer(
                f"مبلغ انتخاب‌شده بیشتر از حداکثر مجاز است ({int(max_irr/Decimal('10')):,} تومان). لطفاً از منوی کیف پول دوباره اقدام کنید."
            )
            return
        topup = WalletTopUp(
            user_id=user.id,
            amount=amount,
            currency="IRR",
            status="pending",
            receipt_file_id=file_id,
            note=None,
            admin_id=None,
        )
        session.add(topup)
        await session.flush()
        await log_audit(session, actor="user", action="wallet_topup_created", target_type="wallet_topup", target_id=topup.id, meta=str({"amount": str(amount)}))
        await session.commit()
    await message.answer("درخواست شارژ ثبت شد و برای ادمین ارسال گردید.")
    # Forward to admins
    admin_raw = os.getenv("TELEGRAM_ADMIN_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_raw.split(",") if x.strip().isdigit()]
    if admin_ids:
        caption = (
            f"درخواست شارژ کیف پول\n"
            f"TopUp ID: {topup.id}\n"
            f"User: {user.marzban_username} (tg:{user.telegram_id})\n"
            f"Amount: {int(amount/10):,} تومان\n"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Approve ✅", callback_data=f"wallet:approve:{topup.id}"), InlineKeyboardButton(text="Reject ❌", callback_data=f"wallet:reject:{topup.id}"), InlineKeyboardButton(text="رد با دلیل 📝", callback_data=f"wallet:rejectr:{topup.id}")]])
        for aid in admin_ids:
            try:
                if is_photo:
                    await message.bot.send_photo(chat_id=aid, photo=file_id, caption=caption, reply_markup=kb)
                else:
                    await message.bot.send_document(chat_id=aid, document=file_id, caption=caption, reply_markup=kb)
            except Exception:
                pass


@router.callback_query(F.data.startswith("wallet:rejectr:"))
async def cb_wallet_reject_reason_prompt(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        topup_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    _WALLET_REJECT_REASON_INTENT[cb.from_user.id] = topup_id
    orig_caption = getattr(cb.message, "caption", None)
    orig_text = getattr(cb.message, "text", None)
    content = orig_caption if orig_caption is not None else (orig_text or "")
    kind = "caption" if orig_caption is not None else "text"
    _WALLET_REJECT_REASON_CTX[cb.from_user.id] = (cb.message.chat.id, cb.message.message_id, content, kind)
    await cb.message.answer("لطفاً دلیل رد درخواست را ارسال کنید (یک پیام متنی).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and isinstance(getattr(m, "text", None), str) and m.from_user.id in _WALLET_REJECT_REASON_INTENT)
async def admin_wallet_reject_with_reason_text(message: Message) -> None:
    admin_id = message.from_user.id if message.from_user else None
    if not admin_id or not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        _WALLET_REJECT_REASON_INTENT.pop(admin_id, None)
        _WALLET_REJECT_REASON_CTX.pop(admin_id, None)
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    reason = message.text.strip()
    topup_id = _WALLET_REJECT_REASON_INTENT.pop(admin_id, None)
    ctx = _WALLET_REJECT_REASON_CTX.pop(admin_id, None)
    if not topup_id:
        return
    user_telegram_id = None
    async with session_scope() as session:
        row = await session.execute(select(WalletTopUp, User).join(User, WalletTopUp.user_id == User.id).where(WalletTopUp.id == topup_id))
        data = row.first()
        if not data:
            await message.answer("TopUp not found")
            return
        topup, user = data
        res = await session.execute(
            update(WalletTopUp)
            .where(WalletTopUp.id == topup_id, WalletTopUp.status == "pending")
            .values(status="rejected", admin_id=admin_id, note=reason, processed_at=datetime.utcnow())
            .execution_options(synchronize_session=False)
        )
        if (res.rowcount or 0) == 0:
            await message.answer("این درخواست قبلاً رسیدگی شده است.")
            return
        await log_audit(session, actor="admin", action="wallet_topup_rejected", target_type="wallet_topup", target_id=topup.id, meta=str({"admin_id": admin_id, "reason": reason}))
        user_telegram_id = user.telegram_id
        await session.commit()
    try:
        await message.bot.send_message(chat_id=user_telegram_id, text=f"درخواست شارژ شما رد شد. دلیل: {reason}")
    except Exception:
        pass
    if ctx:
        chat_id, msg_id, content, kind = ctx
        new_content = (content or "")
        append_txt = f"رد شد ❌\nدلیل: {reason}"
        if new_content:
            new_content = new_content + "\n\n" + append_txt
        else:
            new_content = append_txt
        try:
            if kind == "caption":
                await message.bot.edit_message_caption(chat_id=chat_id, message_id=msg_id, caption=new_content)
            else:
                await message.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_content)
        except Exception:
            pass
    await message.answer("رد شد و دلیل به کاربر اطلاع داده شد.")


@router.callback_query(F.data.startswith("wallet:approve:"))
async def cb_wallet_approve(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    if not await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        topup_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    admin_id = cb.from_user.id
    new_balance_for_msg: int | None = None
    user_telegram_id: int | None = None
    async with session_scope() as session:
        row = await session.execute(
            select(WalletTopUp, User).join(User, WalletTopUp.user_id == User.id).where(WalletTopUp.id == topup_id)
        )
        data = row.first()
        if not data:
            await cb.answer("TopUp not found", show_alert=True)
            return
        topup, user = data
        # Ensure pending -> approved transition is atomic
        res = await session.execute(
            update(WalletTopUp)
            .where(WalletTopUp.id == topup_id, WalletTopUp.status == "pending")
            .values(status="approved", admin_id=admin_id, processed_at=datetime.utcnow())
            .execution_options(synchronize_session=False)
        )
        if (res.rowcount or 0) == 0:
            await cb.answer("Already processed", show_alert=True)
            return
        # Guard overflow and update balance atomically
        add = Decimal(topup.amount or 0)
        max_irr = Decimal("9999999999.99")
        await session.execute(
            update(User).where(User.id == user.id).values(balance=User.balance + add).execution_options(synchronize_session=False)
        )
        # Read back for cap check and messaging
        new_bal = await session.scalar(select(User.balance).where(User.id == user.id))
        if new_bal and Decimal(new_bal) > max_irr:
            # revert changes
            await session.rollback()
            await session.execute(
                update(WalletTopUp)
                .where(WalletTopUp.id == topup_id, WalletTopUp.status == "approved")
                .values(status="pending", admin_id=None, processed_at=None)
                .execution_options(synchronize_session=False)
            )
            await session.commit()
            await cb.answer("مبلغ کل از سقف مجاز عبور می‌کند. امکان تایید این شارژ نیست.", show_alert=True)
            return
        await log_audit(session, actor="admin", action="wallet_topup_approved", target_type="wallet_topup", target_id=topup.id, meta=str({"admin_id": admin_id}))
        # Prepare messaging values
        user_telegram_id = user.telegram_id
        try:
            new_balance_for_msg = int((Decimal(new_bal or 0) / Decimal("10")).to_integral_value())
        except Exception:
            new_balance_for_msg = None
        await session.commit()
    try:
        if user_telegram_id is not None and new_balance_for_msg is not None:
            await cb.message.bot.send_message(chat_id=user_telegram_id, text=f"شارژ شما تایید شد. موجودی جدید: {new_balance_for_msg:,} تومان")
    except Exception:
        pass
    try:
        if getattr(cb.message, "caption", None):
            cap = cb.message.caption or "درخواست شارژ کیف پول"
            await cb.message.edit_caption(cap + "\n\nApproved ✅")
        else:
            txt = (cb.message.text or "درخواست شارژ کیف پول") + "\n\nApproved ✅"
            await cb.message.edit_text(txt)
    except Exception:
        pass
    await cb.answer("Approved")


# Admin interactive menu for wallet settings
async def _get_min_topup_value(session) -> Decimal:
    row = await session.scalar(select(Setting).where(Setting.key == "MIN_TOPUP_IRR"))
    if row:
        try:
            return Decimal(str(row.value))
        except Exception:
            return Decimal("100000")
    return Decimal("100000")


async def _get_max_topup_value(session) -> Decimal | None:
    row = await session.scalar(select(Setting).where(Setting.key == "MAX_TOPUP_IRR"))
    if row and str(row.value).strip():
        try:
            val = Decimal(str(row.value))
            return val if val > 0 else None
        except Exception:
            return None
    return None


def _admin_wallet_keyboard(min_irr: Decimal, max_irr: Decimal | None) -> InlineKeyboardMarkup:
    tmn = int(min_irr / Decimal("10"))
    x2 = min_irr * 2
    x5 = min_irr * 5
    rows = [
        [InlineKeyboardButton(text=f"تنظیم حداقل به {tmn:,} تومان", callback_data=f"walletadmin:min:set:{int(min_irr)}")],
        [InlineKeyboardButton(text=f"حداقل {int(x2/Decimal('10')):,}", callback_data=f"walletadmin:min:set:{int(x2)}"), InlineKeyboardButton(text=f"حداقل {int(x5/Decimal('10')):,}", callback_data=f"walletadmin:min:set:{int(x5)}")],
        [InlineKeyboardButton(text="حداقل: مبلغ دلخواه", callback_data="walletadmin:min:custom")],
    ]
    rows.append([InlineKeyboardButton(text=(f"حداکثر فعلی: {int(max_irr/Decimal('10')):,} تومان" if max_irr else "حداکثر: بدون سقف"), callback_data="walletadmin:min:refresh")])
    rows.append([InlineKeyboardButton(text="حداکثر: مبلغ دلخواه", callback_data="walletadmin:max:custom"), InlineKeyboardButton(text="حذف سقف", callback_data="walletadmin:max:clear")])
    rows.append([InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="walletadmin:min:refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "💼 تنظیمات کیف پول")
async def admin_wallet_settings_menu(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    # Best-effort: cancel any lingering plan management intents to avoid cross-capture of inputs
    try:
        from app.bot.handlers import admin_manage as _am
        uid = message.from_user.id
        _am._APLANS_CREATE_INTENT.pop(uid, None)
        _am._APLANS_FIELD_INTENT.pop(uid, None)
        _am._APLANS_PRICE_INTENT.pop(uid, None)
    except Exception:
        pass
    async with session_scope() as session:
        min_irr = await _get_min_topup_value(session)
        max_irr = await _get_max_topup_value(session)
    header = "تنظیمات کیف پول\n"
    header += f"حداقل مبلغ شارژ فعلی: {int(min_irr/Decimal('10')):,} تومان\n"
    header += f"حداکثر مبلغ شارژ فعلی: {int(max_irr/Decimal('10')):,} تومان\n" if max_irr else "حداکثر مبلغ شارژ فعلی: بدون سقف\n"
    text = header + "یکی از گزینه‌ها را انتخاب کنید یا مبلغ دلخواه را تعیین کنید."
    await message.answer(text, reply_markup=_admin_wallet_keyboard(min_irr, max_irr))


@router.callback_query(F.data == "walletadmin:min:refresh")
async def cb_walletadmin_min_refresh(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    async with session_scope() as session:
        min_irr = await _get_min_topup_value(session)
        max_irr = await _get_max_topup_value(session)
    header = "تنظیمات کیف پول\n"
    header += f"حداقل مبلغ شارژ فعلی: {int(min_irr/Decimal('10')):,} تومان\n"
    header += f"حداکثر مبلغ شارژ فعلی: {int(max_irr/Decimal('10')):,} تومان\n" if max_irr else "حداکثر مبلغ شارژ فعلی: بدون سقف\n"
    text = header + "یکی از گزینه‌ها را انتخاب کنید یا مبلغ دلخواه را تعیین کنید."
    try:
        await cb.message.edit_text(text, reply_markup=_admin_wallet_keyboard(min_irr, max_irr))
    except Exception:
        await cb.message.answer(text, reply_markup=_admin_wallet_keyboard(min_irr, max_irr))
    await cb.answer()


@router.callback_query(F.data.startswith("walletadmin:min:set:"))
async def cb_walletadmin_min_set(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        irr = int(cb.data.split(":")[3])
    except Exception:
        await cb.answer("مقدار نامعتبر", show_alert=True)
        return
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == "MIN_TOPUP_IRR"))
        if not row:
            row = Setting(key="MIN_TOPUP_IRR", value=str(int(irr)))
            session.add(row)
        else:
            row.value = str(int(irr))
        await session.commit()
    await cb.answer("ذخیره شد")
    # Refresh menu
    await cb_walletadmin_min_refresh(cb)


@router.callback_query(F.data == "walletadmin:min:custom")
async def cb_walletadmin_min_custom(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    _WALLET_ADMIN_MIN_INTENT[cb.from_user.id] = True
    # Cancel plan create/edit intents if any
    try:
        from app.bot.handlers import admin_manage as _am
        _am._APLANS_CREATE_INTENT.pop(cb.from_user.id, None)
        _am._APLANS_FIELD_INTENT.pop(cb.from_user.id, None)
        _am._APLANS_PRICE_INTENT.pop(cb.from_user.id, None)
    except Exception:
        pass
    await cb.message.answer("مبلغ دلخواه را به تومان ارسال کنید (مثلاً 150000 برای ۱۵۰ هزار تومان).")
    await cb.answer()


@router.callback_query(F.data == "walletadmin:max:custom")
async def cb_walletadmin_max_custom(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    _WALLET_ADMIN_MAX_INTENT[cb.from_user.id] = True
    # Cancel plan create/edit intents if any
    try:
        from app.bot.handlers import admin_manage as _am
        _am._APLANS_CREATE_INTENT.pop(cb.from_user.id, None)
        _am._APLANS_FIELD_INTENT.pop(cb.from_user.id, None)
        _am._APLANS_PRICE_INTENT.pop(cb.from_user.id, None)
    except Exception:
        pass
    await cb.message.answer("حداکثر مبلغ را به تومان ارسال کنید (برای حذف سقف 0 وارد کنید).")
    await cb.answer()


@router.callback_query(F.data == "walletadmin:max:clear")
async def cb_walletadmin_max_clear(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == "MAX_TOPUP_IRR"))
        if row:
            await session.delete(row)
            await session.commit()
    await cb.answer("سقف حذف شد")
    await cb_walletadmin_min_refresh(cb)


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and _WALLET_ADMIN_MAX_INTENT.get(m.from_user.id, False) and isinstance(getattr(m, "text", None), str) and __import__("re").match(r"^\d{1,10}$", m.text))
async def admin_wallet_max_custom_amount(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        _WALLET_ADMIN_MAX_INTENT.pop(message.from_user.id, None)
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        toman = int(message.text.strip())
        if toman < 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. 0 یا یک عدد صحیح ارسال کنید.")
        return
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == "MAX_TOPUP_IRR"))
        if toman == 0:
            # Clear cap
            if row:
                await session.delete(row)
        else:
            irr = toman * 10
            if not row:
                row = Setting(key="MAX_TOPUP_IRR", value=str(int(irr)))
                session.add(row)
            else:
                row.value = str(int(irr))
        await session.commit()
    _WALLET_ADMIN_MAX_INTENT.pop(message.from_user.id, None)
    await message.answer("سقف حداکثر شارژ به‌روزرسانی شد.")
    await admin_wallet_settings_menu(message)


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and _WALLET_ADMIN_MIN_INTENT.get(m.from_user.id, False) and isinstance(getattr(m, "text", None), str) and __import__("re").match(r"^\d{3,10}$", m.text))
async def admin_wallet_min_custom_amount(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        _WALLET_ADMIN_MIN_INTENT.pop(message.from_user.id, None)
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        toman = int(message.text.strip())
        if toman <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. یک عدد صحیح ارسال کنید.")
        return
    irr = toman * 10
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == "MIN_TOPUP_IRR"))
        if not row:
            row = Setting(key="MIN_TOPUP_IRR", value=str(int(irr)))
            session.add(row)
        else:
            row.value = str(int(irr))
        await session.commit()
    _WALLET_ADMIN_MIN_INTENT.pop(message.from_user.id, None)
    await message.answer(f"حداقل مبلغ شارژ تنظیم شد: {toman:,} تومان")
    # Show menu again
    await admin_wallet_settings_menu(message)


@router.callback_query(F.data.startswith("wallet:reject:"))
async def cb_wallet_reject(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    if not await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        topup_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    admin_id = cb.from_user.id
    async with session_scope() as session:
        row = await session.execute(
            select(WalletTopUp, User).join(User, WalletTopUp.user_id == User.id).where(WalletTopUp.id == topup_id)
        )
        data = row.first()
        if not data:
            await cb.answer("TopUp not found", show_alert=True)
            return
        topup, user = data
        # Atomically reject if pending
        res = await session.execute(
            update(WalletTopUp)
            .where(WalletTopUp.id == topup_id, WalletTopUp.status == "pending")
            .values(status="rejected", admin_id=admin_id, processed_at=datetime.utcnow())
            .execution_options(synchronize_session=False)
        )
        if (res.rowcount or 0) == 0:
            await cb.answer("Already processed", show_alert=True)
            return
        await log_audit(session, actor="admin", action="wallet_topup_rejected", target_type="wallet_topup", target_id=topup.id, meta=str({"admin_id": admin_id}))
        await session.commit()
    try:
        await cb.message.bot.send_message(chat_id=user.telegram_id, text=f"درخواست شارژ شما رد شد. مبلغ: {int((topup.amount or 0)/10):,} تومان")
    except Exception:
        pass
    try:
        if getattr(cb.message, "caption", None):
            cap = cb.message.caption or "درخواست شارژ کیف پول"
            await cb.message.edit_caption(cap + "\n\nRejected ❌")
        else:
            txt = (cb.message.text or "درخواست شارژ کیف پول") + "\n\nRejected ❌"
            await cb.message.edit_text(txt)
    except Exception:
        pass
    await cb.answer("Rejected")


# Admin settings
@router.message(F.text.startswith("/admin_wallet_set_min "))
async def admin_wallet_set_min(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1)
    try:
        amount = Decimal(parts[1])
    except Exception:
        await message.answer("فرمت: /admin_wallet_set_min <AMOUNT_IRR>")
        return
    async with session_scope() as session:
        row = await session.scalar(select(Setting).where(Setting.key == "MIN_TOPUP_IRR"))
        if not row:
            row = Setting(key="MIN_TOPUP_IRR", value=str(int(amount)))
            session.add(row)
        else:
            row.value = str(int(amount))
        await session.commit()
    await message.answer(f"حداقل مبلغ شارژ تنظیم شد: {int(amount):,} IRR")


@router.message(F.text.startswith("/admin_wallet_balance "))
async def admin_wallet_balance(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("فرمت: /admin_wallet_balance <username>")
        return
    username = parts[1].strip()
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.marzban_username == username))
        if not user:
            await message.answer("کاربر یافت نشد.")
            return
        await message.answer(f"موجودی {username}: {int((user.balance or 0)/10):,} تومان")


@router.message(F.text.startswith("/admin_wallet_add "))
async def admin_wallet_add(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("فرمت: /admin_wallet_add <username|telegram_id> <amount_IRR>")
        return
    ref = parts[1].strip()
    try:
        amount = Decimal(parts[2])
    except Exception:
        await message.answer("مبلغ نامعتبر است.")
        return
    async with session_scope() as session:
        user = None
        if ref.isdigit():
            user = await session.scalar(select(User).where(User.telegram_id == int(ref)))
        else:
            user = await session.scalar(select(User).where(User.marzban_username == ref))
        if not user:
            await message.answer("کاربر یافت نشد.")
            return
        user.balance = (Decimal(user.balance or 0) + amount)
        await log_audit(session, actor="admin", action="wallet_manual_add", target_type="user", target_id=user.id, meta=str({"amount": str(amount)}))
        await session.commit()
    try:
        tmn_add = int((amount/Decimal('10')).to_integral_value())
        new_tmn = int((Decimal(user.balance or 0)/Decimal('10')).to_integral_value())
        await message.bot.send_message(chat_id=user.telegram_id, text=f"✅ شارژ دستی توسط ادمین: +{tmn_add:,} تومان\nموجودی جدید: {new_tmn:,} تومان")
    except Exception:
        pass
    await message.answer(f"انجام شد. موجودی جدید {user.marzban_username}: {int((user.balance or 0)/10):,} تومان")


@router.message(F.text.startswith("/admin_wallet_add_tmn "))
async def admin_wallet_add_tmn(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("فرمت: /admin_wallet_add_tmn <username|telegram_id> <amount_TMN>")
        return
    ref = parts[1].strip()
    try:
        tmn = Decimal(parts[2])
        if tmn <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است.")
        return
    amount = tmn * Decimal('10')
    async with session_scope() as session:
        user = None
        if ref.isdigit():
            user = await session.scalar(select(User).where(User.telegram_id == int(ref)))
        else:
            user = await session.scalar(select(User).where(User.marzban_username == ref))
        if not user:
            await message.answer("کاربر یافت نشد.")
            return
        user.balance = (Decimal(user.balance or 0) + amount)
        await log_audit(session, actor="admin", action="wallet_manual_add", target_type="user", target_id=user.id, meta=str({"amount": str(amount)}))
        await session.commit()
    try:
        new_tmn = int((Decimal(user.balance or 0)/Decimal('10')).to_integral_value())
        await message.bot.send_message(chat_id=user.telegram_id, text=f"✅ شارژ دستی توسط ادمین: +{int(tmn):,} تومان\nموجودی جدید: {new_tmn:,} تومان")
    except Exception:
        pass
    await message.answer(f"انجام شد. موجودی جدید {user.marzban_username}: {int((user.balance or 0)/10):,} تومان")
