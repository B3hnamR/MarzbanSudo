from __future__ import annotations

import os
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Tuple
import logging

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, update, desc

from app.db.session import session_scope
from app.db.models import User, WalletTopUp, Setting
from app.services.audit import log_audit
from app.services.security import has_capability_async, CAP_WALLET_MODERATE, get_admin_ids
from app.utils.username import tg_username
from app.utils.intent_store import set_intent_json, get_intent_json, clear_intent

router = Router()
logger = logging.getLogger(__name__)

# Helpers
_DIGIT_MAP = str.maketrans(
    {
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
        ",": "", "٬": "", " ": "", "\u200f": "", "\u200e": "",
        "٫": "."
    }
)

def _normalize_amount(txt: str) -> str:
    # Convert Persian digits to ASCII, remove thousands separators/spaces
    return (txt or "").strip().translate(_DIGIT_MAP)

# ===== Admin Manual Wallet Add (UI flow) =====
# Per-admin state: { admin_id: { 'stage': 'await_ref'|'await_unit'|'await_amount',
#                                'user_id': int|None, 'unit': 'IRR'|'TMN'|None } }
_WALLET_MANUAL_ADD_INTENT: Dict[int, Dict[str, object]] = {}


INFO_PREFIX = "\u200Fℹ️ "


def _text_matches(value: str | None, target: str) -> bool:
    if not isinstance(value, str):
        return False
    remove_map = str.maketrans('', '', '\u200c\u200f\u202a\u202b\u202c\u202d\u202e\ufeff\ufe0f')
    normalized = value.translate(remove_map).strip()
    target_normalized = target.translate(remove_map).strip()
    return normalized == target_normalized


@router.message(F.text == "➕ شارژ دستی")
@router.message(lambda m: _text_matches(getattr(m, "text", None), "➕ شارژ دستی"))
async def admin_wallet_manual_add_start(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    admin_id = message.from_user.id
    logger.info("wallet.admin_manual_add_start", extra={"extra": {"uid": admin_id}})
    # Best-effort: cancel any lingering admin user/manage intents to avoid cross-capture of numeric inputs
    try:
        from app.bot.handlers import admin_users as _au
        _au._USER_INTENTS.pop(admin_id, None)
        _au._SVC_INTENTS.pop(admin_id, None)
        _au._SEARCH_INTENT.pop(admin_id, None)
    except Exception:
        pass
    try:
        from app.bot.handlers import admin_manage as _am
        _am._APLANS_CREATE_INTENT.pop(admin_id, None)
        _am._APLANS_FIELD_INTENT.pop(admin_id, None)
        _am._APLANS_PRICE_INTENT.pop(admin_id, None)
    except Exception:
        pass
    logger.info("wallet.admin_manual_add_start.cleanup", extra={"extra": {"uid": admin_id}})
    # Set in-memory flag to enable admin manual-add capture handlers
    _WALLET_MANUAL_ADD_INTENT[admin_id] = {"active": True, "stage": "await_ref"}
    await set_intent_json(f"INTENT:WADM:{admin_id}", {"stage": "await_ref", "user_id": None, "unit": None, "ts": datetime.utcnow().isoformat()})
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="لغو", callback_data="walletadm:add:cancel")]])
    await message.answer("👤 لطفاً شناسه کاربر را ارسال کنید (نام‌کاربری یا 🆔 تلگرام).", reply_markup=kb)


