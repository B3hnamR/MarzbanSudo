گکگfrom __future__ import annotations

import logging
from typing import List

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Plan
from app.scripts.sync_plans import sync_templates_to_plans


router = Router()


@router.message(Command("plans"))
async def handle_plans(message: Message) -> None:
    await message.answer("در حال دریافت پلن‌ها...")
    try:
        async with session_scope() as session:
            rows = (await session.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.template_id))).scalars().all()
            if not rows:
                await message.answer("هیچ پلنی در پایگاه‌داده ثبت نشده است. در حال همگام‌سازی از Marzban...")
                changed = await sync_templates_to_plans(session)
                if not changed:
                    await message.answer("همگام‌سازی انجام شد اما پلنی یافت نشد. لطفاً در Marzban حداقل یک Template فعال ایجاد کنید.")
                    return
                # Re-query after sync
                rows = (await session.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.template_id))).scalars().all()
                if not rows:
                    await message.answer("پس از همگام‌سازی هم پلنی یافت نشد. تنظیمات Marzban و دسترسی‌ها را بررسی کنید.")
                    return
            lines: List[str] = []
            for p in rows:
                if p.data_limit_bytes and p.data_limit_bytes > 0:
                    gb = p.data_limit_bytes / (1024 ** 3)
                    limit_str = f"{gb:.0f}GB"
                else:
                    limit_str = "نامحدود"
                dur_str = f"{p.duration_days}d" if p.duration_days and p.duration_days > 0 else "بدون محدودیت زمانی"
                lines.append(f"- {p.title} (ID: {p.template_id}) | حجم: {limit_str} | مدت: {dur_str}")
            await message.answer("پلن‌های موجود:\n" + "\n".join(lines))
    except Exception as e:
        logging.exception("Failed to fetch plans from DB: %s", e)
        await message.answer("خطا در دریافت پلن‌ها از سیستم. لطفاً کمی بعد تلاش کنید.")
