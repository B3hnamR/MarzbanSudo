import os
import sys
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Healthcheck: validate ENV, token presence, and DB connectivity (SELECT 1)

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


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("missing TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1

    ok_db = asyncio.run(_check_db())
    if not ok_db:
        print("db not ready", file=sys.stderr)
        return 1

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
