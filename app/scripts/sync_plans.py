from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models import Plan
from app.marzban.client import get_client


def _to_days(expire_seconds: Any) -> int:
    try:
        sec = int(expire_seconds or 0)
        return int(sec // 86400) if sec > 0 else 0
    except Exception:
        return 0


def _to_bytes(limit: Any) -> int:
    try:
        val = int(limit or 0)
        return val if val >= 0 else 0
    except Exception:
        return 0


async def sync_templates_to_plans(session: AsyncSession) -> int:
    # If sync is disabled by env, do nothing
    import os
    if os.getenv("SYNC_TEMPLATES_DISABLED", "0").strip() in {"1", "true", "True"}:
        return 0
    client = await get_client()
    created_or_updated = 0
    try:
        data = await client.get_user_templates()
        templates: Iterable[Dict[str, Any]] = data if isinstance(data, list) else data.get("result", [])
        now = datetime.utcnow()
        for t in templates:
            tpl_id = t.get("id") or t.get("template_id")
            if not tpl_id:
                continue
            name = t.get("name") or t.get("title") or f"Template #{tpl_id}"
            data_limit = _to_bytes(t.get("data_limit", 0))
            duration_days = _to_days(t.get("expire_duration", 0))

            existing = await session.scalar(select(Plan).where(Plan.template_id == int(tpl_id)))
            if existing is None:
                p = Plan(
                    template_id=int(tpl_id),
                    title=str(name),
                    price=0,
                    currency="IRR",
                    duration_days=duration_days if duration_days > 0 else 0,
                    data_limit_bytes=data_limit,
                    description=None,
                    is_active=True,
                    updated_at=now,
                )
                session.add(p)
                created_or_updated += 1
            else:
                # Update fields but DO NOT re-activate if user deactivated plan manually
                existing.title = str(name)
                existing.duration_days = duration_days if duration_days > 0 else 0
                existing.data_limit_bytes = data_limit
                if existing.is_active is None:
                    existing.is_active = True
                existing.updated_at = now
                created_or_updated += 1
        await session.commit()
        return created_or_updated
    finally:
        await client.aclose()


async def main() -> None:
    async for session in get_session():
        changed = await sync_templates_to_plans(session)
        print(f"synced plans: {changed}")


if __name__ == "__main__":
    asyncio.run(main())
