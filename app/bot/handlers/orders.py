from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("orders"))
async def handle_orders(message: Message) -> None:
    # Placeholder: در فاز بعدی جریان سفارش (ایجاد، مشاهده، تمدید، افزایش حجم) پیاده می‌شود
    await message.answer(
        "سفارش‌ها: به‌زودی امکان مشاهده و ایجاد سفارش (خرید/تمدید/افزایش حجم) فعال خواهد شد."
    )
