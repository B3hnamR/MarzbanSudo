import asyncio
import logging
import os
from typing import List

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from app.db.session import get_session, session_scope
from app.logging_config import setup_logging
from app.bot.handlers import plans as plans_handlers
from app.bot.middlewares.rate_limit import RateLimitMiddleware

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
    setup_logging()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN تنظیم نشده است. آن را در فایل .env قرار دهید.")
        raise SystemExit(1)

    bot = Bot(token=token)
    dp = Dispatcher()

    # Rate limit per-user (apply to message and callback_query updates)
    try:
        max_per_min = int(os.getenv("RATE_LIMIT_USER_MSG_PER_MIN", "20"))
    except ValueError:
        max_per_min = 20
    rate_limiter = RateLimitMiddleware(max_per_minute=max_per_min)
    dp.message.middleware(rate_limiter)
    dp.callback_query.middleware(rate_limiter)

    dp.include_router(router)
    dp.include_router(plans_handlers.router)

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
