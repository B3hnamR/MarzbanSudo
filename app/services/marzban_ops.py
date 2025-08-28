from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx

from app.marzban.client import get_client

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
            resp = await client._request("POST", "/api/user", json=payload)
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 409:
                # already exists → return current
                resp = await client._request("GET", f"/api/user/{username}")
                return resp.json()
            raise
    finally:
        await client.aclose()


async def update_user_limits(username: str, data_limit_gb: int | float, duration_days: int) -> Dict[str, Any]:
    client = await get_client()
    try:
        expire_ts = int((datetime.now(timezone.utc) + timedelta(days=duration_days)).timestamp()) if duration_days > 0 else 0
        data_limit = int(float(data_limit_gb) * (1024 ** 3)) if data_limit_gb and data_limit_gb > 0 else 0
        # set expire
        await client.update_user(username, {"expire": expire_ts})
        # set data_limit
        await client.update_user(username, {"data_limit": data_limit})
        resp = await client._request("GET", f"/api/user/{username}")
        return resp.json()
    finally:
        await client.aclose()


async def delete_user(username: str) -> None:
    client = await get_client()
    try:
        await client._request("DELETE", f"/api/user/{username}")
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
        resp = await client._request("GET", f"/api/user/{username}")
        return resp.json()
    finally:
        await client.aclose()
