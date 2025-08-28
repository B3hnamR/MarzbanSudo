from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.marzban.client import get_client
from app.utils.username import tg_username
from app.config import settings


logger = logging.getLogger(__name__)


async def provision_trial(telegram_id: int) -> dict:
    """Create or refresh a trial user in Marzban with configured limits.

    Strategy:
      - Validate template exists.
      - Check if user exists (GET). If yes → try update; regardless of update result, return current user info.
      - If not exists → try create; on 409 → try update; finally return current user info if possible.
    """
    client = await get_client()
    try:
        # Validate template id exists on server
        templates = await client.get_user_templates()
        tpl_list = templates if isinstance(templates, list) else templates.get("result", [])
        if not any(int(t.get("id") or t.get("template_id", -1)) == settings.trial_template_id for t in tpl_list):
            raise RuntimeError(f"Invalid TRIAL_TEMPLATE_ID={settings.trial_template_id}; not found on Marzban")

        username = tg_username(telegram_id)
        data_limit = settings.trial_data_gb * 1024 ** 3
        expire_at = datetime.now(timezone.utc) + timedelta(days=settings.trial_duration_days)
        expire_ts = int(expire_at.timestamp())
        update_payload = {
            "data_limit": data_limit,
            "expire": expire_ts,
        }
        create_payload = {
            "username": username,
            "template_id": settings.trial_template_id,
            "data_limit": data_limit,
            "expire": expire_ts,
            "note": f"trial: {settings.trial_data_gb}GB/{settings.trial_duration_days}d",
        }

        # Check existence
        user_exists = False
        try:
            current = await client.get_user(username)
            user_exists = True
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                user_exists = False
            else:
                raise

        if user_exists:
            # Try update, but even if fails, return current info
            try:
                await client.update_user(username, update_payload)
                logger.info("trial updated", extra={"extra": {"username": username}})
            except httpx.HTTPStatusError as e:
                logger.warning("update_user failed", extra={"extra": {"username": username, "status": e.response.status_code if e.response else None}})
            # Return latest user info (best-effort)
            try:
                return await client.get_user(username)
            except Exception:
                # If fetching fails unexpectedly, fall back to previous snapshot
                return current
        else:
            # Try create; if conflict, try update; finally return current info if possible
            try:
                created = await client.create_user(**create_payload)
                logger.info("trial created", extra={"extra": {"username": username}})
                return created
            except httpx.HTTPStatusError as e:
                status = e.response.status_code if e.response else None
                logger.warning("create_user failed", extra={"extra": {"username": username, "status": status}})
                if status == 409:
                    try:
                        await client.update_user(username, update_payload)
                        logger.info("trial updated after conflict", extra={"extra": {"username": username}})
                    except httpx.HTTPStatusError as e2:
                        logger.warning(
                            "update_user after conflict failed",
                            extra={"extra": {"username": username, "status": e2.response.status_code if e2.response else None}},
                        )
                    # Return current info if available
                    try:
                        return await client.get_user(username)
                    except Exception:
                        raise
                else:
                    raise
    finally:
        await client.aclose()
