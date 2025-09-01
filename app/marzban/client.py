from __future__ import annotations

import asyncio
import logging
import random
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
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0, read=10.0, write=10.0))
        self._auth_lock = asyncio.Lock()
        self._max_attempts = 3
        self._backoff_base = 0.5  # seconds

    async def _ensure_token(self) -> None:
        if self._auth.access_token:
            return
        async with self._auth_lock:
            if self._auth.access_token:
                return
            await self._login()

    async def _login(self) -> None:
        url = f"{self.base_url}/api/admin/token"
        # Use form-encoded grant_type=password for compatibility with Marzban 0.8.4
        form = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "accept": "application/json",
        }
        resp = await self._client.post(url, data=form, headers=headers)
        resp.raise_for_status()
        data_json = resp.json()
        token = data_json.get("access_token")
        if not token:
            raise RuntimeError("Marzban token missing in response")
        self._auth.access_token = token
        logging.info("Marzban token acquired")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        if self._auth.access_token:
            headers["Authorization"] = f"Bearer {self._auth.access_token}"
        return headers

    async def _request(self, method: str, path: str, allowed_statuses: Optional[set[int]] = None, **kwargs: Any) -> httpx.Response:
        await self._ensure_token()
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                resp = await self._client.request(method, url, headers=self._headers(), **kwargs)
                if resp.status_code == 401:
                    # token expired → retry once after re-login
                    async with self._auth_lock:
                        self._auth.access_token = None
                        await self._login()
                    resp = await self._client.request(method, url, headers=self._headers(), **kwargs)

                if resp.status_code in {429, 502, 503, 504}:
                    if attempt < self._max_attempts:
                        delay = self._backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                        logging.warning("Retryable status %s on %s %s, attempt %d/%d, sleeping %.2fs", resp.status_code, method, url, attempt, self._max_attempts, delay)
                        await asyncio.sleep(delay)
                        continue
                # Allow certain statuses to pass through without raising/logging (e.g., 409 conflict on create)
                if allowed_statuses and resp.status_code in allowed_statuses:
                    return resp
                resp.raise_for_status()
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteError, httpx.ReadError, httpx.TransportError, httpx.TimeoutException) as e:  # type: ignore[attr-defined]
                last_exc = e
                if attempt < self._max_attempts:
                    delay = self._backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                    logging.warning("Network error on %s %s: %s, attempt %d/%d, sleeping %.2fs", method, url, e, attempt, self._max_attempts, delay)
                    await asyncio.sleep(delay)
                    continue
                logging.exception("HTTP transport error on %s %s after %d attempts: %s", method, url, attempt, e)
                raise
            except httpx.HTTPError as e:
                # Non-retryable HTTP error
                logging.exception("HTTP error on %s %s: %s", method, url, e)
                raise
        # If loop exits without return and without raising (unlikely), raise last exception
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"Request failed without exception: {method} {url}")

    # API wrappers (to be completed in Phase 1)
    async def get_user_templates(self) -> Dict[str, Any]:
        resp = await self._request("GET", "/api/user_template")
        return resp.json()

    async def get_user(self, username: str) -> Dict[str, Any]:
        # Treat 404 as an allowed status to avoid noisy error logging in _request,
        # then re-raise a HTTPStatusError here so callers can handle it gracefully.
        resp = await self._request("GET", f"/api/user/{username}", allowed_statuses={404})
        if resp.status_code == 404:
            raise httpx.HTTPStatusError(
                message=f"Client error '404 Not Found' for url '{resp.request.url}'",
                request=resp.request,
                response=resp,
            )
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
