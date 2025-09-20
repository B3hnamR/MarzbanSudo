import asyncio
import logging
import os
from typing import List

from aiogram import Bot, Dispatcher, Router, F
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
from app.bot.handlers import wallet as wallet_handlers
from app.bot.handlers import admin_users as admin_users_handlers
from app.bot.handlers import admin_trial as admin_trial_handlers
from app.bot.middlewares.rate_limit import RateLimitMiddleware
from app.bot.middlewares.ban_gate import BanGateMiddleware
from app.bot.middlewares.correlation import CorrelationMiddleware
from app.bot.middlewares.channel_gate import ChannelGateMiddleware
from app.config import settings
from app.marzban.client import aclose_shared as aclose_mz_shared

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

    token = settings.telegram_bot_token
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN تنظیم نشده است. آن را در فایل .env قرار دهید.")
        raise SystemExit(1)

    bot = Bot(token=token)
    dp = Dispatcher()

    # Rate limit per-user (apply to message and callback_query updates)
    max_per_min = settings.rate_limit_user_msg_per_min
    # High-priority ban gate middleware (must be first)
    dp.message.middleware(BanGateMiddleware())
    dp.callback_query.middleware(BanGateMiddleware())

    # Correlation id middleware for observability
    corr = CorrelationMiddleware()
    dp.message.middleware(corr)
    dp.callback_query.middleware(corr)

    # Channel gate middleware (enforce REQUIRED_CHANNEL on every update)
    ch_gate = ChannelGateMiddleware()
    dp.message.middleware(ch_gate)
    dp.callback_query.middleware(ch_gate)

    rate_limiter = RateLimitMiddleware(max_per_minute=max_per_min)
    dp.message.middleware(rate_limiter)
    dp.callback_query.middleware(rate_limiter)

    # High-priority coupons wizard bridge: route any text to coupon wizard when active
    async def _cpw_bridge_entry(message: Message) -> None:
        try:
            # Only delegate for plain text (not commands) and when wizard expects text
            txt = getattr(message, "text", None)
            if not isinstance(txt, str) or txt.startswith("/"):
                return
            from app.utils.intent_store import get_intent_json as _get_intent
            uid = getattr(getattr(message, "from_user", None), "id", None)
            cpw = await _get_intent(f"INTENT:CPW:{uid}") if uid else None
            if not cpw:
                return
            stage = str(cpw.get("stage") or "")
            if stage in {"await_code", "await_value", "await_cap", "await_min", "await_title"}:
                from app.bot.handlers import admin_coupons as _ac
                await _ac._msg_wizard_capture(message)  # type: ignore[attr-defined]
                return
        except Exception:
            pass

    try:
        dp.message.register(_cpw_bridge_entry, F.text, flags={"block": True})
    except Exception:
        pass

    # High-priority numeric bridge: route numeric texts to start router bridge before other routers
    async def _numeric_bridge_entry(message: Message) -> None:
        try:
            from app.bot.handlers import start as start_handlers  # local import to avoid cycles
            # Coupons wizard has priority: if active, delegate to its capture handler
            try:
                from app.utils.intent_store import get_intent_json as _get_intent
                uid = getattr(getattr(message, "from_user", None), "id", None)
                cpw = await _get_intent(f"INTENT:CPW:{uid}") if uid else None
                if cpw:
                    from app.bot.handlers import admin_coupons as _ac
                    await _ac._msg_wizard_capture(message)  # type: ignore[attr-defined]
                    return
            except Exception:
                pass
            # Route-by-stage: if WADM awaiting reference, delegate to ref bridge first
            try:
                from app.utils.intent_store import get_intent_json as _get_intent
                uid = getattr(getattr(message, "from_user", None), "id", None)
                payload = await _get_intent(f"INTENT:WADM:{uid}") if uid else None
                if payload and str(payload.get("stage")) == "await_ref":
                    await start_handlers._bridge_wallet_manual_add_ref(message)  # type: ignore[attr-defined]
                    return
            except Exception:
                pass
            # Otherwise, handle numeric as amount/settings/custom
            await start_handlers._bridge_wallet_numeric(message)  # type: ignore[attr-defined]
        except Exception:
            pass

    # Strict numeric (ASCII/Persian digits), then permissive fallback (any text containing digits)
    try:
        dp.message.register(
            _numeric_bridge_entry,
            F.text.regexp(r"^[0-9\u06F0-\u06F9][0-9\u06F0-\u06F9,\.]{0,13}$"),
        )
        dp.message.register(
            _numeric_bridge_entry,
            F.text.regexp(r".*[0-9\u06F0-\u06F9].*"),
        )
    except Exception:
        pass

    dp.include_router(router)
    dp.include_router(start_handlers.router)
    # Place admin and control routers before generic message catch-alls
    dp.include_router(admin_handlers.router)
    dp.include_router(admin_manage_handlers.router)
    dp.include_router(admin_orders_handlers.router)
    dp.include_router(admin_users_handlers.router)
    dp.include_router(admin_trial_handlers.router)
    # Coupons admin
    from app.bot.handlers import admin_coupons as admin_coupons_handlers
    dp.include_router(admin_coupons_handlers.router)
    # Functional user flows
    dp.include_router(orders_handlers.router)
    dp.include_router(account_handlers.router)
    dp.include_router(wallet_handlers.router)
    dp.include_router(trial_handlers.router)
    # Plans last to avoid its generic text handler swallowing commands
    dp.include_router(plans_handlers.router)

    # Polling startup
    logging.info("Starting Telegram bot polling ...")
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        # Close bot session(s)
        try:
            from app.services.notifications import aclose_bot
            await aclose_bot()
        except Exception:
            pass
        try:
            await aclose_mz_shared()
        except Exception:
            pass
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
