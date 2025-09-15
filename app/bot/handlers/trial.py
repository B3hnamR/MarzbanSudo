from __future__ import annotations

import os
import html
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from app.services.provisioning import provision_trial
from sqlalchemy import select
from app.db.session import session_scope
from app.db.models import User, UserService
from app.utils.username import tg_username
from app.marzban.client import get_client
from app.utils.qr import generate_qr_png


router = Router()


@router.message(Command("trial"))
@router.message(F.text == "🧪 دریافت تست")
@router.message(lambda m: isinstance(getattr(m, "text", None), str) and (("دریافت" in m.text or "دريافت" in m.text) and "تست" in m.text))
async def handle_trial(message: Message) -> None:
    if not message.from_user:
        return
    username = tg_username(message.from_user.id)
    await message.answer("⏳ در حال آماده‌سازی حساب تست ...")
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
            deliver_sid = svc.id

        # Friendly delivery header
        sub_domain = os.getenv("SUB_DOMAIN_PREFERRED", "")
        lines = [
            f"🎉 حساب تستی {username} ایجاد شد و به لیست سرویس‌های شما اضافه شد.",
        ]
        if token and sub_domain:
            lines += [
                f"🔗 لینک اشتراک: https://{sub_domain}/sub4me/{token}/",
                f"🛰 v2ray: https://{sub_domain}/sub4me/{token}/v2ray",
                f"🧩 JSON:  https://{sub_domain}/sub4me/{token}/v2ray-json",
            ]
        await message.answer("\n".join(lines))

        # Post-provision delivery: send configs and QR similar to plan purchase
        deliver_username = username
        try:
            client = await get_client()
            info2 = await client.get_user(deliver_username)
        except Exception:
            info2 = {}
        finally:
            try:
                await client.aclose()
            except Exception:
                pass

        links = list(map(str, info2.get("links") or []))
        sub_url = info2.get("subscription_url") or ""
        token2 = token or (sub_url.rstrip("/").split("/")[-1] if sub_url else None)

        manage_kb = InlineKeyboardMarkup(
            inline_keyboard=[[ 
                InlineKeyboardButton(text="🛠 مدیریت سرویس", callback_data=f"acct:svc:{deliver_sid}"),
                InlineKeyboardButton(text="📋 کپی همه", callback_data=f"acct:copyall:svc:{deliver_sid}")
            ]]
        )

        if links:
            encoded = [html.escape(str(ln).strip()) for ln in links if str(ln).strip()]
            blocks = [f"<pre>{e}</pre>"]
            blocks = [f"<pre>{e}</pre>" for e in encoded]
            header = "📄 کانفیگ‌ها:\n\n"
            body = header + "\n\n".join(blocks)
            if len(body) <= 3500:
                await message.answer(body, reply_markup=manage_kb, parse_mode="HTML")
            else:
                chunk: list[str] = []
                size = 0
                first = True
                for b in blocks:
                    entry = ("" if first else "\n\n") + b
                    addition = (header + entry) if first else entry
                    if size + len(addition) > 3500:
                        await message.answer((header if first else "") + "\n\n".join(chunk), parse_mode="HTML")
                        chunk = [b]
                        size = len(header) + len(b)
                        first = False
                        continue
                    chunk.append(b)
                    size += len(addition)
                    first = False
                if chunk:
                    await message.answer((header if first else "") + "\n\n".join(chunk), reply_markup=manage_kb, parse_mode="HTML")
        else:
            await message.answer("ℹ️ برای مدیریت و دریافت کانفیگ‌ها از دکمه زیر استفاده کنید.", reply_markup=manage_kb)

        # Send QR
        disp_url = ""
        if sub_domain and token2:
            disp_url = f"https://{sub_domain}/sub4me/{token2}/"
        elif sub_url:
            disp_url = sub_url
        if disp_url:
            qr_file = BufferedInputFile(generate_qr_png(disp_url, size=400, border=2), filename="subscription_qr.png")
            try:
                await message.answer_photo(qr_file, caption="🔗 QR اشتراک")
            except Exception:
                await message.answer(disp_url)

    except RuntimeError as e:
        msg = str(e)
        if msg == "trial_already_used":
            await message.answer("❌ شما قبلاً حساب تست دریافت کرده‌اید و امکان دریافت مجدد وجود ندارد.")
        elif msg == "trial_not_allowed":
            await message.answer("⚠️ دسترسی تست برای شما فعال نیست. لطفاً با پشتیبانی تماس بگیرید.")
        elif msg == "trial_disabled_user":
            await message.answer("⛔️ دریافت تست برای حساب شما غیرفعال شده است.")
        elif msg == "trial_disabled":
            await message.answer("⛔️ دریافت تست در حال حاضر غیرفعال است.")
        else:
            await message.answer("❌ در حال حاضر امکان ایجاد حساب تست وجود ندارد. لطفاً بعداً تلاش کنید.")
    except Exception:
        await message.answer("❌ در حال حاضر امکان ایجاد حساب تست وجود ندارد. لطفاً بعداً تلاش کنید.")

