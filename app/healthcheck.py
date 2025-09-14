import os
import sys
import asyncio

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Healthcheck: validate ENV, Telegram token presence, DB connectivity (SELECT 1),
# and optional Marzban admin reachability.
#
# You can skip the Marzban check by setting HEALTHCHECK_SKIP_MARZBAN=1
# (useful in staging or when Marzban is temporarily unavailable).

async def _check_db() -> bool:
    db_url = os.getenv("DB_URL", "")
    if not db_url:
        return False
    try:
        engine = create_async_engine(db_url, pool_pre_ping=True)
        async with engine.connect() as conn:  # type: ignore[func-returns-value]
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


async def _check_marzban() -> bool:
    base = (os.getenv("MARZBAN_BASE_URL", "") or "").rstrip("/")
    username = os.getenv("MARZBAN_ADMIN_USERNAME", "") or ""
    password = os.getenv("MARZBAN_ADMIN_PASSWORD", "") or ""
    if not base or not username or not password:
        return False
    try:
        timeout = httpx.Timeout(12.0, connect=6.0, read=6.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Acquire token (form-encoded as in client.py for 0.8.4)
            resp = await client.post(
                f"{base}/api/admin/token",
                data={
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "accept": "application/json",
                },
            )
            resp.raise_for_status()
            token = resp.json().get("access_token")
            if not token:
                return False
            # Light probe
            resp2 = await client.get(
                f"{base}/api/user_template",
                headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
            )
            resp2.raise_for_status()
            return True
    except Exception:
        return False


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("missing TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1

    ok_db = asyncio.run(_check_db())
    if not ok_db:
        print("db not ready", file=sys.stderr)
        return 1

    skip_mz = (os.getenv("HEALTHCHECK_SKIP_MARZBAN", "0").strip().lower() in {"1", "true", "yes", "on"})
    if not skip_mz:
        ok_mz = asyncio.run(_check_marzban())
        if not ok_mz:
            print("marzban not ready", file=sys.stderr)
            return 1
    else:
        # Skipped by env
        pass

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
