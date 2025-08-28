from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiojobs import create_scheduler

from app.db.session import session_scope


logger = logging.getLogger(__name__)


async def job_sync_plans() -> None:
    from app.scripts.sync_plans import sync_templates_to_plans
    async with session_scope() as session:
        changed = await sync_templates_to_plans(session)
        logger.info("job_sync_plans done", extra={"extra": {"changed": changed}})


async def job_notify_usage() -> None:
    # TODO: implement usage notifications
    logger.info("job_notify_usage tick")


async def job_notify_expiry() -> None:
    # TODO: implement expiry notifications
    logger.info("job_notify_expiry tick")


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
    await sched.spawn(periodic(job_sync_plans, 6 * 60 * 60))  # every 6h
    await sched.spawn(periodic(job_notify_usage, 60 * 60))     # every 1h
    await sched.spawn(periodic(job_notify_expiry, 24 * 60 * 60))  # every 24h

    logger.info("scheduler started")
