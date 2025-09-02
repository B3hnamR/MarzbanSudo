from __future__ import annotations

import json
from typing import Any, Optional

from app.db.session import session_scope
from app.db.models import Setting


async def set_intent_json(key: str, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False)
    async with session_scope() as session:
        row = await session.get(Setting, key)
        if not row:
            session.add(Setting(key=key, value=data))
        else:
            row.value = data
        await session.commit()


async def get_intent_json(key: str) -> Optional[dict[str, Any]]:
    async with session_scope() as session:
        row = await session.get(Setting, key)
        if not row or row.value is None:
            return None
        try:
            return json.loads(row.value)
        except Exception:
            return None


async def clear_intent(key: str) -> None:
    async with session_scope() as session:
        row = await session.get(Setting, key)
        if row:
            await session.delete(row)
            await session.commit()
