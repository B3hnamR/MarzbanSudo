from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


async def log_audit(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    target_type: str,
    target_id: Optional[int] = None,
    meta: Optional[str] = None,
) -> None:
    entry = AuditLog(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        meta=meta,
        created_at=datetime.utcnow(),
    )
    session.add(entry)
    await session.flush()