@router.callback_query(F.data == "walletadm:add:cancel")
async def cb_admin_wallet_manual_add_cancel(cb: CallbackQuery) -> None:
    uid = cb.from_user.id if cb.from_user else None
    try:
        if uid:
            await clear_intent(f"INTENT:WADM:{uid}")
            _WALLET_MANUAL_ADD_INTENT.pop(uid, None)
    except Exception:
        pass
    await cb.answer("لغو شد")
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and (m.from_user.id in get_admin_ids()) and _WALLET_MANUAL_ADD_INTENT.get(m.from_user.id, {}).get("active") and _WALLET_MANUAL_ADD_INTENT.get(m.from_user.id, {}).get("stage") == "await_ref" and isinstance(getattr(m, "text", None), str) and __import__("re").fullmatch(r"^(?:\d{5,}|[a-z0-9_]{3,})$", (m.text or "").strip().lower().lstrip("@")) is not None)
async def admin_wallet_manual_add_ref(message: Message) -> None:
    admin_id = message.from_user.id
    logger.info("wallet.admin_manual_add_ref", extra={"extra": {"uid": admin_id, "text": (message.text or "")}})
    # Only handle when admin has an active manual-add intent at 'await_ref' stage
    payload = await get_intent_json(f"INTENT:WADM:{admin_id}")
    logger.info("wallet.admin_manual_add_ref.stage", extra={"extra": {"uid": admin_id, "stage": (payload or {}).get("stage")}})
    if not payload or payload.get("stage") != "await_ref":
        return
    if not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        _WALLET_MANUAL_ADD_INTENT.pop(admin_id, None)
        await message.answer("⛔️ شما دس��رسی ادمین ندارید.")
        return
    ref = (message.text or "").strip()
    norm = ref.strip().lower().lstrip("@")
    # Only accept valid refs: numeric tg_id or username-like [a-z0-9_]{3,}
    if not (norm.isdigit() or re.fullmatch(r"[a-z0-9_]{3,}", norm or "")):
        return
    async with session_scope() as session:
        created = False
        user = None
        if norm.isdigit():
            user = await session.scalar(select(User).where(User.telegram_id == int(norm)))
            if not user:
                tg_value = int(norm)
                username = tg_username(tg_value)
                user = User(
                    telegram_id=tg_value,
                    marzban_username=username,
                    subscription_token=None,
                    status="active",
                    data_limit_bytes=0,
                    balance=0,
                )
                session.add(user)
                await session.flush()
                await session.commit()
                created = True
        else:
            user = await session.scalar(select(User).where(User.marzban_username == norm))
        if not user:
            await message.answer("کاربر یافت نشد. مجدد شناسه صحیح را ارسال کنید یا لغو کنید.")
            return
        await set_intent_json(f"INTENT:WADM:{admin_id}", {"stage": "await_unit", "user_id": int(user.id), "unit": None, "ts": datetime.utcnow().isoformat()})
    _WALLET_MANUAL_ADD_INTENT[admin_id] = {**_WALLET_MANUAL_ADD_INTENT.get(admin_id, {"active": True}), "active": True, "stage": "await_unit"}
    if created:
        await message.answer(f"👤 کاربر جدید با شناسه {user.marzban_username} ایجاد شد.")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ورود مبلغ به تومان", callback_data="walletadm:add:unit:TMN"), InlineKeyboardButton(text="ورود مبلغ به ریال", callback_data="walletadm:add:unit:IRR")]])
    await message.answer("💱 واحد مبلغ را انتخاب کنید:", reply_markup=kb)


@router.callback_query(F.data.startswith("walletadm:add:unit:"))
async def cb_admin_wallet_manual_add_unit(cb: CallbackQuery) -> None:
    uid = cb.from_user.id if cb.from_user else None
    logger.info("wallet.admin_manual_add_unit.enter", extra={"extra": {"uid": uid, "data": cb.data}})
    payload = await get_intent_json(f"INTENT:WADM:{uid}") if uid else None
    if not payload or payload.get("stage") != "await_unit":
        await cb.answer()
        return
    if not await has_capability_async(uid, CAP_WALLET_MODERATE):
        try:
            if uid:
                await clear_intent(f"INTENT:WADM:{uid}")
        except Exception:
            pass
        await cb.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    unit = cb.data.split(":")[-1]
    logger.info("wallet.admin_manual_add_unit.choice", extra={"extra": {"uid": uid, "unit": unit}})
    if unit not in {"TMN", "IRR"}:
        await cb.answer("واحد نامعتبر", show_alert=True)
        return
    await set_intent_json(f"INTENT:WADM:{uid}", {"stage": "await_amount", "user_id": payload.get("user_id"), "unit": unit, "ts": datetime.utcnow().isoformat()})
    # Reflect stage in in-memory flag to guide handler routing
    _WALLET_MANUAL_ADD_INTENT[uid] = {**_WALLET_MANUAL_ADD_INTENT.get(uid, {"active": True}), "active": True, "stage": "await_amount"}
    await cb.message.answer("🔢 مبلغ را به صورت عدد ارسال کنید.")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and (m.from_user.id in get_admin_ids()) and _WALLET_MANUAL_ADD_INTENT.get(m.from_user.id, {}).get("active") and _WALLET_MANUAL_ADD_INTENT.get(m.from_user.id, {}).get("stage") == "await_amount" and isinstance(getattr(m, "text", None), str) and __import__("re").fullmatch(r"^[0-9\u06F0-\u06F9][0-9\u06F0-\u06F9,\.]*$", m.text or "") is not None)
