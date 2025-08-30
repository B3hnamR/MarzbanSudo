from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, update

from app.db.session import session_scope
from app.db.models import User, WalletTopUp, Setting
from app.services.audit import log_audit
from app.services.security import has_capability_async, CAP_WALLET_MODERATE

router = Router()


def _admin_ids() -> set[int]:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "")
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}


def _is_admin_user_id(uid: int | None) -> bool:
    return bool(uid and uid in _admin_ids())

# In-memory intent storage (per-process)
_TOPUP_INTENT: Dict[int, Decimal] = {}
# Admin intent for setting minimum top-up (awaiting amount input)
_WALLET_ADMIN_MIN_INTENT: Dict[int, bool] = {}


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


@router.message(F.text.regexp(r"^\d{4,10}$"))
async def handle_wallet_custom_amount(message: Message) -> None:
    if not message.from_user:
        return
    if message.from_user.id not in _TOPUP_INTENT or _TOPUP_INTENT[message.from_user.id] != Decimal("-1"):
        return
    try:
        toman = Decimal(message.text)
        if toman <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. دوباره ارسال کنید.")
        return
    rial = toman * Decimal("10")
    _TOPUP_INTENT[message.from_user.id] = rial
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
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Approve ✅", callback_data=f"wallet:approve:{topup.id}"), InlineKeyboardButton(text="Reject ❌", callback_data=f"wallet:reject:{topup.id}")]])
        for aid in admin_ids:
            try:
                if is_photo:
                    await message.bot.send_photo(chat_id=aid, photo=file_id, caption=caption, reply_markup=kb)
                else:
                    await message.bot.send_document(chat_id=aid, document=file_id, caption=caption, reply_markup=kb)
            except Exception:
                pass


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
    cap = cb.message.caption or "درخواست شارژ کیف پول"
    await cb.message.edit_caption(cap + "\n\nApproved ✅")
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


def _admin_min_keyboard(min_irr: Decimal) -> InlineKeyboardMarkup:
    tmn = int(min_irr / Decimal("10"))
    x2 = min_irr * 2
    x5 = min_irr * 5
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"تنظیم به {tmn:,} تومان", callback_data=f"walletadmin:min:set:{int(min_irr)}")],
        [InlineKeyboardButton(text=f"{int(x2/Decimal('10')):,} تومان", callback_data=f"walletadmin:min:set:{int(x2)}"), InlineKeyboardButton(text=f"{int(x5/Decimal('10')):,} تومان", callback_data=f"walletadmin:min:set:{int(x5)}")],
        [InlineKeyboardButton(text="مبلغ دلخواه", callback_data="walletadmin:min:custom")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="walletadmin:min:refresh")],
    ])


@router.message(F.text == "💼 تنظیمات کیف پول")
async def admin_wallet_settings_menu(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    async with session_scope() as session:
        min_irr = await _get_min_topup_value(session)
    text = (
        "تنظیمات کیف پول\n"
        f"حداقل مبلغ شارژ فعلی: {int(min_irr/Decimal('10')):,} تومان\n"
        "یکی از گزینه‌ها را انتخاب کنید یا مبلغ دلخواه را تعیین کنید."
    )
    await message.answer(text, reply_markup=_admin_min_keyboard(min_irr))


@router.callback_query(F.data == "walletadmin:min:refresh")
async def cb_walletadmin_min_refresh(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    async with session_scope() as session:
        min_irr = await _get_min_topup_value(session)
    try:
        await cb.message.edit_text(
            "تنظیمات کیف پول\n"
            f"حداقل مبلغ شارژ فعلی: {int(min_irr/Decimal('10')):,} تومان\n"
            "یکی از گزینه‌ها را انتخاب کنید یا مبلغ دلخواه را تعیین کنید.",
            reply_markup=_admin_min_keyboard(min_irr)
        )
    except Exception:
        await cb.message.answer(
            "تنظیمات کیف پول\n"
            f"حداقل مبلغ شارژ فعلی: {int(min_irr/Decimal('10')):,} تومان\n"
            "یکی از گزینه‌ها را انتخاب کنید یا مبلغ دلخواه را تعیین کنید.",
            reply_markup=_admin_min_keyboard(min_irr)
        )
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
    await cb.message.answer("مبلغ دلخواه را به تومان ارسال کنید (مثلاً 150000 برای ۱۵۰ هزار تومان).")
    await cb.answer()


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
    cap = cb.message.caption or "درخواست شارژ کیف پول"
    await cb.message.edit_caption(cap + "\n\nRejected ❌")
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
        await message.answer("فرمت: /admin_wallet_add <username> <amount>")
        return
    username = parts[1].strip()
    try:
        amount = Decimal(parts[2])
    except Exception:
        await message.answer("مبلغ نامعتبر است.")
        return
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.marzban_username == username))
        if not user:
            await message.answer("کاربر یافت نشد.")
            return
        user.balance = (Decimal(user.balance or 0) + amount)
        await log_audit(session, actor="admin", action="wallet_manual_add", target_type="user", target_id=user.id, meta=str({"amount": str(amount)}))
        await session.commit()
    await message.answer(f"اضافه شد. موجودی جدید {username}: {int((user.balance or 0)/10):,} تومان")
