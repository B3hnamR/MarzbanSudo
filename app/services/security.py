from __future__ import annotations

import os
import asyncio
from typing import Set

from app.db.session import session_scope
from app.db.models import Setting

# Capability codes (examples for future role-based control)
CAP_PLANS_MANAGE = "PLANS_MANAGE"
CAP_PLANS_CREATE = "PLANS_CREATE"
CAP_PLANS_EDIT = "PLANS_EDIT"
CAP_PLANS_DELETE = "PLANS_DELETE"
CAP_PLANS_SET_PRICE = "PLANS_SET_PRICE"
CAP_PLANS_TOGGLE_ACTIVE = "PLANS_TOGGLE_ACTIVE"
CAP_ORDERS_MODERATE = "ORDERS_MODERATE"
CAP_WALLET_MODERATE = "WALLET_MODERATE"


def _parse_csv(s: str) -> Set[str]:
    return {x.strip().upper() for x in s.split(",") if x.strip()}


def _admin_ids() -> Set[int]:
    raw = os.getenv("TELEGRAM_ADMIN_IDS", "")
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}


def is_admin_uid(uid: int | None) -> bool:
    return bool(uid and uid in _admin_ids())


def get_admin_ids() -> Set[int]:
    """Return the set of admin Telegram user IDs from ENV/DB.
    Currently resolves from ENV (TELEGRAM_ADMIN_IDS) and optional DB overrides in future.
    """
    return _admin_ids()


async def _load_user_caps(uid: int) -> Set[str]:
    # DB override: Setting key = f"ADMIN_CAPS:{uid}", value = CSV of caps or "*"
    async with session_scope() as session:
        row = await session.get(Setting, f"ADMIN_CAPS:{uid}")
        if row and row.value:
            caps = _parse_csv(row.value)
            return caps if caps else {"*"}
    # ENV default: ADMIN_CAPS_DEFAULT="*" or CSV
    default = os.getenv("ADMIN_CAPS_DEFAULT", "*").strip()
    if default == "*" or not default:
        return {"*"}
    return _parse_csv(default)


async def has_capability_async(uid: int | None, code: str) -> bool:
    if not is_admin_uid(uid):
        return False
    caps = await _load_user_caps(int(uid))  # type: ignore[arg-type]
    return ("*" in caps) or (code.strip().upper() in caps)


def has_capability(uid: int | None, code: str) -> bool:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Best-effort fallback when inside an event loop
            default = os.getenv("ADMIN_CAPS_DEFAULT", "*").strip()
            return is_admin_uid(uid) and (default == "*" or code.strip().upper() in _parse_csv(default))
        return loop.run_until_complete(has_capability_async(uid, code))
    except RuntimeError:
        # No loop case
        default = os.getenv("ADMIN_CAPS_DEFAULT", "*").strip()
        return is_admin_uid(uid) and (default == "*" or code.strip().upper() in _parse_csv(default))