async def admin_wallet_manual_add_amount(message: Message) -> None:
    admin_id = message.from_user.id
    logger.info("wallet.admin_manual_add_amount.enter", extra={"extra": {"uid": admin_id, "text": (message.text or "")}})
    payload = await get_intent_json(f"INTENT:WADM:{admin_id}")
    logger.info("wallet.admin_manual_add_amount.stage", extra={"extra": {"uid": admin_id, "stage": (payload or {}).get("stage"), "unit": (payload or {}).get("unit"), "user_id": (payload or {}).get("user_id")}})
    if not payload or not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        try:
            await clear_intent(f"INTENT:WADM:{admin_id}")
        except Exception:
            pass
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        raw = _normalize_amount(message.text)
        # Allow integer or decimal; convert to Decimal
        val = Decimal(raw)
        if val <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. یک عدد مثبت ارسال کنید یا لغو کنید.")
        return
    unit = payload.get("unit")
    user_id = payload.get("user_id")
    if unit not in {"TMN", "IRR"} or not user_id:
        try:
            await clear_intent(f"INTENT:WADM:{admin_id}")
        except Exception:
            pass
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
    try:
        await clear_intent(f"INTENT:WADM:{admin_id}")
    except Exception:
        pass
    _WALLET_MANUAL_ADD_INTENT.pop(admin_id, None)
    await message.answer(f"✅ انجام شد. موجودی جدید {target_username}: {new_tmn:,} تومان")

# Fallback: capture arbitrary text for admin amount stage
@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and (m.from_user.id in get_admin_ids()) and _WALLET_MANUAL_ADD_INTENT.get(m.from_user.id, {}).get("active") and _WALLET_MANUAL_ADD_INTENT.get(m.from_user.id, {}).get("stage") == "await_amount" and isinstance(getattr(m, "text", None), str) and __import__("re").search(r"\d", m.text or "") is not None)
async def admin_wallet_manual_add_amount_fallback(message: Message) -> None:
    admin_id = message.from_user.id if message.from_user else None
    logger.info("wallet.admin_manual_add_amount_fallback.enter", extra={"extra": {"uid": admin_id, "text": (message.text or "")}})
    if not admin_id:
        return
    payload = await get_intent_json(f"INTENT:WADM:{admin_id}")
    logger.info("wallet.admin_manual_add_amount_fallback.stage", extra={"extra": {"uid": admin_id, "stage": (payload or {}).get("stage"), "unit": (payload or {}).get("unit"), "user_id": (payload or {}).get("user_id")}})
    if not payload or payload.get("stage") != "await_amount":
        return
    if not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        await clear_intent(f"INTENT:WADM:{admin_id}")
        return
    raw = _normalize_amount(message.text or "")
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        await message.answer("مبلغ نامعتبر است. یک عدد مثبت ارسال کنید یا لغو کنید.")
        return
    try:
        val = Decimal(m.group(1))
        if val <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. یک عدد مثبت ارسال کنید یا لغو کنید.")
        return
    unit = payload.get("unit")
    user_id = payload.get("user_id")
    if unit not in {"TMN", "IRR"} or not user_id:
        await clear_intent(f"INTENT:WADM:{admin_id}")
        await message.answer("وضعیت نامعتبر. از ابتدا تلاش کنید.")
        return
    irr = val * Decimal('10') if unit == "TMN" else val
    tmn_add = int((irr/Decimal('10')).to_integral_value())
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.id == int(user_id)))
        if not user:
            await clear_intent(f"INTENT:WADM:{admin_id}")
            await message.answer("کاربر یافت نشد.")
            return
        user.balance = (Decimal(user.balance or 0) + irr)
        await log_audit(session, actor="admin", action="wallet_manual_add", target_type="user", target_id=user.id, meta=str({"amount": str(irr)}))
        await session.commit()
        new_tmn = int((Decimal(user.balance or 0)/Decimal('10')).to_integral_value())
        target_tg = user.telegram_id
        target_username = user.marzban_username
    try:
        await message.bot.send_message(chat_id=target_tg, text=f"✅ شارژ دستی توسط ادمین: +{tmn_add:,} تومان\nموجودی جدید: {new_tmn:,} تومان")
    except Exception:
        pass
    await clear_intent(f"INTENT:WADM:{admin_id}")
    await message.answer(f"✅ انجام شد. موجودی جدید {target_username}: {new_tmn:,} تومان")


