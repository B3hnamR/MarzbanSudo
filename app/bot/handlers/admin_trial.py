from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Setting
from app.services.security import has_capability_async, CAP_WALLET_MODERATE
from app.utils.intent_store import set_intent_json, get_intent_json, clear_intent


router = Router()


def _bool_str(val: bool) -> str:
    return "بله" if val else "خیر"


async def _load_trial_config() -> tuple[bool, int, int, bool]:
    """Return (enabled, data_gb, duration_days, one_per_user) with DB override and ENV fallback."""
    enabled = (os.getenv("TRIAL_ENABLED", "0").strip() in {"1", "true", "True"})
    data_gb = int(os.getenv("TRIAL_DATA_GB", "2") or "2")
    duration_days = int(os.getenv("TRIAL_DURATION_DAYS", "1") or "1")
    one_per_user = False
    try:
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_ENABLED"))
            if row:
                enabled = str(row.value).strip() in {"1", "true", "True"}
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_DATA_GB"))
            if row:
                try:
                    data_gb = int(str(row.value).strip())
                except Exception:
                    pass
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_DURATION_DAYS"))
            if row:
                try:
                    duration_days = int(str(row.value).strip())
                except Exception:
                    pass
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_ONE_PER_USER"))
            if row:
                one_per_user = str(row.value).strip() in {"1", "true", "True"}
    except Exception:
        pass
    return enabled, data_gb, duration_days, one_per_user


