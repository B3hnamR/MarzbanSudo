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
from app.bot.handlers import start as start_handlers
from app.bot.handlers import account as account_handlers
from app.bot.handlers import admin as admin_handlers
from app.bot.handlers import admin_manage as admin_manage_handlers
from app.bot.handlers import orders as orders_handlers
from app.bot.handlers import admin_orders as admin_orders_handlers
from app.bot.handlers import trial as trial_handlers
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
    dp.include_router(start_handlers.router)
    dp.include_router(plans_handlers.router)
    dp.include_router(account_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(admin_manage_handlers.router)
    dp.include_router(orders_handlers.router)
    dp.include_router(admin_orders_handlers.router)
    dp.include_router(trial_handlers.router)

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