@router.message(F.text == "💳 درخواست‌های شارژ")
async def admin_wallet_pending_topups(message: Message) -> None:
    # List up to 9 pending wallet top-ups with Approve/Reject buttons
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    # Cancel any lingering manual-add intent to avoid cross-capture
    try:
        await clear_intent(f"INTENT:WADM:{message.from_user.id}")
    except Exception:
        pass
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
        await message.answer(f"{INFO_PREFIX}هیچ درخواستی برای بررسی موجود نیست.")
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



# In-memory intent storage (per-process)
# _TOPUP_INTENT moved to DB-backed intents (see intent_store)
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


async def _get_min_topup_value(session) -> Decimal:
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
    # Clear any lingering admin manual-add intent to avoid cross-capture when admin uses wallet as a user
    try:
        await clear_intent(f"INTENT:WADM:{tg_id}")
    except Exception:
        pass
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if not user:
            # Auto-register minimal user record to enable wallet usage before first purchase
            username = tg_username(tg_id)
            user = User(
                telegram_id=tg_id,
                marzban_username=username,
                subscription_token=None,
                status="active",
                data_limit_bytes=0,
                balance=0,
            )
            session.add(user)
            await session.flush()
            await session.commit()
        bal = Decimal(user.balance or 0)
        min_amt = await _get_min_topup_value(session)
        options = _amount_options(min_amt)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"شارژ {int(a/10):,} تومان", callback_data=f"wallet:amt:{int(a)}")] for a in options
        ] + [[InlineKeyboardButton(text="مبلغ دلخواه", callback_data="wallet:custom")]])
        await message.answer(
            f"👛 موجودی کیف پول شما: {int(bal/10):,} تومان\n⬇️ یکی از مبالغ زیر را انتخاب کنید یا مبلغ دلخواه را وارد کنید.",
            reply_markup=kb,
        )


@router.callback_query(F.data == "wallet:custom")
async def cb_wallet_custom(cb: CallbackQuery) -> None:
    await cb.message.answer("💵 مبلغ دلخواه را به تومان ارسال کنید (مثلاً 76000 برای ۷۶۰۰۰ تومان).")
    # Clear admin manual-add intent for this user (if admin), to avoid text capture conflicts
    try:
        await clear_intent(f"INTENT:WADM:{cb.from_user.id}")
    except Exception:
        pass
    await set_intent_json(f"INTENT:TOPUP:{cb.from_user.id}", {"amount": "-1", "ts": datetime.utcnow().isoformat()})
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

@router.message(F.text.regexp(r"^[0-9\u06F0-\u06F9][0-9\u06F0-\u06F9,\.]{0,13}$"))
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
    payload = await get_intent_json(f"INTENT:TOPUP:{uid}")
    if not payload or str(payload.get("amount")) != "-1":
        return
    try:
        raw = _normalize_amount(message.text)
        toman = Decimal(raw)
        if toman <= 0:
            raise ValueError
    except Exception:
        await message.answer("مبلغ نامعتبر است. دوباره ارسال کنید.")
        return
    rial = toman * Decimal("10")
    async with session_scope() as session:
        min_irr = await _get_min_topup_value(session)
        max_irr = await _get_max_topup(session)
    if rial < min_irr:
        await message.answer(
            f"⚠️ حداقل مبلغ شارژ {int(min_irr/Decimal('10')):,} تومان است. لطفاً مبلغ بیشتری وارد کنید."
        )
        await set_intent_json(f"INTENT:TOPUP:{uid}", {"amount": "-1", "ts": datetime.utcnow().isoformat()})
        return
    if max_irr is not None and rial > max_irr:
        await message.answer(
            f"⚠️ حداکثر مبلغ شارژ {int(max_irr/Decimal('10')):,} تومان است. لطفاً مبلغ کمتری وارد کنید."
        )
        await set_intent_json(f"INTENT:TOPUP:{uid}", {"amount": "-1", "ts": datetime.utcnow().isoformat()})
        return
    await set_intent_json(f"INTENT:TOPUP:{uid}", {"amount": str(int(rial)), "ts": datetime.utcnow().isoformat()})
    await message.answer(f"✅ مبلغ {int(toman):,} تومان انتخاب شد.\n🧾 لطفاً عکس رسید پرداخت را ارسال کنید.")


