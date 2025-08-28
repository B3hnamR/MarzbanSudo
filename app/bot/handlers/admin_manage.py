from __future__ import annotations

import os
from typing import List

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.utils.username import tg_username
from app.services import marzban_ops as ops

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


def _require_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in _get_admin_ids())


@router.message(Command("admin_create"))
async def admin_create(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دستر��ی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    username = parts[1].strip() if len(parts) == 2 else tg_username(message.from_user.id)  # default to caller
    await message.answer(f"در حال ایجاد کاربر {username}...")
    try:
        data = await ops.create_user_minimal(username, note="admin:create")
        await message.answer(f"ایجاد شد: {username}")
    except Exception as e:
        await message.answer(f"خطا در ایجاد: {e}")


@router.message(Command("admin_delete"))
async def admin_delete(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("فرمت: /admin_delete <username>")
        return
    username = parts[1].strip()
    await message.answer(f"حذف کاربر {username}...")
    try:
        await ops.delete_user(username)
        await message.answer("حذف شد.")
    except Exception as e:
        await message.answer(f"خطا در حذف: {e}")


@router.message(Command("admin_reset"))
async def admin_reset(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("فرمت: /admin_reset <username>")
        return
    username = parts[1].strip()
    try:
        await ops.reset_user(username)
        await message.answer("reset انجام شد.")
    except Exception as e:
        await message.answer(f"خطا در reset: {e}")


@router.message(Command("admin_revoke"))
async def admin_revoke(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("فرمت: /admin_revoke <username>")
        return
    username = parts[1].strip()
    try:
        await ops.revoke_sub(username)
        await message.answer("revoke_sub انجام شد.")
    except Exception as e:
        await message.answer(f"خطا در revoke: {e}")


@router.message(Command("admin_set"))
async def admin_set(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    # Format: /admin_set <username> <gb> <days>
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("فرمت: /admin_set <username> <GB> <DAYS>")
        return
    username = parts[1].strip()
    try:
        gb = float(parts[2])
        days = int(parts[3])
    except ValueError:
        await message.answer("مقادیر GB و DAYS نامعتبر است.")
        return
    await message.answer(f"تنظیم محدودیت برای {username}: {gb}GB / {days}d ...")
    try:
        data = await ops.update_user_limits(username, gb, days)
        await message.answer("اعمال شد.")
    except Exception as e:
        await message.answer(f"خطا در admin_set: {e}")
