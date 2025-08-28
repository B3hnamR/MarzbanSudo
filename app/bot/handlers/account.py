from __future__ import annotations

import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.marzban.client import get_client
from app.utils.username import tg_username

router = Router()


@router.message(Command("account"))
async def handle_account(message: Message) -> None:
    if not message.from_user:
        return
    username = tg_username(message.from_user.id)
    await message.answer("در حال دریافت اطلاعات اکانت...")
    client = await get_client()
    try:
        data = await client.get_user(username)
        # Expected fields: subscription_url or token, data_limit, used_traffic, expire
        token = data.get("subscription_token") or data.get("subscription_url", "").split("/")[-1]
        expire_ts = int(data.get("expire")) if data.get("expire") else 0
        data_limit = int(data.get("data_limit") or 0)
        used_traffic = int(data.get("used_traffic") or 0)
        remaining = max(data_limit - used_traffic, 0)
        def _fmt_gb(v: int) -> str:
            if v <= 0:
                return "نامحدود"
            return f"{v / (1024**3):.0f}GB"
        lines = [
            f"نام کاربری: {username}",
            f"حجم کل: {_fmt_gb(data_limit)}",
            f"مصرف‌شده: {_fmt_gb(used_traffic)}",
            f"باقی‌مانده: {_fmt_gb(remaining)}",
        ]
        if expire_ts > 0:
            from datetime import datetime
            lines.append(f"انقضا: {datetime.utcfromtimestamp(expire_ts).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        if token:
            sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
            if sub_domain:
                lines.append(f"لینک اشتراک: https://{sub_domain}/sub4me/{token}/")
                lines.append(f"v2ray: https://{sub_domain}/sub4me/{token}/v2ray")
                lines.append(f"JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json")
        await message.answer("\n".join(lines))
    except Exception:
        await message.answer("اکانت شما در سیستم یافت نشد یا در حال حاضر اطلاعات قابل دریافت نیست.")
    finally:
        await client.aclose()