# Fallback: if user sends arbitrary text while TOPUP intent is active, try to parse amount
@router.message(F.text.regexp(r".*[0-9\u06F0-\u06F9].*"))
async def handle_wallet_custom_amount_fallback(message: Message) -> None:
    if not message.from_user or not isinstance(getattr(message, "text", None), str):
        return
    uid = message.from_user.id
    payload = await get_intent_json(f"INTENT:TOPUP:{uid}")
    logger.info("wallet.custom_amount_fallback", extra={"extra": {"uid": uid, "has_intent": bool(payload), "text": (message.text or "")[:48]}})
    if not payload or str(payload.get("amount")) != "-1":
        return
    raw = _normalize_amount(message.text)
    # Extract leading digits (and optional decimal) from arbitrary text
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        return
    try:
        toman = Decimal(m.group(1))
        if toman <= 0:
            raise ValueError
    except Exception:
        return
    rial = toman * Decimal("10")
    async with session_scope() as session:
        min_irr = await _get_min_topup_value(session)
        max_irr = await _get_max_topup(session)
    if rial < min_irr or (max_irr is not None and rial > max_irr):
        await set_intent_json(f"INTENT:TOPUP:{uid}", {"amount": "-1", "ts": datetime.utcnow().isoformat()})
        return
    await set_intent_json(f"INTENT:TOPUP:{uid}", {"amount": str(int(rial)), "ts": datetime.utcnow().isoformat()})
    await message.answer(f"✅ مبلغ {int(toman):,} تومان انتخاب شد.\n🧾 لطفاً عکس رسید پرداخت را ارسال کنید.")

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
        min_irr = await _get_min_topup_value(session)
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
    await set_intent_json(f"INTENT:TOPUP:{cb.from_user.id}", {"amount": str(int(amount)), "ts": datetime.utcnow().isoformat()})
    await cb.message.answer(
        f"✅ مبلغ {int(amount/10):,} تومان انتخاب شد.\n🧾 لطفاً عکس رسید پرداخت را ارسال کنید (بدون نیاز به متن)."
    )
    await cb.answer()


