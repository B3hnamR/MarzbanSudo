from __future__ import annotations

import os
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.db.session import session_scope
from app.db.models import Setting, User
from app.services.security import has_capability_async, CAP_WALLET_MODERATE, is_admin_uid
from sqlalchemy import select
from app.utils.username import tg_username
from app.utils.text_normalize import text_matches

# Import existing handlers to reuse their logic without showing slash commands
from app.bot.handlers.plans import handle_plans as plans_handler
from app.bot.handlers.orders import handle_orders as orders_handler
from app.bot.handlers.account import handle_account as account_handler
from app.bot.handlers.admin_orders import admin_orders_pending as admin_pending_handler, admin_orders_recent as admin_recent_handler
from app.bot.handlers.admin_manage import admin_show_plans_menu as admin_plans_menu_handler
from app.bot.handlers.wallet import (
    wallet_menu as wallet_menu_handler,
    admin_wallet_settings_menu as wallet_settings_handler,
    admin_wallet_manual_add_start as wallet_manual_add_start,
    admin_wallet_pending_topups as wallet_pending_handler,
    admin_wallet_manual_add_ref as wallet_manual_add_ref,
    handle_wallet_custom_amount as wallet_custom_amount_handler,
    admin_wallet_manual_add_amount as wallet_manual_add_amount_handler,
    admin_wallet_limits_numeric_input as wallet_limits_numeric_input_handler,
)

router = Router()

logger = logging.getLogger(__name__)



def _is_admin(msg: Message) -> bool:
    return bool(msg.from_user and is_admin_uid(msg.from_user.id))


def _user_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 خرید سرویس"), KeyboardButton(text="📦 سفارش‌ها")],
            [KeyboardButton(text="👤 اکانت من"), KeyboardButton(text="💳 کیف پول")],
            [KeyboardButton(text="🧪 دریافت تست")],
        ], resize_keyboard=True
    )


