import asyncio
import logging
import os
import sys
from typing import Optional

import httpx
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


# ----------------------
# Config helpers
# ----------------------

def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_str(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = os.getenv(name, default)
    if required and not val:
        print(f"Missing required environment variable: {name}")
        sys.exit(2)
    return val


class Config:
    def __init__(self) -> None:
        self.bot_token: str = _env_str("BOT_TOKEN", required=True)  # Telegram bot token
        self.marzban_base_url: str = _env_str("MARZBAN_BASE_URL", required=True)  # e.g. https://panel.example.com
        # Provide either MARZBAN_ADMIN_TOKEN or MARZBAN_ADMIN_USERNAME + MARZBAN_ADMIN_PASSWORD
        self.marzban_admin_token: Optional[str] = _env_str("MARZBAN_ADMIN_TOKEN")
        self.marzban_admin_username: Optional[str] = _env_str("MARZBAN_ADMIN_USERNAME")
        self.marzban_admin_password: Optional[str] = _env_str("MARZBAN_ADMIN_PASSWORD")
        self.verify_ssl: bool = _env_bool("MARZBAN_VERIFY_SSL", True)


# ----------------------
# Marzban API client
# ----------------------

class MarzbanClient:
    def __init__(self, base_url: str, *, token: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None, verify_ssl: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._username = username
        self._password = password
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(20.0), verify=verify_ssl)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _ensure_token(self) -> None:
        if self._token:
            return
        if not self._username or not self._password:
            raise RuntimeError("Marzban admin token not provided and credentials missing")
        # Obtain admin token
        resp = await self._client.post("/api/admin/token", json={"username": self._username, "password": self._password})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Failed to get admin token: {e.response.status_code} {e.response.text}") from e
        data = resp.json()
        # Try common key names
        self._token = data.get("access_token") or data.get("token") or data.get("accessToken")
        if not self._token:
            raise RuntimeError(f"Admin token not found in response keys: {list(data.keys())}")

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        await self._ensure_token()
        headers = kwargs.pop("headers", {})
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return await self._client.request(method, url, headers=headers, **kwargs)

    async def get_system(self) -> dict:
        resp = await self._request("GET", "/api/system")
        resp.raise_for_status()
        return resp.json()

    async def get_admin_me(self) -> dict:
        resp = await self._request("GET", "/api/admin")
        resp.raise_for_status()
        return resp.json()


# ----------------------
# Telegram Bot Handlers
# ----------------------

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="وضعیت Marzban /ping")]], resize_keyboard=True)
    await message.answer(
        "سلام. ربات مدیریت Marzban آماده است.\n"
        "با دستور /ping اتصال به پنل تست می‌شود.",
        reply_markup=kb,
    )


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    client: MarzbanClient = message.bot.get("marzban_client")
    try:
        sys_info = await client.get_system()
        # Try to extract something meaningful
        cpu = sys_info.get("cpu") or sys_info.get("cpu_usage") or sys_info.get("cpu_percent")
        mem = sys_info.get("memory") or sys_info.get("mem_usage") or sys_info.get("memory_percent")
        nodes = sys_info.get("nodes") or sys_info.get("node_count")
        await message.answer(
            "اتصال برقرار است.\n"
            f"CPU: {cpu}\n"
            f"Memory: {mem}\n"
            f"Nodes: {nodes}"
        )
    except Exception as e:
        logging.exception("Ping failed")
        await message.answer(f"خطا در ارتباط با Marzban: {e}")


# ----------------------
# Entrypoint
# ----------------------

async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = Config()

    marzban = MarzbanClient(
        cfg.marzban_base_url,
        token=cfg.marzban_admin_token,
        username=cfg.marzban_admin_username,
        password=cfg.marzban_admin_password,
        verify_ssl=cfg.verify_ssl,
    )

    # Ensure we can fetch admin info early for clarity
    try:
        _ = await marzban.get_admin_me()
        logging.info("Authenticated to Marzban as admin")
    except Exception as e:
        logging.warning("Marzban admin auth check failed: %s", e)
        # Do not exit, allow /ping to show detailed error to the operator

    bot = Bot(cfg.bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    # attach marzban client to bot context
    bot["marzban_client"] = marzban

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await marzban.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