@router.message(F.photo | F.document)
async def handle_wallet_photo(message: Message) -> None:
    # Only process as top-up if user has an active intent; otherwise ignore here
    if not message.from_user:
        return
    tg_id = message.from_user.id
    payload = await get_intent_json(f"INTENT:TOPUP:{tg_id}")
    if not payload:
        return
    # TTL check (15 minutes)
    try:
        ts_s = str(payload.get("ts"))
        from datetime import datetime as _dt
        expired = (_dt.utcnow() - _dt.fromisoformat(ts_s)).total_seconds() > 900
    except Exception:
        expired = True
    if expired:
        await clear_intent(f"INTENT:TOPUP:{tg_id}")
        await message.answer("درخواست شارژ منقضی شد. لطفاً از منوی کیف پول دوباره اقدام کنید.")
        return
    try:
        amount = Decimal(str(payload.get("amount")))
    except Exception:
        await clear_intent(f"INTENT:TOPUP:{tg_id}")
        return
    # mimic pop behaviour: clear intent now so user must reselect on failures
    await clear_intent(f"INTENT:TOPUP:{tg_id}")
    file_id = None
    is_photo = False
    if message.photo:
        file_id = message.photo[-1].file_id
        is_photo = True
    elif message.document:
        mime = (message.document.mime_type or "").lower()
        # Allow only images or PDF documents for receipts
        if not (mime.startswith("image/") or mime == "application/pdf"):
            await message.answer("فقط تصویر یا PDF مجاز است. لطفاً رسید را به‌صورت عکس یا PDF ارسال کنید.")
            return
        file_id = message.document.file_id
    if not file_id:
        return
    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        if not user:
            # Auto-register minimal user to attach the top-up
            username = tg_username(tg_id)
            user = User(
                telegram_id=tg_id,
                marzban_username=username,
                subscription_token=None,
                status="active",
                data_limit_bytes=0,
                balance=0,
            )
            session.add(user)
            await session.flush()
        min_irr = await _get_min_topup_value(session)
        max_irr = await _get_max_topup(session)
        if amount < min_irr:
            await message.answer(
                f"⚠️ مبلغ انتخاب‌شده کمتر از حداقل مجاز است ({int(min_irr/Decimal('10')):,} تومان). لطفاً از منوی کیف پول دوباره اقدام کنید."
            )
            return
        if max_irr is not None and amount > max_irr:
            await message.answer(
                f"⚠️ مبلغ انتخاب‌شده بیشتر از حداکثر مجاز است ({int(max_irr/Decimal('10')):,} تومان). لطفاً از منوی کیف پول دوباره اقدام کنید."
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
    await message.answer("✅ درخواست شارژ ثبت شد و برای ادمین ارسال گردید.")
    try:
        import logging
        from app.utils.correlation import get_correlation_id
        logging.getLogger(__name__).info(
            "wallet topup created",
            extra={"extra": {"cid": get_correlation_id(), "topup_id": topup.id, "user_id": user.id, "amount_irr": str(amount), "mime": (message.document.mime_type if message.document else "photo")}},
        )
    except Exception:
        pass
    # Forward to admins
    admin_ids = list(get_admin_ids())
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
        await cb.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        topup_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("شناسه نامعتبر", show_alert=True)
        return
    await set_intent_json(f"INTENT:WREJ:{cb.from_user.id}", {"topup_id": topup_id, "ts": datetime.utcnow().isoformat()})
    # Set in-memory capture flag so the next admin text is captured by reject-with-reason handler only in this state
    _WALLET_REJECT_REASON_INTENT[cb.from_user.id] = topup_id
    orig_caption = getattr(cb.message, "caption", None)
    orig_text = getattr(cb.message, "text", None)
    content = orig_caption if orig_caption is not None else (orig_text or "")
    kind = "caption" if orig_caption is not None else "text"
    await set_intent_json(
        f"INTENT:WREJCTX:{cb.from_user.id}",
        {"chat_id": cb.message.chat.id, "message_id": cb.message.message_id, "content": content or "", "kind": kind, "ts": datetime.utcnow().isoformat()},
    )
    await cb.message.answer("📝 لطفاً دلیل رد درخواست را ارسال کنید (یک پیام متنی).")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and m.from_user and (m.from_user.id in get_admin_ids()) and _WALLET_REJECT_REASON_INTENT.get(m.from_user.id, False) and isinstance(getattr(m, "text", None), str))
async def admin_wallet_reject_with_reason_text(message: Message) -> None:
    admin_id = message.from_user.id if message.from_user else None
    if not admin_id or not await has_capability_async(admin_id, CAP_WALLET_MODERATE):
        try:
            await clear_intent(f"INTENT:WREJ:{admin_id}")
            await clear_intent(f"INTENT:WREJCTX:{admin_id}")
        except Exception:
            pass
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    reason = message.text.strip()
    payload = await get_intent_json(f"INTENT:WREJ:{admin_id}")
    ctx = await get_intent_json(f"INTENT:WREJCTX:{admin_id}")
    if not payload:
        return
    topup_id = int(payload.get("topup_id"))
    user_telegram_id = None
    async with session_scope() as session:
        row = await session.execute(select(WalletTopUp, User).join(User, WalletTopUp.user_id == User.id).where(WalletTopUp.id == topup_id))
        data = row.first()
        if not data:
            await message.answer("⚠️ درخواست یافت نشد.")
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
        await message.bot.send_message(chat_id=user_telegram_id, text=f"❌ درخواست شارژ شما رد شد.\n📝 دلیل: {reason}")
    except Exception:
        pass
    if ctx:
        # ctx may be a dict (new storage) or a tuple/list (legacy). Handle both safely.
        try:
            if isinstance(ctx, (list, tuple)) and len(ctx) >= 4:
                chat_id, msg_id, content, kind = ctx[:4]
            else:
                chat_id = int(ctx.get("chat_id"))
                msg_id = int(ctx.get("message_id"))
                content = ctx.get("content") or ""
                kind = ctx.get("kind") or "text"
        except Exception:
            chat_id = None
            msg_id = None
            content = ""
            kind = "text"
        new_content = (content or "")
        append_txt = f"رد شد ❌\nدلیل: {reason}"
        if new_content:
            new_content = new_content + "\n\n" + append_txt
        else:
            new_content = append_txt
        if (chat_id is not None) and (msg_id is not None):
            try:
                if kind == "caption":
                    await message.bot.edit_message_caption(chat_id=chat_id, message_id=msg_id, caption=new_content)
                else:
                    await message.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_content)
            except Exception:
                pass
    try:
        await clear_intent(f"INTENT:WREJ:{admin_id}")
        await clear_intent(f"INTENT:WREJCTX:{admin_id}")
    except Exception:
        pass
    # Clear in-memory capture flag
    _WALLET_REJECT_REASON_INTENT.pop(admin_id, None)
    await message.answer("✅ رد شد و دلیل به کاربر اطلاع داده شد.")


