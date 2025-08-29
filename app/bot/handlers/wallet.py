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

router = Router()

# In-memory intent storage (per-process)
_TOPUP_INTENT: Dict[int, Decimal] = {}


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
            [InlineKeyboardButton(text=f"شارژ {int(a):,} IRR", callback_data=f"wallet:amt:{int(a)}")] for a in options
        ])
        await message.answer(
            f"موجودی کیف پول شما: {bal:.0f} IRR\nبرای شارژ یکی از مبالغ زیر را انتخاب کنید.",
            reply_markup=kb,
        )


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
        f"مبلغ {int(amount):,} IRR انتخاب شد.\nلطفاً عکس رسید پرداخت را ارسال کنید (بدون نیاز به متن)."
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
            f"Amount: {int(amount):,} IRR\n"
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
    try:
        topup_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    admin_id = cb.from_user.id
    async with session_scope() as session:
        row = await session.execute(select(WalletTopUp, User).join(User, WalletTopUp.user_id == User.id).where(WalletTopUp.id == topup_id))
        data = row.first()
        if not data:
            await cb.answer("TopUp not found", show_alert=True)
            return
        topup, user = data
        if topup.status != "pending":
            await cb.answer("Already processed", show_alert=True)
            return
        # Update balance and topup
        user.balance = (Decimal(user.balance or 0) + Decimal(topup.amount or 0))
        topup.status = "approved"
        topup.admin_id = admin_id
        topup.processed_at = datetime.utcnow()
        await log_audit(session, actor="admin", action="wallet_topup_approved", target_type="wallet_topup", target_id=topup.id, meta=str({"admin_id": admin_id}))
        await session.commit()
    try:
        await cb.message.bot.send_message(chat_id=user.telegram_id, text=f"شارژ شما تایید شد. موجودی جدید: {int(user.balance):,} IRR")
    except Exception:
        pass
    await cb.message.edit_text(cb.message.caption + "\n\nApproved ✅")
    await cb.answer("Approved")


@router.callback_query(F.data.startswith("wallet:reject:"))
async def cb_wallet_reject(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    try:
        topup_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    admin_id = cb.from_user.id
    async with session_scope() as session:
        topup = await session.scalar(select(WalletTopUp).where(WalletTopUp.id == topup_id))
        if not topup:
            await cb.answer("TopUp not found", show_alert=True)
            return
        if topup.status != "pending":
            await cb.answer("Already processed", show_alert=True)
            return
        topup.status = "rejected"
        topup.admin_id = admin_id
        topup.processed_at = datetime.utcnow()
        await log_audit(session, actor="admin", action="wallet_topup_rejected", target_type="wallet_topup", target_id=topup.id, meta=str({"admin_id": admin_id}))
        await session.commit()
    await cb.message.edit_text(cb.message.caption + "\n\nRejected ❌")
    await cb.answer("Rejected")


# Admin settings
@router.message(F.text.startswith("/admin_wallet_set_min "))
async def admin_wallet_set_min(message: Message) -> None:
    if not message.from_user:
        return
    admin_ids = [int(x.strip()) for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip().isdigit()]
    if message.from_user.id not in admin_ids:
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
    admin_ids = [int(x.strip()) for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip().isdigit()]
    if not message.from_user or message.from_user.id not in admin_ids:
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
        await message.answer(f"موجودی {username}: {int(user.balance or 0):,} IRR")


@router.message(F.text.startswith("/admin_wallet_add "))
async def admin_wallet_add(message: Message) -> None:
    admin_ids = [int(x.strip()) for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip().isdigit()]
    if not message.from_user or message.from_user.id not in admin_ids:
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
    await message.answer(f"اضافه شد. موجودی جدید {username}: {int(user.balance):,} IRR")