def _admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 خرید سرویس"), KeyboardButton(text="📦 سفارش‌های من")],
            [KeyboardButton(text="👤 اکانت من"), KeyboardButton(text="💳 کیف پول")],
            [KeyboardButton(text="⚙️ تنظیمات ربات")],
        ], resize_keyboard=True
    )


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    logger.info("start.handle_start: enter", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None), 'text': getattr(message, 'text', None)}})
    # Ensure a DB user record exists for anyone who starts the bot
    try:
        if message.from_user:
            tg_id = message.from_user.id
            async with session_scope() as session:
                existing = await session.scalar(select(User).where(User.telegram_id == tg_id))
                if not existing:
                    username = tg_username(tg_id)
                    u = User(
                        telegram_id=tg_id,
                        marzban_username=username,
                        subscription_token=None,
                        status="active",
                        data_limit_bytes=0,
                        balance=0,
                    )
                    session.add(u)
                    await session.flush()
                    await session.commit()
                # Upsert Telegram username to settings for search (lowercased)
                try:
                    tg_un = getattr(message.from_user, "username", None)
                    if tg_un:
                        tg_un_l = tg_un.strip().lower()
                        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:TG_USERNAME"))
                        if not row:
                            session.add(Setting(key=f"USER:{tg_id}:TG_USERNAME", value=tg_un_l))
                        else:
                            row.value = tg_un_l
                        await session.flush()
                        await session.commit()
                except Exception:
                    pass
    except Exception:
        pass

    # Channel membership gate (applies to all users including admins)
    channel = os.getenv("REQUIRED_CHANNEL", "").strip()
    if channel and message.from_user:
        try:
            member = await message.bot.get_chat_member(chat_id=channel, user_id=message.from_user.id)
            status = getattr(member, "status", None)
            if status not in {"member", "creator", "administrator"}:
                join_url = f"https://t.me/{channel.lstrip('@')}"
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 عضویت در کانال", url=join_url)],
                    [InlineKeyboardButton(text="من عضو شدم ✅", callback_data="chk:chan")],
                ])
                txt = (
                    "برای استفاده از ربات، ابتدا در کانال عضو شوید.\n"
                    "پس از عضویت، روی دکمه \"من عضو شدم ✅\" بزنید."
                )
                logger.info("start.handle_start: gate enforced", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
                await message.answer(txt, reply_markup=kb)
                return
        except Exception:
            # If we cannot verify membership (bot not admin in channel), still enforce gate UI
            join_url = f"https://t.me/{channel.lstrip('@')}"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 عضویت در کانال", url=join_url)],
                [InlineKeyboardButton(text="من عضو شدم ✅", callback_data="chk:chan")],
            ])
            txt = (
            "برای استفاده از ربات، ابتدا در کانال عضو شوید.\n"
            "توجه: برای بررسی خودکار عضویت، باید ربات را به عنوان ادمین کانال اضافه کنید.\n"
            "پس از عضویت، روی دکمه \"من عضو شدم ✅\" بزنید."
            )
            logger.info("start.handle_start: gate enforced (fallback)", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
            await message.answer(txt, reply_markup=kb)
            return
    if _is_admin(message):
        logger.info("start.handle_start: admin branch", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
        text = (
            "👋 به MarzbanSudo خوش آمدید، ادمین عزیز!\n\n"
            "🧭 از دکمه‌ها برای مدیریت استفاده کنید. دستورات اسلشی فعال‌اند ولی در منو نمایش داده نمی‌شوند."
        )
        await message.answer(text, reply_markup=_admin_keyboard())
        logger.info("start.handle_start: admin reply sent", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
    else:
        logger.info("start.handle_start: user branch", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
        text = (
            "👋 به MarzbanSudo خوش آمدید!\n\n"
            "از دکمه‌های زیر استفاده کنید: 🛒 خرید پلن، 📦 مشاهده سفارش‌ها و 👤 وضعیت اکانت."
        )
        await message.answer(text, reply_markup=_user_keyboard())
        logger.info("start.handle_start: user reply sent", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})


# Map non-slash buttons to existing handlers
@router.message(F.text.in_({"🛒 پلن‌ها", "🛒 خرید سرویس"}))
async def _btn_plans(message: Message) -> None:
    await plans_handler(message)


@router.message(F.text.in_({"📦 سفارش‌ها", "📦 سفارش‌های من"}))
async def _btn_orders(message: Message) -> None:
    logger.info("start.btn_orders", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
    await orders_handler(message)


@router.message(F.text.in_({"👤 اکانت", "👤 اکانت من"}))
async def _btn_account(message: Message) -> None:
    logger.info("start.btn_account", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
    await account_handler(message)


# Wallet buttons (normalized matching) → delegate to wallet handlers
@router.message(F.text == "💳 کیف پول")
@router.message(lambda m: text_matches(getattr(m, "text", None), "💳 کیف پول"))
async def _btn_wallet(message: Message) -> None:
    logger.info("start.btn.wallet", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
    await wallet_menu_handler(message)

@router.message(F.text == "💼 تنظیمات کیف پول")
@router.message(lambda m: text_matches(getattr(m, "text", None), "💼 تنظیمات کیف پول"))
async def _btn_admin_wallet_settings(message: Message) -> None:
    logger.info("start.btn.wallet_settings", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
    await wallet_settings_handler(message)

@router.message(F.text == "➕ شارژ دستی")
@router.message(lambda m: text_matches(getattr(m, "text", None), "➕ شارژ دستی"))
async def _btn_wallet_manual_add(message: Message) -> None:
    logger.info("start.btn.wallet_manual_add", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
    await wallet_manual_add_start(message)

@router.message(F.text == "💳 درخواست‌های شارژ")
@router.message(lambda m: text_matches(getattr(m, "text", None), "💳 درخواست‌های شارژ"))
async def _btn_admin_wallet_pending(message: Message) -> None:
    logger.info("start.btn.wallet_pending", extra={'extra': {'uid': getattr(getattr(message, 'from_user', None), 'id', None)}})
    await wallet_pending_handler(message)


@router.message(F.text == "⚙️ مدیریت پلن‌ها")
async def _btn_admin_plans_manage(message: Message) -> None:
    await admin_plans_menu_handler(message)


@router.message(F.text == "📦 سفارش‌های اخیر")
async def _btn_admin_recent_orders(message: Message) -> None:
    await admin_recent_handler(message)

@router.message(F.text == "🎟️ کدهای تخفیف")
async def _btn_admin_coupons_bridge(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    try:
        from app.bot.handlers import admin_coupons as _ac
        await _ac._admin_coupons_entry(message)  # type: ignore[attr-defined]
    except Exception:
        # اگر به هر دلیل فراخوانی مستقیم شکست خورد، پیغام راهنما نمایش داده می‌شود
        await message.answer("🎟️ مدیریت کدهای تخفیف")

# Admin Settings Hub

def _admin_settings_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💼 تنظیمات کیف پول")],
            [KeyboardButton(text="📱 تنظیمات احراز شماره")],
            [KeyboardButton(text="🧪 تنظیمات تست")],
            [KeyboardButton(text="💳 درخواست‌های شارژ")],
            [KeyboardButton(text="⚙️ مدیریت پلن‌ها")],
            [KeyboardButton(text="➕ شارژ دستی")],
            [KeyboardButton(text="📦 سفارش‌های اخیر")],
            [KeyboardButton(text="🎟️ کدهای تخفیف")],
            [KeyboardButton(text="👥 مدیریت کاربران")],
            [KeyboardButton(text="⬅️ بازگشت")],
        ], resize_keyboard=True
    )

@router.message(F.text == "⚙️ تنظیمات ربات")
async def _btn_admin_settings_hub(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    await message.answer("⚙️ تنظیمات ربات", reply_markup=_admin_settings_keyboard())

@router.message(F.text == "⬅️ بازگشت")
async def _btn_admin_settings_back(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    await message.answer("بازگشت به منوی اصلی ادمین", reply_markup=_admin_keyboard())

# Bridge: Admin manual-add flow — capture numeric tg_id/username in await_ref stage
@router.message(F.text.regexp(r"^(?:\d{5,}|[A-Za-z0-9_]{3,})$"), flags={"block": False})
async def _bridge_wallet_manual_add_ref(message: Message) -> None:
    if not message.from_user:
        return
    try:
        from app.utils.intent_store import get_intent_json
        payload = await get_intent_json(f"INTENT:WADM:{message.from_user.id}")
        if payload and payload.get("stage") == "await_ref":
            await wallet_manual_add_ref(message)
    except Exception:
        # fail-safe: do nothing
        pass

# Bridge: Wallet numeric routing — prioritize admin/manual and then user custom
@router.message(F.text.regexp(r"^[0-9\u06F0-\u06F9][0-9\u06F0-\u06F9,\.]{0,13}$"))
async def _bridge_wallet_numeric(message: Message) -> None:
    """Route numeric messages deterministically to the right wallet flow.
    Priority:
      1) Admin manual add amount (WADM stage=await_amount)
      2) Admin min/max intents (wallet limits numeric input)
      3) User custom top-up amount (TOPUP.amount == -1)
    """
    if not message.from_user:
        return
    uid = getattr(message.from_user, "id", None)
    if not uid:
        return

    # Entry log (best-effort)
    try:
        logger.info("start.bridge.numeric.enter", extra={"extra": {"uid": uid, "text": (message.text or "")[:64]}})
    except Exception:
        pass

    # 1) Admin manual add amount stage (short-circuit on success)
    # 1.a) In-memory flag check (strongest)
    try:
        from app.bot.handlers import wallet as _wmod
        st = (_wmod._WALLET_MANUAL_ADD_INTENT.get(uid, {}) or {}).get("stage")  # type: ignore[attr-defined]
        try:
            logger.info("start.bridge.numeric.mem", extra={"extra": {"uid": uid, "stage": st}})
        except Exception:
            pass
        if st == "await_amount":
            logger.info("start.bridge.numeric.path", extra={"extra": {"uid": uid, "path": "wadm-memory"}})
            await wallet_manual_add_amount_handler(message)
            return
    except Exception:
        pass
    # 1.b) DB-backed intent check
    try:
        from app.utils.intent_store import get_intent_json as _get_intent
        wadm = await _get_intent(f"INTENT:WADM:{uid}")
        try:
            _st = str(wadm.get("stage") if wadm else "")
            _un = str(wadm.get("unit") if wadm else "")
            logger.info("start.bridge.numeric.db", extra={"extra": {"uid": uid, "stage": _st, "unit": _un}})
        except Exception:
            pass
        if wadm and wadm.get("stage") == "await_amount":
            logger.info("start.bridge.numeric.path", extra={"extra": {"uid": uid, "path": "wadm-db"}})
            await wallet_manual_add_amount_handler(message)
            return
    except Exception:
        pass

    # 1.d) Heuristic: if WADM has a valid unit (TMN/IRR), treat numeric text as amount
    try:
        from app.utils.intent_store import get_intent_json as _get_intent
        _wadm_h = await _get_intent(f"INTENT:WADM:{uid}")
        _unit = str(_wadm_h.get("unit") if _wadm_h else "")
        if _unit in {"TMN", "IRR"}:
            logger.info("start.bridge.numeric.path", extra={"extra": {"uid": uid, "path": "wadm-heuristic"}})
            await wallet_manual_add_amount_handler(message)
            return
    except Exception:
        pass

    # 1.c) Admin limits in-memory flags (optional fast-path)
    try:
        from app.bot.handlers import wallet as _wmod
        if _wmod._WALLET_ADMIN_MIN_INTENT.get(uid, False) or _wmod._WALLET_ADMIN_MAX_INTENT.get(uid, False):  # type: ignore[attr-defined]
            logger.info("start.bridge.numeric.path", extra={"extra": {"uid": uid, "path": "limits-memory"}})
            await wallet_limits_numeric_input_handler(message)
    except Exception:
        pass

    # 2) Admin limits (min/max). Do not block other flows on errors
    try:
        logger.info("start.bridge.numeric.path", extra={"extra": {"uid": uid, "path": "limits"}})
        await wallet_limits_numeric_input_handler(message)
    except Exception:
        pass

    # 3) User custom amount (only when active). Independent of limits outcome
    try:
        from app.utils.intent_store import get_intent_json as _get_intent
        topup = await _get_intent(f"INTENT:TOPUP:{uid}")
        if topup and str(topup.get("amount")) == "-1":
            logger.info("start.bridge.numeric.path", extra={"extra": {"uid": uid, "path": "custom"}})
            await wallet_custom_amount_handler(message)
    except Exception:
        pass


# Fallback bridge: any text containing digits; non-blocking so other handlers can still proceed if needed
@router.message(F.text.regexp(r".*[0-9\u06F0-\u06F9].*"), flags={"block": False})
async def _bridge_wallet_numeric_fallback(message: Message) -> None:
    try:
        await _bridge_wallet_numeric(message)
    except Exception:
        # never break pipeline due to bridge
        pass

@router.callback_query(F.data == "chk:chan")
async def cb_check_channel(cb: CallbackQuery) -> None:
    channel = os.getenv("REQUIRED_CHANNEL", "").strip()
    if not channel or not cb.from_user:
        await cb.answer()
        return
    try:
        member = await cb.message.bot.get_chat_member(chat_id=channel, user_id=cb.from_user.id)
        status = getattr(member, "status", None)
        if status in {"member", "creator", "administrator"}:
            await cb.message.answer("✅ عضویت شما تایید شد.", reply_markup=_user_keyboard())
            await cb.answer("عضو شدید")
            return
    except Exception:
        await cb.answer("امکان بررسی عضویت نیست. ربات باید ادمین کانال باشد.", show_alert=True)
        return
    await cb.answer("هنوز عضو کانال نیستید.", show_alert=True)


async def _get_pv_enabled() -> bool:
    # Read from settings; fallback to ENV
    val_env = os.getenv("PHONE_VERIFICATION_ENABLED", "0").strip()
    try:
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "PHONE_VERIFICATION_ENABLED"))
            if row:
                return str(row.value).strip() in {"1", "true", "True"}
    except Exception:
        pass
    return val_env in {"1", "true", "True"}


@router.message(F.text == "📱 تنظیمات احراز شماره")
async def admin_phone_verify_menu(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("⛔️ شما دسترسی ادمین ندارید.")
        return
    enabled = await _get_pv_enabled()
    status = "فعال" if enabled else "غیرفعال"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="فعال کردن ✅", callback_data="pv:on"), InlineKeyboardButton(text="غیرفعال کردن ❌", callback_data="pv:off")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="pv:refresh")],
    ])
    await message.answer(f"📱 احراز شماره تلفن: {status}\nاگر فعال باشد، قبل از خرید شماره تلگرام کاربر درخواست می‌شود.", reply_markup=kb)


@router.callback_query(F.data.in_({"pv:on", "pv:off", "pv:refresh"}))
async def cb_admin_pv_toggle(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    if cb.data in {"pv:on", "pv:off"}:
        val = "1" if cb.data == "pv:on" else "0"
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "PHONE_VERIFICATION_ENABLED"))
            if not row:
                row = Setting(key="PHONE_VERIFICATION_ENABLED", value=val)
                session.add(row)
            else:
                row.value = val
            await session.commit()
        await cb.answer("✅ ذخیره شد")
    # Refresh view
    enabled = await _get_pv_enabled()
    status = "فعال" if enabled else "غیرفعال"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="فعال کردن ✅", callback_data="pv:on"), InlineKeyboardButton(text="غیرفعال کردن ❌", callback_data="pv:off")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="pv:refresh")],
    ])
    try:
        await cb.message.edit_text(f"📱 احراز شماره تلفن: {status}\nاگر فعال باشد، قبل از خرید شماره تلگرام کاربر درخواست می‌شود.", reply_markup=kb)
    except Exception:
        await cb.message.answer(f"📱 احراز شماره تلفن: {status}", reply_markup=kb)
    await cb.answer()


