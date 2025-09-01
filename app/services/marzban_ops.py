from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx

from app.marzban.client import get_client
from app.db.models import Plan

logger = logging.getLogger(__name__)


async def _get_vless_inbound_tags(client) -> List[str]:
    try:
        resp = await client._request("GET", "/api/inbounds")
        data = resp.json()
        vless = data.get("vless", []) if isinstance(data, dict) else []
        tags = [item.get("tag") for item in vless if isinstance(item, dict) and item.get("tag")]
        return [t for t in tags if t and t.lower() != "info"] or tags
    except Exception as e:
        logger.warning("failed to fetch inbounds: %s", e)
        return []


async def create_user_minimal(username: str, note: str = "") -> Dict[str, Any]:
    client = await get_client()
    try:
        vless_tags = await _get_vless_inbound_tags(client)
        payload: Dict[str, Any] = {
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
            "note": note,
        }
        try:
            # allow 409 to pass through without raising/logging; we'll fallback to GET
            resp = await client._request("POST", "/api/user", allowed_statuses={409}, json=payload)
            if resp.status_code == 409:
                resp = await client._request("GET", f"/api/user/{username}")
            return resp.json()
        except httpx.HTTPStatusError:
            # other HTTP errors propagate
            raise
    finally:
        await client.aclose()


async def update_user_limits(username: str, data_limit_gb: int | float, duration_days: int) -> Dict[str, Any]:
    client = await get_client()
    try:
        expire_ts = int((datetime.now(timezone.utc) + timedelta(days=duration_days)).timestamp()) if duration_days > 0 else 0
        data_limit = int(float(data_limit_gb) * (1024 ** 3)) if data_limit_gb and data_limit_gb > 0 else 0
        await client.update_user(username, {"expire": expire_ts})
        await client.update_user(username, {"data_limit": data_limit})
        resp = await client._request("GET", f"/api/user/{username}")
        return resp.json()
    finally:
        await client.aclose()


async def delete_user(username: str) -> None:
    client = await get_client()
    try:
        # Ignore 404 to avoid noisy logs when user was already removed
        await client._request("DELETE", f"/api/user/{username}", allowed_statuses={404})
    finally:
        await client.aclose()


async def reset_user(username: str) -> Dict[str, Any]:
    client = await get_client()
    try:
        resp = await client._request("POST", f"/api/user/{username}/reset")
        return resp.json()
    finally:
        await client.aclose()


async def revoke_sub(username: str) -> Dict[str, Any]:
    client = await get_client()
    try:
        resp = await client._request("POST", f"/api/user/{username}/revoke_sub")
        return resp.json()
    finally:
        await client.aclose()


async def get_user(username: str) -> Dict[str, Any]:
    client = await get_client()
    try:
        return await client.get_user(username)
    finally:
        await client.aclose()


async def get_user_summary(username: str) -> Dict[str, Any]:
    data = await get_user(username)
    def gb(v: int | None) -> str:
        if not v or v <= 0:
            return "∞"
        return f"{v / (1024**3):.2f} GB"
    data_limit = int(data.get("data_limit") or 0)
    used = int(data.get("used_traffic") or 0)
    remaining = max(data_limit - used, 0) if data_limit > 0 else 0
    return {
        "username": data.get("username"),
        "status": data.get("status"),
        "expire": data.get("expire"),
        "data_limit": data_limit,
        "used_traffic": used,
        "remaining": remaining,
        "subscription_url": data.get("subscription_url", ""),
        "links": data.get("links", []),
        "summary_text": (
            f"user: {data.get('username')}\n"
            f"status: {data.get('status')}\n"
            f"limit: {gb(data_limit)}\n"
            f"used: {gb(used)}\n"
            f"remaining: {gb(remaining)}\n"
        ),
    }


async def set_status(username: str, status: str) -> Dict[str, Any]:
    client = await get_client()
    try:
        await client.update_user(username, {"status": status})
        return await get_user(username)
    finally:
        await client.aclose()


async def add_data_gb(username: str, delta_gb: float) -> Dict[str, Any]:
    current = await get_user(username)
    current_limit = int(current.get("data_limit") or 0)
    add_bytes = int(float(delta_gb) * (1024 ** 3))
    new_limit = (current_limit if current_limit > 0 else 0) + add_bytes
    client = await get_client()
    try:
        await client.update_user(username, {"data_limit": new_limit})
        return await get_user(username)
    finally:
        await client.aclose()


async def replace_user_username(old_username: str, new_username: str, note: str = "") -> Dict[str, Any]:
    """Replace a user's username in Marzban to avoid duplicates.
    Strategy:
      - If names are equal → ensure user exists via create_user_minimal
      - If different → try to delete old (ignore 404), then create minimal new
    Returns the resulting user snapshot for new_username.
    """
    if not new_username:
        raise ValueError("new_username is required")
    if old_username == new_username:
        return await create_user_minimal(new_username, note=note)
    # Delete old user best-effort
    try:
        await delete_user(old_username)
    except Exception:
        pass
    # Create new minimal
    return await create_user_minimal(new_username, note=note or f"rename from {old_username}")


async def provision_for_plan(username: str, plan: Plan) -> Dict[str, Any]:
    """Provision user for a given Plan using UI-safe flow.
    - Ensure minimal user exists
    - Set expire and data_limit based on plan
    - Return current user snapshot
    """
    await create_user_minimal(username, note=f"order: {plan.title}")
    # Plan fields are bytes and days
    gb = (plan.data_limit_bytes or 0) / (1024 ** 3)
    days = int(plan.duration_days or 0)
    return await update_user_limits(username, gb, days)


async def extend_expire(username: str, delta_days: int) -> Dict[str, Any]:
    current = await get_user(username)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    current_exp = int(current.get("expire") or 0)
    base = current_exp if current_exp and current_exp > 0 else now_ts
    new_exp = base + delta_days * 86400
    client = await get_client()
    try:
        await client.update_user(username, {"expire": new_exp})
        return await get_user(username)
    finally:
        await client.aclose()


async def list_expired() -> List[Dict[str, Any]]:
    client = await get_client()
    try:
        resp = await client._request("GET", "/api/users/expired")
        data = resp.json()
        return data if isinstance(data, list) else data.get("result", [])
    finally:
        await client.aclose()


async def delete_expired() -> Dict[str, Any]:
    """Delete expired users.

    Behavior:
      - Try bulk DELETE /api/users/expired
      - If 404 (endpoint missing), fallback to GET list and DELETE each user
      - Return a summary dict
    """
    client = await get_client()
    try:
        try:
            resp = await client._request("DELETE", "/api/users/expired")
            # Prefer JSON if available
            try:
                data = resp.json()
                return data if isinstance(data, dict) else {"status": resp.status_code}
            except Exception:
                return {"status": resp.status_code}
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else None
            if status != 404:
                raise
            # Fallback: list then delete individually
            try:
                lst_resp = await client._request("GET", "/api/users/expired")
                items = lst_resp.json()
                users = items if isinstance(items, list) else items.get("result", [])
                usernames = [u.get("username") for u in users if isinstance(u, dict) and u.get("username")]
            except Exception:
                usernames = []
            if not usernames:
                return {"deleted": 0, "failed": 0, "bulk": False, "reason": "not_found"}
            deleted = 0
            failed = 0
            for u in usernames:
                try:
                    await client._request("DELETE", f"/api/user/{u}")
                    deleted += 1
                except Exception:
                    failed += 1
            return {"deleted": deleted, "failed": failed, "bulk": False}
    finally:
        await client.aclose()
