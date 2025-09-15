from __future__ import annotations

import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from app.services.provisioning import provision_trial
from app.utils.username import tg_username

router = Router()

@router.message(Command("trial"))
@router.message(F.text == "?? ?????? ???")
async def handle_trial(message: Message) -> None:
    if not message.from_user:
        return
    username = tg_username(message.from_user.id)
    await message.answer("?? ??? ?????/??????????? ???? ???????...")
    try:
        result = await provision_trial(message.from_user.id)
        token = result.get("subscription_token") or (
            result.get("subscription_url", "").split("/")[-1]
            if result.get("subscription_url") else None
        )
        lines = [f"???? ??????? ???? {username} ????? ??."]
        if token:
            sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
            if sub_domain:
                lines.append(f"???? ??????: https://{sub_domain}/sub4me/{token}/")
                lines.append(f"v2ray: https://{sub_domain}/sub4me/{token}/v2ray")
                lines.append(f"JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json")
        await message.answer("\n".join(lines))
    except Exception:
        await message.answer("????? ?? ???? ???? ??????? ?? ???. ????? ?????? ???? ????.")
