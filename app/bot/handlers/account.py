from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("account"))
async def handle_account(message: Message) -> None:
    # Placeholder: در فاز بعدی از DB + sub4me/info تغذیه می‌شود
    await message.answer("اطلاعات اکانت شما به‌زودی در دسترس خواهد بود.")
