from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.marzban.client import get_client
from sqlalchemy import select
from app.db.session import session_scope
from app.db.models import Setting
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
    # Resolve trial config from DB (overrides ENV), with ENV fallback
    enabled = settings.trial_enabled
    data_gb = settings.trial_data_gb
    duration_days = settings.trial_duration_days
    one_per_user = False
    access_mode = "public"  # public | whitelist
    try:
        async with session_scope() as session:
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_ENABLED"))
            if row:
                enabled = str(row.value).strip() in {"1", "true", "True"}
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_DATA_GB"))
            if row:
                try:
                    data_gb = int(str(row.value).strip())
                except Exception:
                    pass
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_DURATION_DAYS"))
            if row:
                try:
                    duration_days = int(str(row.value).strip())
                except Exception:
                    pass
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_ONE_PER_USER"))
            if row:
                one_per_user = str(row.value).strip() in {"1", "true", "True"}
            row = await session.scalar(select(Setting).where(Setting.key == "TRIAL_ACCESS_MODE"))
            if row:
                val = str(row.value).strip().lower()
                if val in {"public", "whitelist"}:
                    access_mode = val
            if one_per_user:
                used = await session.scalar(select(Setting).where(Setting.key == f"USER:{telegram_id}:TRIAL_USED_AT"))
                if used and str(used.value).strip():
                    raise RuntimeError("trial_already_used")
            # Per-user access policy
            if access_mode == "whitelist":
                allow = await session.scalar(select(Setting).where(Setting.key == f"USER:{telegram_id}:TRIAL_ALLOWED"))
                if not (allow and str(allow.value).strip() in {"1", "true", "True"}):
                    raise RuntimeError("trial_not_allowed")
            else:
                deny = await session.scalar(select(Setting).where(Setting.key == f"USER:{telegram_id}:TRIAL_DISABLED"))
                if deny and str(deny.value).strip() in {"1", "true", "True"}:
                    raise RuntimeError("trial_disabled_user")
    except RuntimeError:
        raise
    except Exception:
        # On any error reading settings, proceed with ENV defaults
        pass

    if not enabled:
        raise RuntimeError("trial_disabled")

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
        expire_ts = int((datetime.now(timezone.utc) + timedelta(days=duration_days)).timestamp()) if duration_days > 0 else 0
        data_limit_bytes = int(data_gb) * 1024 ** 3 if data_gb > 0 else 0

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
            result = await client.get_user(username)
            # Mark trial used for user if policy is one-per-user
            if one_per_user:
                try:
                    from datetime import datetime as _dt
                    async with session_scope() as session:
                        row = await session.scalar(select(Setting).where(Setting.key == f"USER:{telegram_id}:TRIAL_USED_AT"))
                        ts = _dt.utcnow().isoformat()
                        if not row:
                            session.add(Setting(key=f"USER:{telegram_id}:TRIAL_USED_AT", value=ts))
                        else:
                            row.value = ts
                        await session.commit()
                except Exception:
                    pass
            return result
        except Exception:
            # If fetch fails, synthesize a minimal response
            return {"username": username, "status": "active", "data_limit": data_limit_bytes, "expire": expire_ts}
    finally:
        await client.aclose()
