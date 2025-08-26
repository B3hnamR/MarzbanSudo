from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from app.config import settings


@dataclass
class MarzbanAuth:
    access_token: Optional[str] = None


class MarzbanClient:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._auth = MarzbanAuth()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self._auth_lock = asyncio.Lock()

    async def _ensure_token(self) -> None:
        if self._auth.access_token:
            return
        async with self._auth_lock:
            if self._auth.access_token:
                return
            await self._login()

    async def _login(self) -> None:
        url = f"{self.base_url}/api/admin/token"
        payload = {"username": self.username, "password": self.password}
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Marzban token missing in response")
        self._auth.access_token = token
        logging.info("Marzban token acquired")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._auth.access_token:
            headers["Authorization"] = f"Bearer {self._auth.access_token}"
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        await self._ensure_token()
        url = f"{self.base_url}{path}"
        try:
            resp = await self._client.request(method, url, headers=self._headers(), **kwargs)
            if resp.status_code == 401:
                # token expired → retry once
                async with self._auth_lock:
                    self._auth.access_token = None
                    await self._login()
                resp = await self._client.request(method, url, headers=self._headers(), **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPError as e:
            logging.exception("HTTP error on %s %s: %s", method, url, e)
            raise

    # API wrappers (to be completed in Phase 1)
    async def get_user_templates(self) -> Dict[str, Any]:
        resp = await self._request("GET", "/api/user_template")
        return resp.json()

    async def get_user(self, username: str) -> Dict[str, Any]:
        resp = await self._request("GET", f"/api/user/{username}")
        return resp.json()

    async def create_user(self, username: str, template_id: int, data_limit: int, expire: int, note: str = "") -> Dict[str, Any]:
        payload = {
            "username": username,
            "template_id": template_id,
            "data_limit": data_limit,
            "expire": expire,
            "note": note,
        }
        resp = await self._request("POST", "/api/user", json=payload)
        return resp.json()

    async def update_user(self, username: str, data: Dict[str, Any]) -> Dict[str, Any]:
        resp = await self._request("PUT", f"/api/user/{username}", json=data)
        return resp.json()

    async def reset_user(self, username: str) -> Dict[str, Any]:
        resp = await self._request("POST", f"/api/user/{username}/reset")
        return resp.json()

    async def revoke_sub(self, username: str) -> Dict[str, Any]:
        resp = await self._request("POST", f"/api/user/{username}/revoke_sub")
        return resp.json()

    async def get_sub_info(self, token: str) -> Dict[str, Any]:
        resp = await self._request("GET", f"/sub4me/{token}/info")
        return resp.json()

    async def get_sub_usage(self, token: str) -> Dict[str, Any]:
        resp = await self._request("GET", f"/sub4me/{token}/usage")
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()


async def get_client() -> MarzbanClient:
    return MarzbanClient(
        settings.marzban_base_url,
        settings.marzban_admin_username,
        settings.marzban_admin_password,
    )
