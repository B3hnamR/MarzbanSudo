import asyncio
import logging
import os
from typing import List

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.marzban.client import get_client
from app.db.session import get_session, session_scope
from app.db.models import Plan
from app.scripts.sync_plans import sync_templates_to_plans

try:
    # Optional: load .env in non-production environments
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


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
            logging.warning("Invalid admin id in TELEGRAM_ADMIN_IDS: %s", part)
    return ids


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    text = (
        "به MarzbanSudo خوش آمدید!\n\n"
        "- با دستور /plans پلن‌ها را ببینید.\n"
        "- با دستور /orders سفارش‌های خود را مدیریت کنید.\n"
        "- با دستور /account وضعیت اکانت و لینک‌ها را ببینید.\n"
    )
    await message.answer(text)


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
            lines = []
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


@router.message(Command("account"))
async def handle_account(message: Message) -> None:
    # Placeholder: در فازهای بعدی از DB و sub4me/info تغذیه می‌شود
    await message.answer("اطلاعات اکانت شما به‌زودی در دسترس خواهد بود.")


@router.message(Command("admin"))
async def handle_admin(message: Message) -> None:
    admin_ids = _get_admin_ids()
    if message.from_user and message.from_user.id in admin_ids:
        await message.answer("پنل ادمین: به‌زودی دستورهای مدیریتی فعال می‌شوند.")
    else:
        await message.answer("شما دسترسی ادمین ندارید.")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN تنظیم نشده است. آن را در فایل .env قرار دهید.")
        raise SystemExit(1)

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    # Polling startup
    logging.info("Starting Telegram bot polling ...")
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
