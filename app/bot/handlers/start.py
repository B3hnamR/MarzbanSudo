from __future__ import annotations

import os
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# Import existing handlers to reuse their logic without showing slash commands
from app.bot.handlers.plans import handle_plans as plans_handler
from app.bot.handlers.orders import handle_orders as orders_handler
from app.bot.handlers.account import handle_account as account_handler
from app.bot.handlers.admin_orders import admin_orders_pending as admin_pending_handler
from app.bot.handlers.admin_manage import admin_show_plans_menu as admin_plans_menu_handler
from app.bot.handlers.wallet import wallet_menu as wallet_menu_handler, admin_wallet_pending_topups as wallet_pending_handler

router = Router()


def _admin_ids() -> set[int]:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "").strip()
    ids: set[int] = set()
    for x in raw.split(","):
        x = x.strip()
        if x.isdigit():
            ids.add(int(x))
    return ids


def _is_admin(msg: Message) -> bool:
    return bool(msg.from_user and msg.from_user.id in _admin_ids())


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
            [KeyboardButton(text="🛒 پلن‌ها"), KeyboardButton(text="📦 سفارش‌ها")],
            [KeyboardButton(text="👤 اکانت"), KeyboardButton(text="💳 کیف پول")],
            [KeyboardButton(text="💳 درخواست‌های شارژ"), KeyboardButton(text="💼 تنظیمات کیف پول")],
            [KeyboardButton(text="⚙️ مدیریت پلن‌ها")],
        ], resize_keyboard=True
    )


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if _is_admin(message):
        text = (
            "به MarzbanSudo خوش آمدید، ادمین عزیز!\n\n"
            "از دکمه‌ها برای مدیریت استفاده کنید. دستورات اسلشی فعال‌اند ولی در منو نمایش داده نمی‌شوند."
        )
        await message.answer(text, reply_markup=_admin_keyboard())
    else:
        text = (
            "به MarzbanSudo خوش آمدید!\n\n"
            "از دکمه‌های زیر استفاده کنید: خرید پلن، مشاهده سفارش‌ها و وضعیت اکانت."
        )
        await message.answer(text, reply_markup=_user_keyboard())


# Map non-slash buttons to existing handlers
@router.message(F.text == "🛒 پلن‌ها")
async def _btn_plans(message: Message) -> None:
    await plans_handler(message)


@router.message(F.text == "📦 سفارش‌ها")
async def _btn_orders(message: Message) -> None:
    await orders_handler(message)


@router.message(F.text == "👤 اکانت")
async def _btn_account(message: Message) -> None:
    await account_handler(message)


@router.message(F.text == "💳 کیف پول")
async def _btn_wallet(message: Message) -> None:
    await wallet_menu_handler(message)


@router.message(F.text == "💳 درخواست‌های شارژ")
async def _btn_admin_wallet_pending(message: Message) -> None:
    # wallet_pending_handler has its own admin check
    await wallet_pending_handler(message)


@router.message(F.text == "⚙️ مدیریت پلن‌ها")
async def _btn_admin_plans_manage(message: Message) -> None:
    await admin_plans_menu_handler(message)
