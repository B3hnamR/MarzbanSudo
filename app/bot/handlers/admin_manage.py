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


@router.message(Command("admin_get"))
async def admin_get(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("فرمت: /admin_get <username>")
        return
    username = parts[1].strip()
    try:
        info = await ops.get_user_summary(username)
        await message.answer(info["summary_text"])
        if info.get("subscription_url"):
            await message.answer(info["subscription_url"])
    except Exception as e:
        await message.answer(f"خطا در admin_get: {e}")


@router.message(Command("admin_status"))
async def admin_status(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("فرمت: /admin_status <username> <active|disabled|on_hold>")
        return
    username = parts[1].strip()
    status = parts[2].strip()
    try:
        await ops.set_status(username, status)
        await message.answer("اعمال شد.")
    except Exception as e:
        await message.answer(f"خطا در admin_status: {e}")


@router.message(Command("admin_addgb"))
async def admin_addgb(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("فرمت: /admin_addgb <username> <GB>")
        return
    username = parts[1].strip()
    try:
        gb = float(parts[2])
    except ValueError:
        await message.answer("مقدار GB نامعتبر است.")
        return
    try:
        await ops.add_data_gb(username, gb)
        await message.answer("اعمال شد.")
    except Exception as e:
        await message.answer(f"خطا در admin_addgb: {e}")


@router.message(Command("admin_extend"))
async def admin_extend(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("فرمت: /admin_extend <username> <DAYS>")
        return
    username = parts[1].strip()
    try:
        days = int(parts[2])
    except ValueError:
        await message.answer("مقدار DAYS نامعتبر است.")
        return
    try:
        await ops.extend_expire(username, days)
        await message.answer("اعمال شد.")
    except Exception as e:
        await message.answer(f"خطا در admin_extend: {e}")


@router.message(Command("admin_list_expired"))
async def admin_list_expired(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        rows = await ops.list_expired()
        if not rows:
            await message.answer("موردی یافت نشد.")
            return
        lines = []
        for r in rows[:20]:
            lines.append(f"- {r.get('username')} | status={r.get('status')} | expire={r.get('expire')}")
        await message.answer("Expired users (first 20):\n" + "\n".join(lines))
    except Exception as e:
        await message.answer(f"خطا در admin_list_expired: {e}")


@router.message(Command("admin_delete_expired"))
async def admin_delete_expired(message: Message) -> None:
    if not _require_admin(message):
        await message.answer("شما دسترسی ادمین ندارید.")
        return
    try:
        res = await ops.delete_expired()
        await message.answer(f"Deleted expired: {res}")
    except Exception as e:
        await message.answer(f"خطا در admin_delete_expired: {e}")
