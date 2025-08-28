from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    text = (
        "به MarzbanSudo خوش آمدید!\n\n"
        "- با دستور /plans پلن‌ها را ببینید.\n"
        "- با دستور /orders سفارش‌های خود را مدیریت کنید.\n"
        "- با دستور /account وضعیت اکانت و لینک‌ها را ببینید.\n"
    )
    await message.answer(text)
