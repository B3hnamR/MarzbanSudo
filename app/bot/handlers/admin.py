from __future__ import annotations

import os
from typing import List

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


def _get_admin_ids() -> List[int]:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "").strip()
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            pass
    return ids


@router.message(Command("admin"))
async def handle_admin(message: Message) -> None:
    admin_ids = _get_admin_ids()
    if message.from_user and message.from_user.id in admin_ids:
        await message.answer("پنل ادمین: به‌زودی دستورهای مدیریتی فعال می‌شوند.")
    else:
        await message.answer("شما دسترسی ادمین ندارید.")