@router.message(F.contact)
async def handle_contact_share(message: Message) -> None:
    if not message.from_user or not message.contact:
        return
    # Ensure user shares own number
    if message.contact.user_id != message.from_user.id:
        await message.answer("لطفاً شماره همین حساب تلگرام را ارسال کنید.")
        return
    phone = message.contact.phone_number
    from datetime import datetime
    async with session_scope() as session:
        row_p = await session.scalar(select(Setting).where(Setting.key == f"USER:{message.from_user.id}:PHONE"))
        if not row_p:
            session.add(Setting(key=f"USER:{message.from_user.id}:PHONE", value=phone))
        else:
            row_p.value = phone
        row_t = await session.scalar(select(Setting).where(Setting.key == f"USER:{message.from_user.id}:PHONE_VERIFIED_AT"))
        now_iso = datetime.utcnow().isoformat()
        if not row_t:
            session.add(Setting(key=f"USER:{message.from_user.id}:PHONE_VERIFIED_AT", value=now_iso))
        else:
            row_t.value = now_iso
        await session.commit()
    await message.answer("✅ شماره شما با موفقیت تایید شد. اکنون می‌توانید خرید را ادامه دهید.", reply_markup=_user_keyboard())


# Bridge: also handle trial request text here to avoid any filter mismatch
@router.message(F.text.in_({"🧪 دریافت تست", "دریافت تست", "دريافت تست"}))
async def _btn_request_trial(message: Message) -> None:
    try:
        from app.bot.handlers.trial import handle_trial as _handle_trial
        await _handle_trial(message)
    except Exception:
        try:
            await message.answer("/trial")
        except Exception:
            pass