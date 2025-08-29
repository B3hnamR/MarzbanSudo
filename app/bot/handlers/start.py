from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    text = (
        "به MarzbanSudo خوش آمدید!\n\n"
        "از دکمه‌های زیر استفاده کنید یا دستورات را بنویسید:\n"
        "/plans — پلن‌ها\n"
        "/orders — سفارش‌ها\n"
        "/account — اکانت\n"
    )
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/plans"), KeyboardButton(text="/orders")],
            [KeyboardButton(text="/account")],
        ], resize_keyboard=True
    )
    await message.answer(text, reply_markup=kb)
