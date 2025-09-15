from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from aiojobs import create_scheduler
import httpx
from sqlalchemy import select, update, and_

from app.db.session import session_scope
from app.db.models import User, Order
from app.services.notifications import notify_user, notify_log
from app.services.marzban_ops import get_user as mz_get_user
from app.config import settings

logger = logging.getLogger(__name__)


async def job_sync_plans() -> None:
    from app.scripts.sync_plans import sync_templates_to_plans
    async with session_scope() as session:
        changed = await sync_templates_to_plans(session)
        logger.info("job_sync_plans done", extra={"extra": {"changed": changed}})


async def job_notify_usage() -> None:
    """Fetch usage from Marzban and notify users when crossing configured thresholds.
    Uses settings.NOTIFY_USAGE_THRESHOLDS as CSV (e.g., "0.7,0.9").
    Stores last_notified_usage_threshold to avoid duplicate notifications.
    """
    try:
        thresholds = [float(x.strip()) for x in settings.notify_usage_thresholds.split(',') if x.strip()]
        thresholds = sorted(set([t for t in thresholds if 0 < t < 1]))
    except Exception:
        thresholds = [0.7, 0.9]
    if not thresholds:
        return

    async with session_scope() as session:
        users = (await session.execute(select(User).where(User.status == "active"))).scalars().all()
        for u in users:
            try:
                data = await mz_get_user(u.marzban_username)
                limit = int(data.get("data_limit") or 0)
                used = int(data.get("used_traffic") or 0)
                ratio = (used / limit) if (limit and limit > 0) else 0.0
                last_notified = float(u.last_notified_usage_threshold or 0)
                crossed = None
                for t in thresholds:
                    if ratio >= t and t > last_notified:
                        crossed = t
                if crossed is None:
                    continue
                u.last_usage_bytes = used
                u.last_usage_ratio = Decimal(str(ratio))
                u.last_notified_usage_threshold = Decimal(str(crossed))
                await session.flush()
                pct = int(crossed * 100)
                await notify_user(u.telegram_id, f"⚠️ اطلاعیه مصرف: شما از {pct}% حجم سرویس خود عبور کرده‌اید.")
            except httpx.HTTPStatusError as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 404:
                    logger.info(
                        "job_notify_usage: user not found in Marzban; skipping",
                        extra={"extra": {"user_id": u.id, "username": u.marzban_username}},
                    )
                    continue
                logger.exception("job_notify_usage: http error for user %s", u.id)
            except Exception:
                logger.exception("job_notify_usage: error for user %s", u.id)
        await session.commit()


async def job_notify_expiry() -> None:
    """Notify users N days before expiry based on settings.NOTIFY_EXPIRY_DAYS (CSV of days)."""
    try:
        days_list = [int(x.strip()) for x in settings.notify_expiry_days.split(',') if x.strip()]
        days_list = sorted(set([d for d in days_list if d >= 0]))
    except Exception:
        days_list = [3, 1, 0]
    if not days_list:
        return

    now = datetime.now(timezone.utc)
    async with session_scope() as session:
        users = (await session.execute(select(User).where(User.status == "active"))).scalars().all()
        for u in users:
            try:
                data = await mz_get_user(u.marzban_username)
                expire_ts = int(data.get("expire") or 0)
                if expire_ts <= 0:
                    continue
                exp_dt = datetime.fromtimestamp(expire_ts, tz=timezone.utc)
                days_left = (exp_dt.date() - now.date()).days
                last_day = int(u.last_notified_expiry_day or -999)
                if days_left in days_list and days_left != last_day:
                    u.last_notified_expiry_day = days_left
                    await session.flush()
                    await notify_user(u.telegram_id, f"⏳ اطلاعیه انقضا: {days_left} روز تا پایان سرویس باقی مانده است.")
            except httpx.HTTPStatusError as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 404:
                    logger.info(
                        "job_notify_expiry: user not found in Marzban; skipping",
                        extra={"extra": {"user_id": u.id, "username": u.marzban_username}},
                    )
                    continue
                logger.exception("job_notify_expiry: http error for user %s", u.id)
            except Exception:
                logger.exception("job_notify_expiry: error for user %s", u.id)
        await session.commit()


async def job_cleanup_receipts() -> None:
    """Placeholder cleanup; receipts are Telegram File IDs (no local files)."""
    days = settings.receipt_retention_days
    logger.debug("cleanup_receipts: retention=%s days; telegram file-id only, skipping disk cleanup", days)


async def job_autocancel_orders() -> None:
    """Auto-cancel stale pending orders after configured hours."""
    hours = settings.pending_order_autocancel_hours
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    async with session_scope() as session:
        res = await session.execute(
            update(Order)
            .where(and_(Order.status == "pending", Order.created_at < cutoff))
            .values(status="cancelled", updated_at=datetime.utcnow())
            .execution_options(synchronize_session=False)
        )
        count = res.rowcount or 0
        if count > 0:
            await notify_log(f"Auto-cancelled {count} pending orders older than {hours}h.")
        await session.commit()


async def run_scheduler() -> None:
    sched = await create_scheduler()

    async def periodic(coro, interval: float) -> None:
        while True:
            try:
                await coro()
            except Exception as e:
                logger.exception("periodic job error: %s", e)
            await asyncio.sleep(interval)

    # Schedule periodic jobs
    await sched.spawn(periodic(job_sync_plans, 6 * 60 * 60))         # every 6h
    await sched.spawn(periodic(job_notify_usage, 60 * 60))           # every 1h
    await sched.spawn(periodic(job_notify_expiry, 24 * 60 * 60))     # every 24h
    await sched.spawn(periodic(job_cleanup_receipts, 24 * 60 * 60))  # every 24h
    await sched.spawn(periodic(job_autocancel_orders, 60 * 60))      # every 1h

    logger.info("scheduler started")
    # Keep the scheduler running; on cancellation try to close bot singleton (notifications)
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        try:
            from app.services.notifications import aclose_bot
            await aclose_bot()
        except Exception:
            pass
        raise

