from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.marzban.client import get_client
from app.utils.username import tg_username
from app.config import settings


logger = logging.getLogger(__name__)


async def _get_vless_inbound_tags(client) -> list[str]:
    """Fetch inbound tags for vless protocol and filter out non-service tags like 'Info'."""
    try:
        resp = await client._request("GET", "/api/inbounds")  # reuse authed client
        data = resp.json()
        vless = data.get("vless", []) if isinstance(data, dict) else []
        tags = [item.get("tag") for item in vless if isinstance(item, dict) and item.get("tag")]
        # Filter out control/info tags if present
        return [t for t in tags if t.lower() != "info"] or tags
    except Exception as e:
        logger.warning("failed to fetch inbounds; falling back to empty list: %s", e)
        return []


async def provision_trial(telegram_id: int) -> dict:
    """Create or refresh a trial user in Marzban with a safe, UI-compatible flow.

    Strategy:
      - Read vless inbound tags (exclude 'Info').
      - Create user with minimal payload (no template_id):
        username, status=active, expire=0, data_limit=0, data_limit_reset_strategy=no_reset,
        inbounds={vless: [...]}, proxies={vless: {}}.
      - Then set expire and data_limit via two separate PUT calls.
      - Finally return current user info.
    """
    client = await get_client()
    try:
        username = tg_username(telegram_id)

        # Prepare minimal creation payload
        vless_tags = await _get_vless_inbound_tags(client)
        if not vless_tags:
            # As a last resort, try to at least provide an empty vless proxies section
            vless_tags = []
        create_payload = {
            "username": username,
            "status": "active",
            "expire": 0,
            "data_limit": 0,
            "data_limit_reset_strategy": "no_reset",
            "inbounds": {"vless": vless_tags},
            "proxies": {"vless": {}},
            "next_plan": {
                "add_remaining_traffic": False,
                "data_limit": 0,
                "expire": 0,
                "fire_on_either": True,
            },
            "note": "trial:init",
        }

        # Create if not exists; if exists, proceed to update
        exists = False
        try:
            resp = await client._request("POST", "/api/user", json=create_payload)
            logger.info("trial created (minimal)", extra={"extra": {"username": username}})
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 409:
                exists = True
                logger.info("user exists; will update", extra={"extra": {"username": username}})
            else:
                # If non-409 on create, check if user actually exists; otherwise re-raise
                try:
                    await client.get_user(username)
                    exists = True
                except httpx.HTTPStatusError:
                    raise

        # Stage updates (expire then data_limit) if limits configured
        expire_ts = int((datetime.now(timezone.utc) + timedelta(days=settings.trial_duration_days)).timestamp()) if settings.trial_duration_days > 0 else 0
        data_limit_bytes = int(settings.trial_data_gb) * 1024 ** 3 if settings.trial_data_gb > 0 else 0

        # Update expire first
        try:
            await client.update_user(username, {"expire": expire_ts})
        except httpx.HTTPStatusError as e:
            logger.warning("set expire failed", extra={"extra": {"username": username, "status": e.response.status_code if e.response else None}})

        # Then update data_limit
        try:
            await client.update_user(username, {"data_limit": data_limit_bytes})
        except httpx.HTTPStatusError as e:
            logger.warning("set data_limit failed", extra={"extra": {"username": username, "status": e.response.status_code if e.response else None}})

        # Return current snapshot (best-effort)
        try:
            return await client.get_user(username)
        except Exception:
            # If fetch fails, synthesize a minimal response
            return {"username": username, "status": "active", "data_limit": data_limit_bytes, "expire": expire_ts}
    finally:
        await client.aclose()
