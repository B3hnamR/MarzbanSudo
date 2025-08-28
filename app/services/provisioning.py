from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.marzban.client import get_client
from app.utils.username import tg_username
from app.config import settings


logger = logging.getLogger(__name__)


async def provision_trial(telegram_id: int) -> dict:
    """Create or refresh a trial user in Marzban with configured limits.

    Returns a dict with created/updated info and subscription details.
    """
    client = await get_client()
    try:
        username = tg_username(telegram_id)
        data_limit = settings.trial_data_gb * 1024 ** 3
        expire_at = datetime.now(timezone.utc) + timedelta(days=settings.trial_duration_days)
        expire_ts = int(expire_at.timestamp())
        payload = {
            "username": username,
            "template_id": settings.trial_template_id,
            "data_limit": data_limit,
            "expire": expire_ts,
            "note": f"trial: {settings.trial_data_gb}GB/{settings.trial_duration_days}d",
        }
        # Try create; if user exists, update
        try:
            created = await client.create_user(**payload)
            logger.info("trial created", extra={"extra": {"username": username}})
            return created
        except Exception as e:
            logger.info("create_user failed, trying update", extra={"extra": {"username": username}})
            # Update user with new limits (extend or reset volume)
            updated = await client.update_user(username, {
                "data_limit": data_limit,
                "expire": expire_ts,
            })
            return updated
    finally:
        await client.aclose()
