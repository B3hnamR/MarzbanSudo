from __future__ import annotations

import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from app.services.provisioning import provision_trial
from sqlalchemy import select
from app.db.session import session_scope
from app.db.models import User, UserService
from app.utils.username import tg_username


router = Router()


@router.message(Command("trial"))
@router.message(F.text == "🧪 دریافت تست")
@router.message(lambda m: isinstance(getattr(m, "text", None), str) and (("دریافت" in m.text or "دريافت" in m.text) and "تست" in m.text))
async def handle_trial(message: Message) -> None:
    if not message.from_user:
        return
    username = tg_username(message.from_user.id)
    await message.answer("در حال آماده‌سازی حساب تست ...")
    try:
        result = await provision_trial(message.from_user.id)
        token = result.get("subscription_token") or (
            result.get("subscription_url", "").split("/")[-1]
            if result.get("subscription_url") else None
        )
        # Persist user and service for account listing
        async with session_scope() as session:
            user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
            if not user:
                user = User(
                    telegram_id=message.from_user.id,
                    marzban_username=username,
                    subscription_token=None,
                    status="active",
                    data_limit_bytes=0,
                    balance=0,
                )
                session.add(user)
                await session.flush()
            svc = await session.scalar(
                select(UserService).where(UserService.user_id == user.id, UserService.username == username)
            )
            if not svc:
                svc = UserService(user_id=user.id, username=username, status="active")
                session.add(svc)
                await session.flush()
            if token:
                svc.last_token = token
                user.subscription_token = token
            await session.commit()

        lines = [f"Trial account {username} created and added to your services."]
        if token:
            sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
            if sub_domain:
                lines.append(f"Subscription: https://{sub_domain}/sub4me/{token}/")
                lines.append(f"v2ray: https://{sub_domain}/sub4me/{token}/v2ray")
                lines.append(f"JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json")
        await message.answer("\n".join(lines))
    except RuntimeError as e:
        msg = str(e)
        if msg == "trial_already_used":
            await message.answer("You already received a trial and cannot request again.")
        elif msg == "trial_not_allowed":
            await message.answer("Trial access is not enabled for you. Contact support.")
        elif msg == "trial_disabled_user":
            await message.answer("Trial is disabled for your account.")
        elif msg == "trial_disabled":
            await message.answer("Trial feature is disabled.")
        else:
            await message.answer("Unable to provision trial right now. Please try again later.")
    except Exception:
        await message.answer("Unable to provision trial right now. Please try again later.")