def _kb(enabled: bool, one_per_user: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=("🟢 روشن" if not enabled else "🔴 خاموش"), callback_data=("trial:on" if not enabled else "trial:off")),
            InlineKeyboardButton(text=("🔁 یک‌بار برای هر کاربر: روشن" if not one_per_user else "🔁 یک‌بار: خاموش"), callback_data=("trial:one:on" if not one_per_user else "trial:one:off")),
        ],
        [
            InlineKeyboardButton(text="📦 تنظیم حجم (GB)", callback_data="trial:set:gb"),
            InlineKeyboardButton(text="⏳ تنظیم مدت (روز)", callback_data="trial:set:days"),
        ],
        [
            InlineKeyboardButton(text="🧹 بازنشانی وضعیت کاربر", callback_data="trial:reset:ask"),
            InlineKeyboardButton(text="🔄 به‌روزرسانی", callback_data="trial:refresh"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("admin_trial"))
async def admin_trial_menu(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("⛔️ دسترسی ندارید.")
        return
    enabled, data_gb, duration_days, one_per_user = await _load_trial_config()
    txt = (
        "🧪 تنظیمات دوره آزمایشی\n\n"
        f"• وضعیت: {'روشن ✅' if enabled else 'خاموش ⛔️'}\n"
        f"• حجم: {data_gb} گیگابایت\n"
        f"• مدت: {duration_days} روز\n"
        f"• یک‌بار برای هر کاربر: {_bool_str(one_per_user)}\n"
    )
    await message.answer(txt, reply_markup=_kb(enabled, one_per_user))


@router.callback_query(F.data.in_({"trial:on", "trial:off", "trial:one:on", "trial:one:off", "trial:refresh"}))
async def cb_trial_toggle_refresh(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("⛔️")
        return
    if cb.data in {"trial:on", "trial:off", "trial:one:on", "trial:one:off"}:
        key = "TRIAL_ENABLED" if cb.data.startswith("trial:") and (cb.data in {"trial:on", "trial:off"}) else "TRIAL_ONE_PER_USER"
        val = "1" if cb.data.endswith(":on") else "0"
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == key))
            if not row:
                session.add(Setting(key=key, value=val))
            else:
                row.value = val
            await session.commit()
        await cb.answer("ذخیره شد ✅")
    # Refresh view
    enabled, data_gb, duration_days, one_per_user = await _load_trial_config()
    txt = (
        "🧪 تنظیمات دوره آزمایشی\n\n"
        f"• وضعیت: {'روشن ✅' if enabled else 'خاموش ⛔️'}\n"
        f"• حجم: {data_gb} گیگابایت\n"
        f"• مدت: {duration_days} روز\n"
        f"• یک‌بار برای هر کاربر: {_bool_str(one_per_user)}\n"
    )
    try:
        await cb.message.edit_text(txt, reply_markup=_kb(enabled, one_per_user))
    except Exception:
        await cb.message.answer(txt, reply_markup=_kb(enabled, one_per_user))
    await cb.answer()


@router.callback_query(F.data == "trial:set:gb")
async def cb_trial_set_gb(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("⛔️")
        return
    await set_intent_json(f"INTENT:TRIAL:SET:GB:{cb.from_user.id}", {"stage": "await_gb"})
    await cb.message.answer("📦 حجم آزمایشی (GB) را ارسال کنید (مثلاً: 2)")
    await cb.answer()


@router.callback_query(F.data == "trial:set:days")
async def cb_trial_set_days(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("⛔️")
        return
    await set_intent_json(f"INTENT:TRIAL:SET:DAYS:{cb.from_user.id}", {"stage": "await_days"})
    await cb.message.answer("⏳ مدت آزمایشی (روز) را ارسال کنید (مثلاً: 1)")
    await cb.answer()


@router.callback_query(F.data == "trial:reset:ask")
async def cb_trial_reset_ask(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("⛔️")
        return
    await set_intent_json(f"INTENT:TRIAL:RESET:{cb.from_user.id}", {"stage": "await_tg"})
    await cb.message.answer("🧹 شناسه تلگرام کاربر را ارسال کنید تا وضعیت آزمایشی او بازنشانی شود.")
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and isinstance(getattr(m, "text", None), str))
async def msg_trial_admin_capture(message: Message) -> None:
    uid = message.from_user.id
    payload = await get_intent_json(f"INTENT:TRIAL:SET:GB:{uid}")
    if payload and payload.get("stage") == "await_gb":
        txt = (message.text or "").strip()
        try:
            gb = int(txt)
            if gb < 0 or gb > 500:
                raise ValueError
        except Exception:
            await message.answer("❌ مقدار نامعتبر. یک عدد صحیح بین 0 تا 500 ارسال کنید.")
            return
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_DATA_GB"))
            if not row:
                session.add(Setting(key="TRIAL_DATA_GB", value=str(gb)))
            else:
                row.value = str(gb)
            await session.commit()
        await clear_intent(f"INTENT:TRIAL:SET:GB:{uid}")
        await message.answer("✅ حجم آزمایشی ذخیره شد.")
        return

    payload = await get_intent_json(f"INTENT:TRIAL:SET:DAYS:{uid}")
    if payload and payload.get("stage") == "await_days":
        txt = (message.text or "").strip()
        try:
            days = int(txt)
            if days < 0 or days > 365:
                raise ValueError
        except Exception:
            await message.answer("❌ مقدار نامعتبر. یک عدد صحیح بین 0 تا 365 ارسال کنید.")
            return
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_DURATION_DAYS"))
            if not row:
                session.add(Setting(key="TRIAL_DURATION_DAYS", value=str(days)))
            else:
                row.value = str(days)
            await session.commit()
        await clear_intent(f"INTENT:TRIAL:SET:DAYS:{uid}")
        await message.answer("✅ مدت آزمایشی ذخیره شد.")
        return

    payload = await get_intent_json(f"INTENT:TRIAL:RESET:{uid}")
    if payload and payload.get("stage") == "await_tg":
        txt = (message.text or "").strip()
        if not txt.isdigit():
            await message.answer("❌ فقط شناسه عددی تلگرام را ارسال کنید.")
            return
        tg_id = int(txt)
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == f"USER:{tg_id}:TRIAL_USED_AT"))
            if row:
                await session.delete(row)
                await session.commit()
                await message.answer("🧹 وضعیت آزمایشی کاربر بازنشانی شد.")
            else:
                await message.answer("ℹ️ برای این کاربر وضعیت استفاده ثبت نشده بود.")
        await clear_intent(f"INTENT:TRIAL:RESET:{uid}")
        return

