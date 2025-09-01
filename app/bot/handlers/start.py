from __future__ import annotations

import os
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.db.session import session_scope
from app.db.models import Setting, User
from app.services.security import has_capability_async, CAP_WALLET_MODERATE, is_admin_uid
from sqlalchemy import select
from app.utils.username import tg_username

# Import existing handlers to reuse their logic without showing slash commands
from app.bot.handlers.plans import handle_plans as plans_handler
from app.bot.handlers.orders import handle_orders as orders_handler
from app.bot.handlers.account import handle_account as account_handler
from app.bot.handlers.admin_orders import admin_orders_pending as admin_pending_handler, admin_orders_recent as admin_recent_handler
from app.bot.handlers.admin_manage import admin_show_plans_menu as admin_plans_menu_handler
from app.bot.handlers.wallet import wallet_menu as wallet_menu_handler, admin_wallet_pending_topups as wallet_pending_handler, admin_wallet_manual_add_start as wallet_manual_add_start

router = Router()


def _is_admin(msg: Message) -> bool:
    return bool(msg.from_user and is_admin_uid(msg.from_user.id))


def _user_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 پلن‌ها"), KeyboardButton(text="📦 سفارش‌ها")],
            [KeyboardButton(text="👤 اکانت"), KeyboardButton(text="💳 کیف پول")],
        ], resize_keyboard=True
    )


def _admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 پلن‌ها"), KeyboardButton(text="📦 سفارش‌های من")],
            [KeyboardButton(text="👤 اکانت"), KeyboardButton(text="💳 کیف پول")],
            [KeyboardButton(text="💳 درخواست‌های شارژ"), KeyboardButton(text="💼 تنظیمات کیف پول")],
            [KeyboardButton(text="⚙️ مدیریت پلن‌ها"), KeyboardButton(text="📦 سفارش‌های اخیر")],
            [KeyboardButton(text="👥 مدیریت کاربران"), KeyboardButton(text="📱 تنظیمات احراز شماره")],
            [KeyboardButton(text="➕ شارژ دستی")],
        ], resize_keyboard=True
    )


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
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
    except Exception:
        pass

    if _is_admin(message):
        text = (
            "به MarzbanSudo خوش آمدید، ادمین عزیز!\n\n"
            "از دکمه‌ها برای مدیریت استفاده کنید. دستورات اسلشی فعال‌اند ولی در منو نمایش داده نمی‌شوند."
        )
        await message.answer(text, reply_markup=_admin_keyboard())
    else:
        # Channel membership gate (if required)
        channel = os.getenv("REQUIRED_CHANNEL", "").strip()
        if channel and message.from_user:
            try:
                member = await message.bot.get_chat_member(chat_id=channel, user_id=message.from_user.id)
                status = getattr(member, "status", None)
                if status not in {"member", "creator", "administrator"}:
                    join_url = f"https://t.me/{channel.lstrip('@')}"
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📢 عضویت در کانال", url=join_url)],
                        [InlineKeyboardButton(text="من عضو شدم ���", callback_data="chk:chan")],
                    ])
                    txt = (
                        "برای استفاده از ربات، ابتدا در کانال عضو شوید.\n"
                        "پس از عضویت، روی دکمه \"من عضو شدم ✅\" بزنید."
                    )
                    await message.answer(txt, reply_markup=kb)
                    return
            except Exception:
                # If check fails, proceed without gate
                pass
        text = (
            "به MarzbanSudo خوش آمدید!\n\n"
            "از دکمه‌های زیر استفاده کنید: خرید پلن، مشاهده سفارش‌ها و وضعیت اکانت."
        )
        await message.answer(text, reply_markup=_user_keyboard())


# Map non-slash buttons to existing handlers
@router.message(F.text == "🛒 پلن‌ها")
async def _btn_plans(message: Message) -> None:
    await plans_handler(message)


@router.message(F.text.in_({"📦 سفارش‌ها", "📦 سفارش‌های من"}))
async def _btn_orders(message: Message) -> None:
    await orders_handler(message)


@router.message(F.text == "👤 اکانت")
async def _btn_account(message: Message) -> None:
    await account_handler(message)


@router.message(F.text == "💳 کیف پول")
async def _btn_wallet(message: Message) -> None:
    await wallet_menu_handler(message)


@router.message(F.text == "➕ شارژ دستی")
async def _btn_wallet_manual_add(message: Message) -> None:
    await wallet_manual_add_start(message)


@router.message(F.text == "💳 درخواست‌های شارژ")
async def _btn_admin_wallet_pending(message: Message) -> None:
    # wallet_pending_handler has its own admin check
    await wallet_pending_handler(message)


@router.message(F.text == "⚙️ مدیریت پلن‌ها")
async def _btn_admin_plans_manage(message: Message) -> None:
    await admin_plans_menu_handler(message)


@router.message(F.text == "📦 سفارش‌های اخیر")
async def _btn_admin_recent_orders(message: Message) -> None:
    await admin_recent_handler(message)


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
        pass
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
        await message.answer("شما دسترسی ادمین ندارید.")
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
        await cb.answer("شما دسترسی ادمین ندارید.", show_alert=True)
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
        await cb.answer("ذخیره شد")
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
