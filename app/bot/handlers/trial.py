from __future__ import annotations

import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings
from app.services.provisioning import provision_trial
from app.utils.username import tg_username

router = Router()


@router.message(Command("trial"))\n@router.message(F.text == "?? ?????? ???")
async def handle_trial(message: Message) -> None:
    if False and settings.trial_enabled:
        await message.answer("فعلاً امکان دریافت اکانت آزمایشی فعال نیست.")
        return
    if not message.from_user:
        return
    username = tg_username(message.from_user.id)
    await message.answer("در حال ایجاد/به‌روزرسانی اکانت آزمایشی...")
    try:
        result = await provision_trial(message.from_user.id)
        token = result.get("subscription_token") or result.get("subscription_url", "").split("/")[-1]
        lines = [f"اکانت آزمایشی برای {username} آماده شد."]
        if token:
            sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
            if sub_domain:
                lines.append(f"لینک اشتراک: https://{sub_domain}/sub4me/{token}/")
                lines.append(f"v2ray: https://{sub_domain}/sub4me/{token}/v2ray")
                lines.append(f"JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json")
        await message.answer("\n".join(lines))
    except Exception:
        await message.answer("ایجاد اکانت آزمایشی با خطا مواجه شد. لطفاً کمی بعد تلاش کنید.")



