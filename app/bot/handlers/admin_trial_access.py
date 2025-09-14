from __future__ import annotations

import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Setting
from app.services.security import has_capability_async, CAP_WALLET_MODERATE
from app.utils.intent_store import set_intent_json, get_intent_json, clear_intent


router = Router()


async def _load_access_mode() -> str:
    mode = "public"
    try:
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_ACCESS_MODE"))
            if row:
                val = str(row.value).strip().lower()
                if val in {"public", "whitelist"}:
                    mode = val
    except Exception:
        pass
    return mode


def _kb_access(mode: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=("🔐 حالت دسترسی: عمومی" if mode == "public" else "🔐 حالت دسترسی: فقط فهرست مجاز"), callback_data=("trialacc:public" if mode != "public" else "trialacc:white")),
            InlineKeyboardButton(text="🔄 به‌روزرسانی", callback_data="trialacc:refresh"),
        ],
        [
            InlineKeyboardButton(text="➕ افزودن به فهرست مجاز", callback_data="trialacc:allow:add"),
            InlineKeyboardButton(text="➖ حذف از فهرست مجاز", callback_data="trialacc:allow:del"),
        ],
        [
            InlineKeyboardButton(text="🚫 مسدودکردن کاربر", callback_data="trialacc:block:add"),
            InlineKeyboardButton(text="✅ رفع مسدودی کاربر", callback_data="trialacc:block:del"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("admin_trial_access"))
@router.message(F.text == "دسترسی تست")
@router.message(lambda m: getattr(m, "from_user", None) and isinstance(getattr(m, "text", None), str) and ("دسترسی" in (m.text or "") and "تست" in (m.text or "")))
async def admin_trial_access_menu(message: Message) -> None:
    if not (message.from_user and await has_capability_async(message.from_user.id, CAP_WALLET_MODERATE)):
        await message.answer("⛔️ دسترسی ندارید.")
        return
    mode = await _load_access_mode()
    txt = (
        "🧪 دسترسی دریافت دوره آزمایشی\n\n"
        f"• حالت دسترسی: {'عمومی' if mode == 'public' else 'فقط فهرست مجاز'}\n"
        "• می‌توانید کاربران را به فهرست مجاز اضافه/حذف کنید یا مسدود/رفع مسدود نمایید.\n"
    )
    await message.answer(txt, reply_markup=_kb_access(mode))


@router.message(F.text == "دسترسی تست")
async def _btn_admin_trial_access_menu(message: Message) -> None:
    await admin_trial_access_menu(message)


@router.callback_query(F.data.startswith("trialacc:"))
async def cb_trial_access(cb: CallbackQuery) -> None:
    if not (cb.from_user and await has_capability_async(cb.from_user.id, CAP_WALLET_MODERATE)):
        await cb.answer("⛔️")
        return
    data = cb.data or ""
    if data in {"trialacc:public", "trialacc:white"}:
        mode = "public" if data.endswith(":public") else "whitelist"
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_ACCESS_MODE"))
            if not row:
                session.add(Setting(key="TRIAL_ACCESS_MODE", value=mode))
            else:
                row.value = mode
            await session.commit()
        await cb.answer("ذخیره شد ✅")
    elif data in {"trialacc:allow:add", "trialacc:allow:del", "trialacc:block:add", "trialacc:block:del"}:
        intent = data.split(":")[1] + ":" + data.split(":")[2]
        await set_intent_json(f"INTENT:TRIALACC:{intent}:{cb.from_user.id}", {"stage": "await_ids"})
        await cb.message.answer("شناسه(های) عددی تلگرام را با کاما یا فاصله ارسال کنید.")
        await cb.answer()
        return
    # refresh
    mode = await _load_access_mode()
    txt = (
        "🧪 دسترسی دریافت دوره آزمایشی\n\n"
        f"• حالت دسترسی: {'عمومی' if mode == 'public' else 'فقط فهرست مجاز'}\n"
        "• می‌توانید کاربران را به فهرست مجاز اضافه/حذف کنید یا مسدود/رفع مسدود نمایید.\n"
    )
    try:
        await cb.message.edit_text(txt, reply_markup=_kb_access(mode))
    except Exception:
        await cb.message.answer(txt, reply_markup=_kb_access(mode))
    await cb.answer()


@router.message(lambda m: getattr(m, "from_user", None) and isinstance(getattr(m, "text", None), str))
async def msg_trial_access_ops(message: Message) -> None:
    uid = message.from_user.id
    # determine which intent is set
    for key, setting_key_tmpl in (
        (f"INTENT:TRIALACC:allow:add:{uid}", "USER:{id}:TRIAL_ALLOWED"),
        (f"INTENT:TRIALACC:allow:del:{uid}", "USER:{id}:TRIAL_ALLOWED"),
        (f"INTENT:TRIALACC:block:add:{uid}", "USER:{id}:TRIAL_DISABLED"),
        (f"INTENT:TRIALACC:block:del:{uid}", "USER:{id}:TRIAL_DISABLED"),
    ):
        payload = await get_intent_json(key)
        if payload and payload.get("stage") == "await_ids":
            raw = (message.text or "").replace("\n", " ").replace(",", " ")
            ids = [p for p in raw.split() if p.strip().isdigit()]
            if not ids:
                await message.answer("❌ لطفاً فقط شناسه‌های عددی معتبر ارسال کنید.")
                return
            async with session_scope() as session:
                if key.endswith(":allow:add"):
                    for sid in ids:
                        skey = setting_key_tmpl.format(id=int(sid))
                        row = await session.scalar(select(Setting).where(Setting.key == skey))
                        if not row:
                            session.add(Setting(key=skey, value="1"))
                        else:
                            row.value = "1"
                elif key.endswith(":allow:del"):
                    for sid in ids:
                        skey = setting_key_tmpl.format(id=int(sid))
                        row = await session.scalar(select(Setting).where(Setting.key == skey))
                        if row:
                            await session.delete(row)
                elif key.endswith(":block:add"):
                    for sid in ids:
                        skey = setting_key_tmpl.format(id=int(sid))
                        row = await session.scalar(select(Setting).where(Setting.key == skey))
                        if not row:
                            session.add(Setting(key=skey, value="1"))
                        else:
                            row.value = "1"
                elif key.endswith(":block:del"):
                    for sid in ids:
                        skey = setting_key_tmpl.format(id=int(sid))
                        row = await session.scalar(select(Setting).where(Setting.key == skey))
                        if row:
                            await session.delete(row)
                await session.commit()
            await clear_intent(key)
            await message.answer("✅ اعمال شد.")
            return
