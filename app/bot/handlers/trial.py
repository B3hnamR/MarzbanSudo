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
@router.message(F.text == "?? ?????? ???")
@router.message(lambda m: getattr(m, "text", None) and isinstance(getattr(m, "text", None), str) and ("??????" in m.text and "???" in m.text))
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
            svc = await session.scalar(select(UserService).where(UserService.user_id == user.id, UserService.username == username))
            if not svc:
                svc = UserService(user_id=user.id, username=username, status="active")
                session.add(svc)
                await session.flush()
            if token:
                svc.last_token = token
                user.subscription_token = token
            await session.commit()

        lines = [f"???? ??????? ???? {username} ????? ??. O'U^UOO_ O"O�OUO U^ O_O�UOOU?O� OO� O_UcU.U� O3O�U^UOO3 O'U^O_."]
        if token:
            sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
            if sub_domain:
                lines.append(f"???? ??????: https://{sub_domain}/sub4me/{token}/")
                lines.append(f"v2ray: https://{sub_domain}/sub4me/{token}/v2ray")
                lines.append(f"JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json")
        await message.answer("\n".join(lines))
    except RuntimeError as e:
        msg = str(e)
        if msg == "trial_already_used":
            await message.answer("O'U^UOO_ ???? ??????? ???? O'O_U� OO3O�O_ O�O O_U�UOO_ O�O3UOO_ UO_.")
        elif msg == "trial_not_allowed":
            await message.answer("O"O�U, O"O�OUO O�U^O_ O_O3 O_O�UOOU?O� O�O. U.U+OO3O" U.O"U,O�.")
        elif msg == "trial_disabled_user":
            await message.answer("O"O�OUO O'U^UOO_ ???? ??????? O�O U_OUOOU+ O�O.")
        elif msg == "trial_disabled":
            await message.answer("OO�U,UO O'U^UOO_ ???? ??????? OO�U�U� O�U^O'.")
        else:
            await message.answer("????? ?? ???? ???? ??????? ?? ???. ????? ?????? ???? ????.")
    except Exception:
        await message.answer("????? ?? ???? ???? ??????? ?? ???. ????? ?????? ???? ????.")