@router.callback_query(F.data.startswith("wallet:approve:"))
async def cb_wallet_approve(cb: CallbackQuery) -> None:
    if not cb.from_user:
        await cb.answer()
        return
    if not await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE):
        await cb.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    try:
        topup_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("⛔️ شناسه نامعتبر", show_alert=True)
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
            await cb.message.bot.send_message(chat_id=user_telegram_id, text=f"✅💳 شارژ شما تایید شد.\n👛 موجودی جدید: {new_balance_for_msg:,} تومان")
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
# _get_min_topup_value defined above and used uniformly


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
@router.message(lambda m: _text_matches(getattr(m, "text", None), "💼 تنظیمات کیف پول"))
async def admin_wallet_settings_menu(message: Message) -> None:
    logger.info("wallet.admin_settings_menu: enter", extra={"extra": {"uid": getattr(message.from_user, 'id', None)}})
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        logger.info("wallet.admin_settings_menu: no_capability", extra={"extra": {"uid": getattr(message.from_user, 'id', None)}})
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    # Best-effort: cancel any lingering plan management intents to avoid cross-capture of inputs
    try:
        from app.bot.handlers import admin_manage as _am
        uid = message.from_user.id
        _am._APLANS_CREATE_INTENT.pop(uid, None)
        _am._APLANS_FIELD_INTENT.pop(uid, None)
        _am._APLANS_PRICE_INTENT.pop(uid, None)
        # Also clear manual wallet add intent (in-memory and DB) to prevent cross-capture
        _WALLET_MANUAL_ADD_INTENT.pop(uid, None)
        from app.utils.intent_store import clear_intent as _clear
        await _clear(f"INTENT:WADM:{uid}")
        # Also clear any lingering reject-with-reason intents to avoid mis-capturing admin texts
        _WALLET_REJECT_REASON_INTENT.pop(uid, None)
        await _clear(f"INTENT:WREJ:{uid}")
        await _clear(f"INTENT:WREJCTX:{uid}")
    except Exception:
        pass
    async with session_scope() as session:
        min_irr = await _get_min_topup_value(session)
        max_irr = await _get_max_topup_value(session)
    header = "💼 تنظیمات کیف پول\n"
    header += f"💵 حداقل مبلغ شارژ فعلی: {int(min_irr/Decimal('10')):,} تومان\n"
    header += f"📈 حداکثر مبلغ شارژ فعلی: {int(max_irr/Decimal('10')):,} تومان\n" if max_irr else "🚫 حداکثر مبلغ شارژ فعلی: بدون سقف\n"
    text = header + "🧭 یکی از گزینه‌ها را انتخاب کنید یا مبلغ دلخواه را تعیین کنید."
    await message.answer(text, reply_markup=_admin_wallet_keyboard(min_irr, max_irr))


@router.callback_query(F.data == "walletadmin:min:refresh")
async def cb_walletadmin_min_refresh(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    async with session_scope() as session:
        min_irr = await _get_min_topup_value(session)
        max_irr = await _get_max_topup_value(session)
    header = "💼 تنظیمات کیف پول\n"
    header += f"💵 حداقل مبلغ شارژ فعلی: {int(min_irr/Decimal('10')):,} تومان\n"
    header += f"📈 حداکثر مبلغ شارژ فعلی: {int(max_irr/Decimal('10')):,} تومان\n" if max_irr else "🚫 حداکثر مبلغ شارژ فعلی: بدون سقف\n"
    text = header + "🧭 یکی از گزینه‌ها را انتخاب کنید یا مبلغ دلخواه را تعیین کنید."
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
        await cb.message.bot.send_message(chat_id=user.telegram_id, text=f"❌ درخواست شارژ شما رد شد.\n💵 مبلغ: {int((topup.amount or 0)/10):,} تومان")
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
